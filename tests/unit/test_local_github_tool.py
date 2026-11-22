"""Exact local GitHub binding: no real HTTP/model calls or runtime database."""

import hashlib
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from jsonschema import Draft202012Validator
from kernel_policy import (
    PolicyAwareToolExecutor,
    PolicyDecisionType,
    ToolApprovalRequiredError,
    ToolPolicy,
    ToolPolicyEvaluator,
)
from kernel_tools import ToolExecutionContext, ToolExecutor, ToolRegistry, ToolRequest
from kernel_tools.errors import ToolValidationError
from kernel_tools.external.config import (
    ExternalToolsConfig,
    HttpEndpoint,
    read_external_tools_config,
)
from kernel_tools.external.loader import load_external_tools
from kernel_tools.external.security import ExternalToolError
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "deploy/local-paid-tools"
ARGS = {"path": {"run_id": 43634747295}, "query": {"exclude_pull_requests": True}}
BODY = b'{"id":43634747295,"run_attempt":1,"conclusion":"success"}'


def configuration() -> ExternalToolsConfig:
    config = read_external_tools_config(DIRECTORY / "tools.json")
    api = config.openapi[0].model_copy(update={"document": DIRECTORY / "github-ci.openapi.json"})
    return config.model_copy(update={"openapi": (api,)})


@pytest_asyncio.fixture
async def binding(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[ToolRegistry, list[httpx.Request], dict[str, bytes]]]:
    config = configuration()
    api = config.openapi[0]
    reviewed = api.bindings[0].model_copy(
        update={"response_sha256": hashlib.sha256(BODY).hexdigest()}
    )
    config = config.model_copy(
        update={"openapi": (api.model_copy(update={"bindings": (reviewed,)}),)}
    )
    requests: list[httpx.Request] = []
    response = {"body": BODY}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, content=response["body"], headers={"Content-Type": "application/json"}
        )

    def client(endpoint: HttpEndpoint) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            headers={name: value.get_secret_value() for name, value in endpoint.headers.items()},
            trust_env=False,
        )

    monkeypatch.setattr("kernel_tools.external.loader.create_http_client", client)
    registry = ToolRegistry()
    async with load_external_tools(registry, config):
        yield registry, requests, response


