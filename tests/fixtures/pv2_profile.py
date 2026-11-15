"""Frozen-profile transport hooks for the owned, internal-only CI containers."""

from __future__ import annotations

import hashlib
import json
import os
from contextvars import ContextVar
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
from uuid import UUID, uuid4

import httpcore
import httpx
from cf2_runtime import EVIDENCE, append, digest, guard, save
from kernel_providers import DeepSeekProvider, LLMProviderError, LLMRequest, LLMResponse
from kernel_rag.embeddings import DashScopeEmbeddingProvider
from kernel_runtime import ExecutionLimits
from kernel_tools.external.http import _GuardedTransport
from kernel_tools.external.openapi import OpenAPITool
from kernel_tools.models import ToolExecutionContext

from scripts.pv1_harness import FixturePool, HarnessBlocked, Journal
from scripts.pv2_offline_harness import FixtureLedger

MODEL = "deepseek-flash"
PROMPT_PATH = Path("/prompts/pv1-runbook-assistant-v1.txt")
PATH = "/repos/royliu1105/agent-kernel/actions/runs/43634747295"
BODY = {
    "id": 43634747295,
    "run_attempt": 1,
    "head_sha": "2bb3f4ab1d50afa1cc2686b42b1ebcaf5db1f726",
    "status": "completed",
    "conclusion": "success",
    "fixture": True,
}
LIMITS = {
    "AGENT_KERNEL_MAX_MODEL_CALLS": "2",
    "AGENT_KERNEL_MAX_TOOL_CALLS": "8",
    "AGENT_KERNEL_MAX_ACTIVE_SECONDS": "120",
    "AGENT_KERNEL_MAX_TOTAL_TOKENS": "32000",
    "AGENT_KERNEL_MAX_OUTPUT_TOKENS": "2048",
    "AGENT_KERNEL_MAX_HISTORY_BYTES": "262144",
}
CASES = {"approve", "reject", "concurrent", "retry_before", "retry_after"}


def setup() -> None:
    guard()
    identities = json.loads((EVIDENCE / "identities.json").read_text())
    document = {
        "openapi": "3.1.0",
        "paths": {
            PATH: {
                "get": {
                    "operationId": "github_ci_run_status",
                    "parameters": [
                        {
                            "name": "exclude_pull_requests",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "boolean", "const": True},
                        }
                    ],
                }
            }
        },
    }
    save("github-openapi.json", document)
    save(
        "tools.json",
        {
            "openapi": [
                {
                    "name": "pv2_github_fixture",
                    "document": "/evidence/github-openapi.json",
                    "endpoint": {
                        "url": "https://api.github.com",
                        "max_response_bytes": 32768,
                        "timeout_ms": 10000,
                        "headers": {
                            "X-GitHub-Api-Version": "2022-11-28",
                            "Accept": "application/vnd.github+json",
                        },
                    },
                    "access": {"workspace_ids": [identities["operator"]["workspace_id"]]},
                    "bindings": [
                        {
                            "operation_id": "github_ci_run_status",
                            "contract": {
                                "name": "github_ci_run_status",
                                "read_only": True,
                                "idempotent": True,
                                "retry_safe": False,
                                "timeout_ms": 10000,
                                "policy_decision": "require_approval",
                            },
                        }
                    ],
                }
            ]
        },
    )
    binding = {
        "model": MODEL,
        "limits": LIMITS,
        "embedding": ["text-embedding-v3", 1024],
        "prompt": PROMPT_PATH.read_text(),
        "tools": json.loads((EVIDENCE / "tools.json").read_text()),
    }
    case_id = uuid4()
    save("profile.json", {"case_id": str(case_id), "binding": digest(binding)})
    FixtureLedger(EVIDENCE / "ledger.jsonl", case_id, digest(binding)).create()
    (EVIDENCE / "journals").mkdir(mode=0o700)


def ledger() -> FixtureLedger:
    data = json.loads((EVIDENCE / "profile.json").read_text())
    return FixtureLedger(EVIDENCE / "ledger.jsonl", UUID(data["case_id"]), data["binding"])


def response(payload: dict[str, Any]) -> dict[str, Any]:
    results = [item for item in payload["input"] if item.get("type") == "function_call_output"]
    task = json.loads(
        next(item["content"][0]["text"] for item in payload["input"] if item.get("role") == "user")
    )
    if task["case"] == "retry_before":
        assert not results
        output = [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": "Synthetic retry completed without a tool"}
                ],
            }
        ]
    elif results:
        assert len(results) == 1
        observed = json.loads(results[0]["output"])
        assert observed["result"]["data"] == BODY
        output = [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Synthetic CI status: success"}],
            }
        ]
    else:
        output = [
            {
                "type": "function_call",
                "call_id": "ci-lookup",
                "name": "github_ci_run_status",
                "arguments": '{"query":{"exclude_pull_requests":true}}',
            }
        ]
    return {"model": MODEL, "output": output, "usage": {"input_tokens": 10, "output_tokens": 2}}


