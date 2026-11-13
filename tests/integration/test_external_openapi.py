import json
import threading
import time
from collections.abc import Iterator
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from kernel_core import RiskLevel, RunEventType, RunStatus
from kernel_policy import PolicyAwareToolExecutor, ToolApprovalRequiredError
from kernel_runtime import RunExecutionService
from kernel_storage import AgentRepository, ApprovalRepository, RunRepository, ToolCallRepository
from kernel_tools import ToolExecutionContext, ToolExecutor, ToolRegistry, ToolRequest
from kernel_tools.errors import ToolTimeoutError, ToolValidationError
from kernel_tools.external import (
    ExternalAccess,
    ExternalConfigurationError,
    ExternalToolContract,
    ExternalToolError,
    ExternalToolsConfig,
    HttpEndpoint,
    OpenAPIBinding,
    OpenAPIConfig,
    load_external_tools,
)
from kernel_tools.external.http import create_http_client
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

SPEC = Path(__file__).parents[2] / "examples" / "external-tools" / "openapi.json"


@pytest.fixture
def http_fixture() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    requests: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            requests.append({"method": "GET", "path": self.path, "headers": dict(self.headers)})
            if self.path.endswith("/slow"):
                time.sleep(0.15)
            if self.path.endswith("/redirect"):
                self.send_response(307)
                self.send_header("Location", "/v1/items/credential_trap")
                self.end_headers()
                return
            if self.path.endswith("/error"):
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"secret-auth-token should not appear in exceptions")
                return
            body = (
                b"x" * 100_000
                if self.path.endswith("/large")
                else json.dumps(
                    {
                        "path": self.path,
                    }
                ).encode()
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            with suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(body)

        def do_POST(self) -> None:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(
                {
                    "method": "POST",
                    "path": self.path,
                    "headers": dict(self.headers),
                    "body": data,
                }
            )
            body = json.dumps({"created": data["name"]}).encode()
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def configuration(url: str, *, timeout_ms: int = 1000) -> ExternalToolsConfig:
    return ExternalToolsConfig(
        openapi=(
            OpenAPIConfig(
                name="inventory",
                document=SPEC,
                endpoint=HttpEndpoint(
                    url=url,
                    allow_private_network=True,
                    max_response_bytes=1024,
                    headers={"Authorization": SecretStr("Bearer fixture-only")},
                ),
                access=ExternalAccess(allow_unscoped=True),
                bindings=(
                    OpenAPIBinding(
                        operation_id="get_item",
                        contract=ExternalToolContract(
                            name="get_item",
                            read_only=True,
                            idempotent=True,
                            timeout_ms=timeout_ms,
                        ),
                    ),
                    OpenAPIBinding(
                        operation_id="create_item",
                        contract=ExternalToolContract(
                            name="create_item",
                            idempotent=True,
                        ),
                        idempotency_header="Idempotency-Key",
                    ),
                ),
            ),
        )
    )


@pytest.mark.asyncio
async def test_openapi_policy_validation_and_stable_idempotency(
    http_fixture: tuple[str, list[dict[str, Any]]],
) -> None:
    url, requests = http_fixture
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration(url)):
        policy = PolicyAwareToolExecutor(registry=registry)
        with pytest.raises(ToolApprovalRequiredError):
            await policy.execute(ToolRequest(tool_name="get_item"))
        executor = ToolExecutor(registry=registry)
        for args in (
            {},
            {"path": {"item_id": 12}},
            {"path": {"item_id": "../private"}},
            {"path": {"item_id": "ok"}, "query": {"unexpected": "value"}},
        ):
            with pytest.raises(ToolValidationError):
                await executor.execute(ToolRequest(tool_name="get_item", arguments=args))
        with pytest.raises(ToolValidationError):
            await executor.execute(
                ToolRequest(
                    tool_name="create_item",
                    arguments={
                        "body": {"name": "valid", "credential": "not allowed"},
                    },
                )
            )
        assert requests == []
        result = await executor.execute(
            ToolRequest(
                tool_name="get_item",
                arguments={
                    "path": {"item_id": "abc"},
                    "query": {"verbose": True},
                },
            )
        )
        assert result.output["data"]["path"] == "/v1/items/abc?verbose=true"
        assert result.output["untrusted"] is True
        assert requests[-1]["headers"]["Authorization"] == "Bearer fixture-only"
        with pytest.raises(ExternalToolError, match="persisted tool call"):
            await executor.execute(
                ToolRequest(
                    tool_name="create_item",
                    arguments={"body": {"name": "item"}},
                )
            )
        call_id = uuid4()
        for _ in range(2):
            await executor.execute(
                ToolRequest(
                    tool_name="create_item",
                    arguments={"body": {"name": "item"}},
                    context=ToolExecutionContext(tool_call_id=call_id),
                )
            )
        assert len(requests) == 3
        assert {r["headers"]["Idempotency-Key"] for r in requests[1:]} == {str(call_id)}
        assert registry.get("create_item").metadata.retry_safe is False
    assert registry.list_metadata() == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("item_id", ["redirect", "large", "error"])
