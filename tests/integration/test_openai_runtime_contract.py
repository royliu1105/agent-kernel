"""Offline wire contracts: real OpenAI adapter, runtime and persisted tool state."""

import json
from typing import Any
from uuid import UUID

import httpx
import pytest
from kernel_core import RiskLevel, RunEventType, RunStatus, ToolCallStatus
from kernel_providers import OpenAIProvider
from kernel_runtime import ModelRouter, RetryPolicy, RunExecutionService
from kernel_storage import AgentRepository, RunRepository, ToolCallRepository
from kernel_storage.models import ModelUsageRecord
from kernel_tools import ToolMetadata, ToolRegistry
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker


class ContractTool:
    metadata = ToolMetadata(
        name="contract_read",
        description="Return synthetic test data without external I/O.",
        input_schema={
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
            "additionalProperties": False,
        },
        risk_level=RiskLevel.READ_ONLY,
    )

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(arguments)
        return {"value": "fixture-result", "key": arguments["key"]}


def _queue(
    factory: sessionmaker[Session], *, fallback: bool = False, fallback_ref: str = "openai:backup"
) -> UUID:
    with factory() as session:
        agent = AgentRepository(session).create(name="wire-contract")
        runs = RunRepository(session)
        payload: dict[str, Any] = {"task": "Read fixture key", "model": "openai:primary"}
        if fallback:
            payload["fallback_models"] = [fallback_ref]
        run = runs.create(agent_id=agent.id, input_payload=payload)
        runs.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        return run.id


def _success(model: str = "primary") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": model,
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Used fixture-result.", "annotations": []}
                    ],
                }
            ],
            "usage": {"input_tokens": 3, "output_tokens": 2},
        },
    )