@pytest.mark.asyncio
async def test_exact_binding_requires_approval_before_any_http(
    binding: tuple[ToolRegistry, list[httpx.Request], dict[str, bytes]],
) -> None:
    registry, requests, _ = binding
    assert requests == []  # Loading a local OpenAPI file must not perform discovery I/O.
    evaluator = ToolPolicyEvaluator(
        ToolPolicy(tool_decisions={"github_ci_run_status": PolicyDecisionType.ALLOW})
    )
    request = ToolRequest(tool_name="github_ci_run_status", arguments=ARGS)
    for _ in range(2):
        with pytest.raises(ToolApprovalRequiredError):
            await PolicyAwareToolExecutor(registry=registry, evaluator=evaluator).execute(request)
    assert requests == []
    assert registry.get("github_ci_run_status").metadata.retry_safe is False

    # Simulate authorized adapter execution only after the above policy boundary.
    result = await ToolExecutor(registry=registry).execute(request)
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert str(requests[0].url) == (
        "https://api.github.com/repos/royliu1105/agent-kernel/actions/runs/43634747295"
        "?exclude_pull_requests=true"
    )
    assert "authorization" not in requests[0].headers
    assert "cookie" not in requests[0].headers
    assert requests[0].headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert result.output["untrusted"] is True
    assert result.output["data"]["run_attempt"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args",
    [
        {},
        {"path": {"run_id": 1}, "query": {"exclude_pull_requests": True}},
        {"path": {"run_id": "43634747295"}, "query": {"exclude_pull_requests": True}},
        {"path": {"run_id": 43634747295}, "query": {"exclude_pull_requests": False}},
        {**ARGS, "url": "https://other.example"},
        {**ARGS, "headers": {"Authorization": "not-allowed"}},
    ],
)
async def test_wrong_arguments_never_dispatch(
    binding: tuple[ToolRegistry, list[httpx.Request], dict[str, bytes]], args: dict[str, Any]
) -> None:
    registry, requests, _ = binding
    with pytest.raises(ToolValidationError):
        await ToolExecutor(registry=registry).execute(
            ToolRequest(tool_name="github_ci_run_status", arguments=args)
        )
    assert requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [b'{"email":"unreviewed-response@example.test"}', BODY + b"\n", b"", b"not-json"],
)
async def test_changed_response_is_not_exposed_or_retried(
    binding: tuple[ToolRegistry, list[httpx.Request], dict[str, bytes]],
    body: bytes,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry, requests, response = binding
    response["body"] = body
    monkeypatch.setenv("AGENT_KERNEL_PRIVATE_EVIDENCE_DIR", str(tmp_path / "review"))
    with pytest.raises(ExternalToolError) as error:
        await ToolExecutor(registry=registry).execute(
            ToolRequest(tool_name="github_ci_run_status", arguments=ARGS)
        )
    assert error.value.error_type == "external_response_review_required"
    assert "unreviewed-response" not in str(error.value)
    assert len(requests) == 1
    evidence = list((tmp_path / "review").glob("*.json"))
    assert len(evidence) == 1
    saved = json.loads(evidence[0].read_text(encoding="utf-8"))
    assert saved["actual_sha256"] == hashlib.sha256(body).hexdigest()
    assert saved["expected_sha256"] == hashlib.sha256(BODY).hexdigest()
    if b"unreviewed-response" in body:
        assert "unreviewed-response@example.test" in (saved.get("body_utf8") or "")


@pytest.mark.parametrize("digest", ["bad", "A" * 64, "0" * 63, "0" * 65, "0" * 64 + "\n"])
def test_invalid_response_hash_is_rejected(digest: str) -> None:
    binding = configuration().openapi[0].bindings[0]
    with pytest.raises(ValidationError):
        type(binding).model_validate({**binding.model_dump(), "response_sha256": digest})


@pytest.mark.asyncio
async def test_local_exception_does_not_allow_authenticated_workspaces(
    binding: tuple[ToolRegistry, list[httpx.Request], dict[str, bytes]],
) -> None:
    registry, requests, _ = binding
    with pytest.raises(ExternalToolError, match="access denied"):
        await ToolExecutor(registry=registry).execute(
            ToolRequest(
                tool_name="github_ci_run_status",
                arguments=ARGS,
                context=ToolExecutionContext(workspace_id=uuid4()),
            )
        )
    assert requests == []


@pytest.mark.asyncio
async def test_review_hash_is_in_checkpoint_contract(
    binding: tuple[ToolRegistry, list[httpx.Request], dict[str, bytes]],
) -> None:
    registry, _, _ = binding
    metadata = registry.get("github_ci_run_status").metadata
    assert metadata.model_dump()["response_sha256"] == hashlib.sha256(BODY).hexdigest()
    assert (
        metadata.model_dump_json()
        != metadata.model_copy(update={"response_sha256": "0" * 64}).model_dump_json()
    )
    assert Draft202012Validator(metadata.input_schema).is_valid(ARGS)


def test_deployed_binding_is_frozen_and_bounded() -> None:
    config = configuration()
    assert len(config.openapi) == 1 and not config.mcp
    api = config.openapi[0]
    assert api.endpoint.url == "https://api.github.com"
    assert api.endpoint.max_response_bytes == 32768
    assert api.endpoint.timeout_ms == 10000
    assert api.endpoint.allow_private_network is False
    assert set(api.endpoint.headers) == {"Accept", "X-GitHub-Api-Version"}
    assert len(api.bindings) == 1
    binding = api.bindings[0]
    assert binding.response_sha256 == (
        "a1b246537bc9e07143ad3daaf7dc1a9da6d03d1663b28829257f05766b11d232"
    )
    assert binding.contract.read_only and binding.contract.idempotent
    assert binding.contract.policy_decision == "require_approval"
    assert binding.contract.retry_safe is False
    assert api.access.allow_unscoped and not api.access.workspace_ids
    with pytest.raises(ValidationError):
        type(binding).model_validate({**binding.model_dump(), "response_sha256": "bad"})