async def test_openapi_http_failures_are_bounded_and_never_retried(
    http_fixture: tuple[str, list[dict[str, Any]]],
    item_id: str,
) -> None:
    url, requests = http_fixture
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration(url)):
        with pytest.raises(ExternalToolError) as error:
            await ToolExecutor(registry=registry).execute(
                ToolRequest(
                    tool_name="get_item",
                    arguments={"path": {"item_id": item_id}},
                )
            )
        assert "secret-auth-token" not in str(error.value)
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_openapi_timeout_cancels_request(
    http_fixture: tuple[str, list[dict[str, Any]]],
) -> None:
    url, requests = http_fixture
    registry = ToolRegistry()
    async with load_external_tools(registry, configuration(url, timeout_ms=30)):
        with pytest.raises(ToolTimeoutError):
            await ToolExecutor(registry=registry).execute(
                ToolRequest(
                    tool_name="get_item",
                    arguments={"path": {"item_id": "slow"}},
                )
            )
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_openapi_workspace_denial_has_no_network_side_effect(
    http_fixture: tuple[str, list[dict[str, Any]]],
) -> None:
    url, requests = http_fixture
    value = configuration(url)
    api = value.openapi[0].model_copy(update={"access": ExternalAccess(workspace_ids=(uuid4(),))})
    registry = ToolRegistry()
    async with load_external_tools(registry, ExternalToolsConfig(openapi=(api,))):
        with pytest.raises(ExternalToolError, match="access denied"):
            await ToolExecutor(registry=registry).execute(
                ToolRequest(
                    tool_name="get_item",
                    arguments={"path": {"item_id": "abc"}},
                    context=ToolExecutionContext(workspace_id=uuid4()),
                )
            )
    assert requests == []


@pytest.mark.asyncio
async def test_http_guard_rejects_unapproved_origin_and_private_address() -> None:
    endpoint = HttpEndpoint(url="https://127.0.0.1/")
    async with create_http_client(endpoint) as client:
        with pytest.raises(ExternalToolError, match="origin"):
            await client.get("https://example.org/")
        with pytest.raises(ExternalToolError, match="disallowed network"):
            await client.get("https://127.0.0.1/")


@pytest.mark.asyncio
async def test_openapi_rejects_claiming_write_is_read_only() -> None:
    config = configuration("http://127.0.0.1:1/v1")
    binding = OpenAPIBinding(
        operation_id="create_item",
        contract=ExternalToolContract(
            name="unsafe",
            read_only=True,
            idempotent=True,
            retry_safe=True,
        ),
    )
    api = config.openapi[0].model_copy(update={"bindings": (binding,)})
    with pytest.raises(ExternalConfigurationError):
        async with load_external_tools(ToolRegistry(), ExternalToolsConfig(openapi=(api,))):
            pytest.fail("Mutating method must not be marked read-only")