def _failure(kind: str, request: httpx.Request) -> httpx.Response:
    if kind == "read_timeout":
        raise httpx.ReadTimeout("synthetic-sensitive-transport", request=request)
    if kind == "connect_error":
        raise httpx.ConnectError("synthetic-sensitive-transport", request=request)
    status = 429 if kind == "rate_limit" else 503
    return httpx.Response(
        status,
        json={
            "error": {
                "code": "rate_limit_exceeded" if status == 429 else "server_is_overloaded",
                "message": "synthetic-sensitive-body",
            }
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("reasoning_mode", ["none", "stored", "encrypted"])
@pytest.mark.parametrize(
    ("failure_kind", "failures", "succeeds", "followup_count"),
    [
        ("overloaded", 0, True, 1),
        ("overloaded", 2, True, 3),
        ("overloaded", 3, False, 3),
        ("rate_limit", 2, True, 3),
        ("read_timeout", 3, False, 3),
        ("unauthorized", 1, False, 1),
    ],
)
async def test_native_tool_round_trip_uses_responses_wire_contract(
    postgres_session_factory: sessionmaker[Session],
    reasoning_mode: str,
    failure_kind: str,
    failures: int,
    succeeds: bool,
    followup_count: int,
) -> None:
    requests: list[dict[str, Any]] = []
    tool = ContractTool()
    registry = ToolRegistry()
    registry.register(tool)
    native_call = {
        "type": "function_call",
        "id": "fc_item_not_the_call_id",
        "call_id": "call_contract_1",
        "name": "contract_read",
        "arguments": '{"key":"alpha"}',
        "status": "completed",
    }
    native_output: list[dict[str, Any]] = [native_call]
    if reasoning_mode != "none":
        reasoning: dict[str, Any] = {
            "type": "reasoning",
            "id": "rs_fixture",
            "summary": [],
            "status": "completed",
        }
        if reasoning_mode == "encrypted":
            reasoning["encrypted_content"] = "synthetic-opaque-reasoning"
        native_output = [
            reasoning,
            {
                "type": "message",
                "id": "msg_fixture",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {"type": "output_text", "text": "Checking fixture.", "annotations": []}
                ],
            },
            native_call,
        ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://provider.invalid/v1/responses"
        assert request.headers["authorization"] == "Bearer synthetic-test-key"
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["model"] == "primary"
        user_item = {
            "role": "user",
            "content": [{"type": "input_text", "text": "Read fixture key"}],
        }
        if len(requests) == 1:
            assert payload["input"] == [user_item]
            assert payload["tools"] == [
                {
                    "type": "function",
                    "name": "contract_read",
                    "description": tool.metadata.description,
                    "parameters": tool.metadata.input_schema,
                }
            ]
            assert payload["tool_choice"] == "auto"
            return httpx.Response(
                200,
                json={
                    "model": "primary",
                    "output": native_output,
                    "usage": {"input_tokens": 5, "output_tokens": 1},
                },
            )
        assert len(requests) <= 4, "No hidden adapter retries or tool replay"
        assert len(payload["input"]) == len(native_output) + 2
        assert payload["input"][0] == user_item
        assert payload["input"][1:-1] == native_output
        output = payload["input"][-1]
        assert output["type"] == "function_call_output"
        assert output["call_id"] == "call_contract_1"
        result = json.loads(output["output"])
        assert result["provider_tool_call_id"] == "call_contract_1"
        assert result["tool_name"] == "contract_read"
        assert result["result"] == {"value": "fixture-result", "key": "alpha"}
        assert UUID(result["tool_call_id"])
        assert payload["tools"] == requests[0]["tools"]
        assert payload["tool_choice"] == "auto"
        if len(requests) - 1 <= failures:
            if failure_kind == "unauthorized":
                return httpx.Response(401, json={"error": {"code": "invalid_api_key"}})
            return _failure(failure_kind, request)
        return _success()

    provider = OpenAIProvider(
        api_key="synthetic-test-key",
        base_url="https://provider.invalid/v1",
        transport=httpx.MockTransport(handler),
    )
    fallback_calls = 0

    def fallback_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal fallback_calls
        fallback_calls += 1
        return _success("backup")

    fallback_provider = OpenAIProvider(
        api_key="other-test-key",
        base_url="https://other-provider.invalid/v1",
        transport=httpx.MockTransport(fallback_handler),
    )
    run_id = _queue(postgres_session_factory, fallback=True, fallback_ref="other:backup")
    service = RunExecutionService(
        router=ModelRouter({"openai": provider, "other": fallback_provider}),
        tool_registry=registry,
        retry_policy=RetryPolicy(provider_max_attempts=3),
    )
    with postgres_session_factory() as session:
        result = await service.execute(run_id=run_id, repository=RunRepository(session))
    with postgres_session_factory() as session:
        stored = RunRepository(session).get(run_id)
        assert stored is not None
        (tool_call,) = ToolCallRepository(session).list_for_run(run_id)
        events = RunRepository(session).list_events(run_id)
        assert stored.status == result.status
        assert tool_call.provider_tool_call_id == "call_contract_1"
        assert tool_call.raw_provider_payload == native_call
        assert tool_call.status is ToolCallStatus.SUCCEEDED
        assert tool_call.result == {"value": "fixture-result", "key": "alpha"}
        returned = json.loads(requests[1]["input"][-1]["output"])
        assert returned["tool_call_id"] == str(tool_call.id)
        assert returned["result"] == tool_call.result
        expected_error = {
            "overloaded": "provider_unavailable",
            "rate_limit": "rate_limit",
            "read_timeout": "provider_timeout",
            "unauthorized": "openai_status_error",
        }[failure_kind]
        retries = [e for e in events if e.type is RunEventType.MODEL_CALL_RETRYING]
        assert [e.payload["attempt"] for e in retries] == list(range(2, followup_count + 1))
        assert all(e.payload["phase"] == "tool_followup" for e in retries)
        assert all(e.payload["max_attempts"] == 3 for e in retries)
        assert all(e.payload["tool_call_id"] == str(tool_call.id) for e in retries)
        assert all(e.payload["provider_tool_call_id"] == "call_contract_1" for e in retries)
        assert all(e.payload["error_type"] == expected_error for e in retries)
        assert [e.type for e in events] == [
            RunEventType.RUN_CREATED,
            RunEventType.RUN_QUEUED,
            RunEventType.RUN_STARTED,
            RunEventType.TOOL_CALL_REQUESTED,
            RunEventType.POLICY_EVALUATED,
            RunEventType.TOOL_CALL_COMPLETED,
            *([RunEventType.MODEL_CALL_RETRYING] * (followup_count - 1)),
            RunEventType.RUN_COMPLETED if succeeds else RunEventType.RUN_FAILED,
        ]
        usage = list(
            session.scalars(select(ModelUsageRecord).where(ModelUsageRecord.run_id == str(run_id)))
        )
        assert len(usage) == (2 if succeeds else 1)
        assert sum(u.input_tokens for u in usage) == (8 if succeeds else 5)
        assert sum(u.output_tokens for u in usage) == (3 if succeeds else 1)
        assert all(u.provider == "openai" and u.model == "primary" for u in usage)
        if not succeeds:
            assert stored.status is RunStatus.FAILED
            assert stored.error_type == expected_error
            assert stored.input_tokens_total == 5
            assert stored.output_tokens_total == 1
        else:
            assert stored.status is RunStatus.SUCCEEDED
            assert stored.output is not None
            assert stored.output["text"] == "Used fixture-result."
            assert stored.input_tokens_total == 8
            assert stored.output_tokens_total == 3
            assert stored.output["usage"]["input_tokens"] == 8
            assert stored.output["usage"]["output_tokens"] == 3
            assert events[-1].payload["attempt_count"] == 1 + followup_count
            assert events[-1].payload["fallback_used"] is False
    assert len(requests) == 1 + followup_count
    assert all(payload == requests[1] for payload in requests[1:])
    assert fallback_calls == 0
    assert tool.calls == [{"key": "alpha"}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "error_type"),
    [
        ("rate_limit", "rate_limit"),
        ("overloaded", "provider_unavailable"),
        ("read_timeout", "provider_timeout"),
        ("connect_error", "provider_unavailable"),
    ],
)
@pytest.mark.parametrize("outcome", ["retry_success", "fallback_success", "exhausted"])
async def test_actual_adapter_retry_and_fallback_are_bounded_and_persisted(
    postgres_session_factory: sessionmaker[Session], kind: str, error_type: str, outcome: str
) -> None:
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        succeed = (
            outcome == "retry_success"
            and len(requests) == 2
            or outcome == "fallback_success"
            and payload["model"] == "backup"
        )
        return _success(payload["model"]) if succeed else _failure(kind, request)

    provider = OpenAIProvider(api_key="synthetic-test-key", transport=httpx.MockTransport(handler))
    service = RunExecutionService(
        router=ModelRouter({"openai": provider}),
        retry_policy=RetryPolicy(provider_max_attempts=2),
    )
    run_id = _queue(postgres_session_factory, fallback=True)
    with postgres_session_factory() as session:
        await service.execute(run_id=run_id, repository=RunRepository(session))
    with postgres_session_factory() as session:
        runs = RunRepository(session)
        stored = runs.get(run_id)
        assert stored is not None
        events = runs.list_events(run_id)
        retries = [e for e in events if e.type is RunEventType.MODEL_CALL_RETRYING]
        fallbacks = [e for e in events if e.type is RunEventType.MODEL_FALLBACK_SELECTED]
        assert len(retries) == (2 if outcome == "exhausted" else 1)
        assert all(e.payload["attempt"] == 2 and e.payload["max_attempts"] == 2 for e in retries)
        assert all(e.payload["error_type"] == error_type for e in (*retries, *fallbacks))
        assert len(fallbacks) == (0 if outcome == "retry_success" else 1)
        if fallbacks:
            assert fallbacks[0].payload["from_model"] == "openai:primary"
            assert fallbacks[0].payload["to_model"] == "openai:backup"
        expected_models = {
            "retry_success": ["primary", "primary"],
            "fallback_success": ["primary", "primary", "backup"],
            "exhausted": ["primary", "primary", "backup", "backup"],
        }[outcome]
        assert [p["model"] for p in requests] == expected_models
        assert all(p["input"] == requests[0]["input"] for p in requests)
        assert requests[0]["input"] == [
            {"role": "user", "content": [{"type": "input_text", "text": "Read fixture key"}]}
        ]
        assert "synthetic-sensitive" not in str([e.payload for e in events])
        if outcome == "exhausted":
            assert stored.status is RunStatus.FAILED
            assert stored.error_type == error_type
        else:
            assert stored.status is RunStatus.SUCCEEDED
            assert events[-1].payload["attempt_count"] == len(expected_models)
            assert events[-1].payload["fallback_used"] == (outcome == "fallback_success")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "code", "error_type"),
    [
        (400, "bad_request", "openai_status_error"),
        (401, "invalid_api_key", "openai_status_error"),
        (403, "forbidden", "openai_status_error"),
        (404, "model_not_found", "openai_status_error"),
        (422, "invalid_input", "openai_status_error"),
        (429, "insufficient_quota", "openai_quota_exhausted"),
        (429, "credit_balance_exhausted", "openai_quota_exhausted"),
    ],
)
async def test_nontransient_http_failure_never_retries_or_falls_back(
    postgres_session_factory: sessionmaker[Session], status: int, code: str, error_type: str
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, json={"error": {"code": code}})

    provider = OpenAIProvider(api_key="test", transport=httpx.MockTransport(handler))
    run_id = _queue(postgres_session_factory, fallback=True)
    with postgres_session_factory() as session:
        result = await RunExecutionService(provider=provider).execute(
            run_id=run_id, repository=RunRepository(session)
        )
        assert result.status is RunStatus.FAILED
        assert result.error_type == error_type
        assert [e.type for e in RunRepository(session).list_events(run_id)] == [
            RunEventType.RUN_CREATED,
            RunEventType.RUN_QUEUED,
            RunEventType.RUN_STARTED,
            RunEventType.RUN_FAILED,
        ]
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_item",
    [
        {"type": "reasoning", "summary": []},
        {"type": "reasoning", "id": "rs_bad", "summary": "not-a-list"},
        {"type": "reasoning", "id": "rs_bad", "summary": [], "encrypted_content": {}},
        {"type": "reasoning", "id": "rs_bad", "summary": [], "status": "incomplete"},
        {"type": "reasoning", "id": "rs_bad", "summary": [], "content": [{"type": "unknown"}]},
        {"type": "web_search_call", "id": "unsupported_native_tool"},
    ],
)
async def test_unreplayable_native_history_fails_before_tool_execution(
    postgres_session_factory: sessionmaker[Session], bad_item: dict[str, Any]
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "model": "primary",
                "output": [
                    bad_item,
                    {
                        "type": "function_call",
                        "call_id": "call_safe",
                        "name": "contract_read",
                        "arguments": '{"key":"alpha"}',
                    },
                ],
            },
        )

    tool = ContractTool()
    registry = ToolRegistry()
    registry.register(tool)
    run_id = _queue(postgres_session_factory, fallback=True)
    service = RunExecutionService(
        provider=OpenAIProvider(api_key="test", transport=httpx.MockTransport(handler)),
        tool_registry=registry,
        retry_policy=RetryPolicy(provider_max_attempts=3),
    )
    with postgres_session_factory() as session:
        result = await service.execute(run_id=run_id, repository=RunRepository(session))
        assert result.status is RunStatus.FAILED
        assert result.error_type == "openai_invalid_tool_history"
        assert ToolCallRepository(session).list_for_run(run_id) == []
    assert calls == 1
    assert tool.calls == []