def install() -> Journal:
    import kernel_rag.embeddings as embeddings
    import kernel_runtime.router as router

    guard()
    assert os.environ.get("PV2_PROFILE") == "1"
    assert ExecutionLimits.from_env() == ExecutionLimits.from_env(LIMITS)
    state = ledger()
    executor = uuid4()
    role = os.environ["CF2_ROLE"]
    state.change(
        "register",
        executor=executor,
        role="api" if role == "api" else "worker",
        attestation=state.binding,
    )
    journal = Journal(EVIDENCE / "journals", state.case_id, executor)
    prompt = PROMPT_PATH.read_text()
    assert hashlib.sha256(prompt.encode()).hexdigest() == (
        "bf6c5329a3e3bfa8587947b53a904fe4c3193444ad1f24a947305f163b1b091b"
    )
    assert (
        digest(
            {
                "model": MODEL,
                "limits": LIMITS,
                "embedding": ["text-embedding-v3", 1024],
                "prompt": prompt,
                "tools": json.loads((EVIDENCE / "tools.json").read_text()),
            }
        )
        == state.binding
    )
    save(
        f"profile-{role}.json",
        {
            "binding": state.binding,
            "limits": ExecutionLimits.from_env().model_dump(mode="json"),
            "model": MODEL,
            "embedding": ["text-embedding-v3", 1024],
            "fallbacks": [],
        },
    )
    seen: set[str] = set()

    class Provider(DeepSeekProvider):
        async def complete(self, request: LLMRequest) -> LLMResponse:
            assert request.model == MODEL and request.max_output_tokens == 2048
            assert request.messages[0].content == prompt
            task = json.loads(
                next(item.content for item in request.messages if item.role.value == "user")
            )
            case = task["case"]
            assert case in CASES
            run_id = UUID(str(request.metadata["run_id"]))
            append(
                "profile-requests.jsonl",
                {
                    "executor": str(executor),
                    "run_id": str(run_id),
                    "case": case,
                    "request": request.model_dump(mode="json"),
                },
            )
            if case == "retry_before" and str(run_id) not in seen:
                seen.add(str(run_id))
                raise LLMProviderError("Synthetic pre-dispatch failure", error_type="rate_limit")

            def transport(wire: httpx.Request) -> httpx.Response:
                assert str(wire.url) == "https://api.deepseek.com/responses"
                payload = json.loads(wire.content)
                assert payload["model"] == MODEL and payload["max_output_tokens"] == 2048
                attempt = uuid4()
                try:
                    state.change("reserve", executor=executor, task=run_id, attempt=attempt)
                except HarnessBlocked as error:
                    raise LLMProviderError(
                        "Fixture admission denied", error_type="pv2_admission_denied"
                    ) from error
                append(
                    "profile-dispatches.jsonl",
                    {
                        "executor": str(executor),
                        "run_id": str(run_id),
                        "payload_sha256": digest(payload),
                        "case": case,
                    },
                )
                if case == "retry_after":
                    return httpx.Response(
                        429, json={"error": {"message": "synthetic unknown charge"}}
                    )
                result = response(payload)
                state.change("complete", executor=executor, attempt=attempt)
                return httpx.Response(200, json=result)

            return await DeepSeekProvider(
                api_key="fixture-only", transport=httpx.MockTransport(transport)
            ).complete(request)

    class Embedding(DashScopeEmbeddingProvider):
        def __init__(self, **kwargs: Any) -> None:
            def transport(wire: httpx.Request) -> httpx.Response:
                assert (
                    str(wire.url) == "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
                )
                payload = json.loads(wire.content)
                assert payload["model"] == "text-embedding-v3" and payload["dimensions"] == 1024
                attempt = uuid4()
                state.change(
                    "reserve",
                    executor=executor,
                    task=uuid4(),
                    attempt=attempt,
                    kind="embedding",
                    amount=Decimal("0.10"),
                )
                result = {
                    "data": [
                        {"index": i, "embedding": [0.01] * 1024}
                        for i in range(len(payload["input"]))
                    ],
                    "usage": {"total_tokens": 10},
                }
                state.change("complete", executor=executor, attempt=attempt)
                append(
                    "profile-embedding.jsonl",
                    {"dimensions": 1024, "model": payload["model"], "executor": str(executor)},
                )
                return httpx.Response(200, json=result)

            super().__init__(
                env={
                    "DASHSCOPE_API_KEY": "fixture-only",
                    "DASHSCOPE_EMBEDDING_DIMENSIONS": "1024",
                    "DASHSCOPE_EMBEDDING_MODEL": "text-embedding-v3",
                },
                transport=httpx.MockTransport(transport),
            )

    bound: ContextVar[FixturePool] = ContextVar("pv2_fixture_pool")
    original_execute = OpenAPITool.execute_with_context
    original_handle = _GuardedTransport.handle_async_request

    async def execute(
        tool: OpenAPITool, arguments: dict[str, Any], *, context: ToolExecutionContext
    ) -> dict[str, Any]:
        assert context.tool_call_id is not None and context.run_id is not None
        pool = FixturePool(journal, context.tool_call_id, body=json.dumps(BODY).encode())
        token = bound.set(pool)
        try:
            output = await original_execute(tool, arguments, context=context)
            pool.validated(output["data"])
            return output
        finally:
            bound.reset(token)

    async def handle(transport: _GuardedTransport, request: httpx.Request) -> httpx.Response:
        await transport._pool.aclose()
        transport._pool = cast(httpcore.AsyncConnectionPool, bound.get())
        return await original_handle(transport, request)

    patch.object(router, "DeepSeekProvider", Provider).start()
    patch.object(embeddings, "DashScopeEmbeddingProvider", Embedding).start()
    patch.object(OpenAPITool, "execute_with_context", execute).start()
    patch.object(_GuardedTransport, "handle_async_request", handle).start()
    return journal