@pytest.mark.asyncio
async def test_openapi_read_only_binding_requires_independent_persisted_approval(
    http_fixture: tuple[str, list[dict[str, Any]]],
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    url, requests = http_fixture
    base = configuration(url).openapi[0]
    binding = base.bindings[0].model_copy(
        update={
            "contract": ExternalToolContract(
                name="get_item",
                read_only=True,
                risk_level=RiskLevel.READ_ONLY,
                policy_decision="require_approval",
            )
        }
    )
    denied_binding = binding.model_copy(
        update={
            "contract": ExternalToolContract(
                name="denied_item",
                read_only=True,
                risk_level=RiskLevel.READ_ONLY,
                policy_decision="deny",
            )
        }
    )
    api = base.model_copy(update={"bindings": (binding, denied_binding)})
    registry = ToolRegistry()
    async with load_external_tools(registry, ExternalToolsConfig(openapi=(api,))):
        with sqlite_session_factory() as session:
            agent = AgentRepository(session).create(name="external-openapi-policy")
            repository = RunRepository(session)
            service = RunExecutionService(tool_registry=registry)
            denied_run = repository.create(
                agent_id=agent.id,
                input_payload={
                    "tool": {
                        "name": "denied_item",
                        "arguments": {"path": {"item_id": "denied"}},
                    }
                },
            )
            repository.apply_transition(
                run_id=denied_run.id,
                status=RunStatus.QUEUED,
                event_type=RunEventType.RUN_QUEUED,
                payload={},
            )
            denied = await service.execute(run_id=denied_run.id, repository=repository)
            assert denied.error_type == "tool_denied"
            assert requests == []
            assert any(
                event.type is RunEventType.POLICY_EVALUATED and event.payload["decision"] == "deny"
                for event in repository.list_events(denied_run.id)
            )
            run = repository.create(
                agent_id=agent.id,
                input_payload={
                    "tool": {
                        "name": "get_item",
                        "arguments": {"path": {"item_id": "approved"}},
                    }
                },
            )
            repository.apply_transition(
                run_id=run.id,
                status=RunStatus.QUEUED,
                event_type=RunEventType.RUN_QUEUED,
                payload={},
            )
            waiting = await service.execute(run_id=run.id, repository=repository)
            assert waiting.status is RunStatus.WAITING_APPROVAL
            assert requests == []
            approvals = ApprovalRepository(session)
            approvals.approve(approval_id=approvals.list_for_run(run.id)[0].id)
            completed = await service.resume(
                run_id=run.id,
                repository=repository,
                approval_repository=approvals,
                tool_call_repository=ToolCallRepository(session),
            )
            assert completed.status is RunStatus.SUCCEEDED
            assert len(requests) == 1
            assert requests[0]["path"] == "/v1/items/approved"
            events = repository.list_events(run.id)
            assert any(
                event.type is RunEventType.POLICY_EVALUATED
                and event.payload["decision"] == "require_approval"
                for event in events
            )
            assert sum(event.type is RunEventType.TOOL_CALL_COMPLETED for event in events) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["remote_ref", "header", "duplicate_id", "path_mismatch"])
async def test_openapi_rejects_unsafe_documents_without_network(case: str, tmp_path: Path) -> None:
    document = json.loads(SPEC.read_text())
    operation = document["paths"]["/items/{item_id}"]["get"]
    if case == "remote_ref":
        operation["parameters"][0]["schema"] = {"$ref": "http://169.254.169.254/credentials"}
    elif case == "header":
        operation["parameters"].append(
            {
                "name": "Authorization",
                "in": "header",
                "schema": {"type": "string"},
            }
        )
    elif case == "duplicate_id":
        document["paths"]["/duplicate"] = {"get": operation}
    else:
        operation["parameters"][0]["name"] = "different_id"
    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(document))
    config = configuration("http://127.0.0.1:1/v1")
    api = config.openapi[0].model_copy(update={"document": path})
    registry = ToolRegistry()
    with pytest.raises(ExternalConfigurationError, match="startup failed"):
        async with load_external_tools(registry, ExternalToolsConfig(openapi=(api,))):
            pytest.fail("Unsafe OpenAPI contract must not be registered")
    assert registry.list_metadata() == ()
