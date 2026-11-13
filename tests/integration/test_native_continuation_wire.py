"""Multi-round Responses wire history survives two approval/database reopens."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from agent_kernel_api.main import create_app
from agent_kernel_worker.main import _create_worker
from fastapi.testclient import TestClient
from kernel_core import ApprovalStatus, RiskLevel, RunEventType, RunStatus, ToolCallStatus
from kernel_identity import PrincipalType, WorkspaceRole
from kernel_providers import OpenAIProvider
from kernel_runtime import ExecutionLimits, RetryPolicy, RunExecutionService
from kernel_storage import (
    AgentRepository,
    ApiKeyRepository,
    ApprovalRepository,
    Base,
    PrincipalRepository,
    RunRepository,
    ToolCallRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from kernel_storage.models import ModelUsageRecord
from kernel_tools import ToolMetadata, ToolRegistry
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(params=["sqlite", "postgres"])
def native_wire_url(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[URL]:
    admin = None
    schema = f"test_native_wire_{uuid4().hex}"
    if request.param == "postgres":
        source = os.getenv("AGENT_KERNEL_TEST_POSTGRES_URL")
        if not source:
            pytest.skip("Set AGENT_KERNEL_TEST_POSTGRES_URL for PostgreSQL wire contracts.")
        source_url = make_url(source)
        assert source_url.get_backend_name() == "postgresql"
        assert source_url.database and source_url.database.casefold() != "appdata"
        admin = create_engine(source_url)
        url = source_url.update_query_dict({"options": f"-csearch_path={schema}"})
    else:
        url = make_url(f"sqlite+pysqlite:///{tmp_path / 'native-wire.db'}")
    schema_created = False
    engine = create_engine(url)
    try:
        if admin is not None:
            with admin.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            schema_created = True
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT current_schema()")) == schema
        Base.metadata.create_all(engine)
        engine.dispose()
        yield url
    finally:
        engine.dispose()
        if admin is not None:
            try:
                if schema_created:
                    with admin.begin() as connection:
                        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            finally:
                admin.dispose()


def test_worker_native_approval_resumes_through_default_api_runner_with_scope_checks(
    native_wire_url: URL, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specifications = [
        ("entry_read_one", "read-one", False),
        ("entry_write_one", "write-one", True),
        ("entry_read_two", "read-two", False),
        ("entry_write_two", "write-two", True),
    ]
    effects: list[tuple[str, str]] = []
    trace: list[str] = []
    registry = ToolRegistry()
    for name, _, write in specifications:
        registry.register(WireTool(name, write=write, effects=effects, trace=trace))
    native_calls = [
        [
            _native_call(round_number + 1, index, name, key)
            for index, (name, key, _) in enumerate(
                specifications[round_number * 2 : (round_number + 1) * 2]
            )
        ]
        for round_number in range(2)
    ]
    native_batches = [
        _native_batch(index + 1, calls, "encrypted") for index, calls in enumerate(native_calls)
    ]
    requests: list[dict[str, Any]] = []
    providers: list[OpenAIProvider] = []
    user_item = {
        "role": "user",
        "content": [{"type": "input_text", "text": "Finish the API-reviewed batches."}],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://entry-wire.invalid/v1/responses"
        assert request.headers["authorization"] == "Bearer synthetic-entry-wire-key"
        payload = json.loads(request.content)
        requests.append(payload)
        index = len(requests) - 1
        assert index < 3, "Unexpected provider replay through an entrypoint"
        assert len(effects) == index * 2
        trace.append(f"provider:{index + 1}")
        assert payload["model"] == "entry-model"
        assert payload["tool_choice"] == "auto"
        assert [tool["name"] for tool in payload["tools"]] == [
            name for name, _, _ in specifications
        ]
        if index:
            assert payload["tools"] == requests[0]["tools"]
        expected_input: list[dict[str, Any]] = [user_item]
        for round_number in range(index):
            expected_input.extend(native_batches[round_number])
            for call_index, call in enumerate(native_calls[round_number]):
                output = payload["input"][len(expected_input)]
                assert set(output) == {"type", "call_id", "output"}
                assert output["type"] == "function_call_output"
                assert output["call_id"] == call["call_id"]
                result = json.loads(output["output"])
                assert UUID(result["tool_call_id"])
                ordinal = round_number * 2 + call_index + 1
                name, key, _ = specifications[ordinal - 1]
                assert result == {
                    "tool_call_id": result["tool_call_id"],
                    "provider_tool_call_id": call["call_id"],
                    "tool_name": name,
                    "result": {"tool": name, "key": key, "ordinal": ordinal},
                }
                expected_input.append(output)
        assert payload["input"] == expected_input
        if index == 2:
            assert payload["input"][: len(requests[1]["input"])] == requests[1]["input"]
        output_items = (
            native_batches[index]
            if index < 2
            else [
                {
                    "type": "message",
                    "id": "msg_entry_final",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {"type": "output_text", "text": "API continuation finished both batches."}
                    ],
                }
            ]
        )
        return httpx.Response(
            200,
            json={
                "model": "entry-model",
                "status": "completed",
                "output": output_items,
                "usage": {"input_tokens": 3, "output_tokens": 1},
            },
        )

    def offline_openai_provider() -> OpenAIProvider:
        provider = OpenAIProvider(
            api_key="synthetic-entry-wire-key",
            base_url="https://entry-wire.invalid/v1",
            transport=httpx.MockTransport(handler),
        )
        providers.append(provider)
        return provider

    def shared_registry(**_: object) -> ToolRegistry:
        return registry

    # Keep the production router, runner, permission checks and repositories intact.
    monkeypatch.setattr("kernel_runtime.router.OpenAIProvider", offline_openai_provider)
    monkeypatch.setattr("agent_kernel_api.main.create_rag_tool_registry", shared_registry)
    monkeypatch.setenv("AGENT_KERNEL_EXTERNAL_TOOLS_CONFIG", "")
    monkeypatch.setenv("AGENT_KERNEL_EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("AGENT_KERNEL_OBJECT_STORE_BACKEND", "local")
    monkeypatch.setenv("AGENT_KERNEL_OBJECT_STORE_ROOT", str(tmp_path / "objects"))
    monkeypatch.setenv("AGENT_KERNEL_RUN_QUEUE_BACKEND", "database")
    for setting in (
        "AGENT_KERNEL_RATE_LIMIT_REQUESTS",
        "AGENT_KERNEL_RATE_LIMIT_PRINCIPAL_REQUESTS",
        "AGENT_KERNEL_RATE_LIMIT_API_KEY_REQUESTS",
    ):
        monkeypatch.setenv(setting, "0")

    engine = create_engine(native_wire_url)
    factory = sessionmaker(engine, expire_on_commit=False)
    headers: dict[str, dict[str, str]] = {}
    try:
        with factory() as session:
            workspace_a = WorkspaceRepository(session).create(name="Wire A", slug="wire-entry-a")
            workspace_b = WorkspaceRepository(session).create(name="Wire B", slug="wire-entry-b")
            for label, workspace, role in (
                ("a", workspace_a, WorkspaceRole.OPERATOR),
                ("b", workspace_b, WorkspaceRole.OPERATOR),
                ("viewer", workspace_a, WorkspaceRole.VIEWER),
            ):
                principal = PrincipalRepository(session).create(
                    type=PrincipalType.USER, display_name=f"Wire {label}"
                )
                WorkspaceMembershipRepository(session).assign(
                    principal_id=principal.id, workspace_id=workspace.id, role=role
                )
                credential = ApiKeyRepository(session).issue(
                    workspace_id=workspace.id,
                    principal_id=principal.id,
                    name=f"Wire {label} key",
                    plaintext_key=f"ak_synthetic_wire_entry_{label}",
                )
                assert credential is not None
                headers[label] = {"Authorization": f"Bearer {credential.plaintext_key}"}

        with TestClient(create_app(session_factory=factory, api_key_auth_enabled=True)) as client:
            created_agent = client.post(
                "/v1/agents", json={"name": "entrypoint-wire"}, headers=headers["a"]
            )
            assert created_agent.status_code == 201, created_agent.text
            created_run = client.post(
                f"/v1/agents/{created_agent.json()['id']}/runs",
                json={
                    "input": {
                        "task": "Finish the API-reviewed batches.",
                        "model": "openai:entry-model",
                    }
                },
                headers=headers["a"],
            )
            assert created_run.status_code == 201, created_run.text
            run_id = UUID(created_run.json()["id"])
            queued = client.post(f"/v1/runs/{run_id}/queue", headers=headers["a"])
            assert queued.status_code == 200 and queued.json()["status"] == "queued"
        assert requests == [] and effects == []

        worker = _create_worker(session_factory=factory, registry=registry)
        batch = asyncio.run(worker.run_once(limit=1))
        assert batch.processed_count == 1 and batch.failed_count == 0, batch
        assert batch.runs[0].run_id == run_id
        assert batch.runs[0].status is RunStatus.WAITING_APPROVAL
        assert len(requests) == 1 and effects == [("entry_read_one", "read-one")]

        # This is a fresh API app using create_app's default runner, not the worker's service.
        with TestClient(create_app(session_factory=factory, api_key_auth_enabled=True)) as client:
            for round_number in range(2):
                listed = client.get("/v1/approvals?status=requested", headers=headers["a"])
                assert listed.status_code == 200
                assert len(listed.json()) == 1
                approval_id = listed.json()[0]["id"]
                assert listed.json()[0]["run_id"] == str(run_id)
                before_denials = (list(trace), len(requests), list(effects))
                hidden = client.get("/v1/approvals?status=requested", headers=headers["b"])
                assert hidden.status_code == 200 and hidden.json() == []
                assert client.get(f"/v1/runs/{run_id}", headers=headers["b"]).status_code == 404
                assert (
                    client.get(f"/v1/approvals/{approval_id}", headers=headers["b"]).status_code
                    == 404
                )
                for caller, expected_status in (("b", 404), ("viewer", 403)):
                    denied_approval = client.post(
                        f"/v1/approvals/{approval_id}/approve", json={}, headers=headers[caller]
                    )
                    denied_resume = client.post(
                        f"/v1/runs/{run_id}/resume",
                        json={"approval_id": approval_id},
                        headers=headers[caller],
                    )
                    assert denied_approval.status_code == expected_status
                    assert denied_resume.status_code == expected_status
                unauthenticated = client.post(
                    f"/v1/runs/{run_id}/resume", json={"approval_id": approval_id}
                )
                assert unauthenticated.status_code == 401
                undecided = client.post(
                    f"/v1/runs/{run_id}/resume",
                    json={"approval_id": approval_id},
                    headers=headers["a"],
                )
                assert undecided.status_code == 409
                assert (trace, len(requests), effects) == before_denials
                with factory() as session:
                    pending = ApprovalRepository(session).get(UUID(approval_id))
                    assert pending is not None and pending.status is ApprovalStatus.REQUESTED
                    waiting = RunRepository(session).get(run_id)
                    assert waiting is not None and waiting.status is RunStatus.WAITING_APPROVAL

                approved = client.post(
                    f"/v1/approvals/{approval_id}/approve",
                    json={"decision_note": "Reviewed through the authenticated API."},
                    headers=headers["a"],
                )
                assert approved.status_code == 200 and approved.json()["status"] == "approved"
                resumed = client.post(
                    f"/v1/runs/{run_id}/resume",
                    json={"approval_id": approval_id},
                    headers=headers["a"],
                )
                assert resumed.status_code == 200, resumed.text
                assert resumed.json()["status"] == (
                    "waiting_approval" if round_number == 0 else "succeeded"
                ), resumed.json()
                assert len(requests) == round_number + 2
                completed_count = 3 if round_number == 0 else 4
                assert effects == [(name, key) for name, key, _ in specifications[:completed_count]]
                before_replay = list(trace)
                duplicate_resume = client.post(
                    f"/v1/runs/{run_id}/resume",
                    json={"approval_id": approval_id},
                    headers=headers["a"],
                )
                assert duplicate_resume.status_code == 409
                assert trace == before_replay

            completed = client.get(f"/v1/runs/{run_id}", headers=headers["a"])
            assert completed.status_code == 200
            assert completed.json()["status"] == "succeeded"
            assert completed.json()["output"]["text"] == "API continuation finished both batches."
            assert completed.json()["output"]["usage"]["input_tokens"] == 9
            assert completed.json()["output"]["usage"]["output_tokens"] == 3
        assert len(providers) == 3, "Setup API, worker and resumed API must build their own router"
        assert trace == [
            "provider:1",
            "tool:entry_read_one:read-one",
            "tool:entry_write_one:write-one",
            "provider:2",
            "tool:entry_read_two:read-two",
            "tool:entry_write_two:write-two",
            "provider:3",
        ]
        assert asyncio.run(worker.run_once(limit=1)).processed_count == 0
        with factory() as session:
            stored = RunRepository(session).get(run_id)
            assert stored is not None and stored.workspace_id == workspace_a.id
            assert stored.status is RunStatus.SUCCEEDED
            calls = ToolCallRepository(session).list_for_run(run_id)
            assert len(calls) == 4
            assert all(call.status is ToolCallStatus.SUCCEEDED for call in calls)
            assert [call.raw_provider_payload for call in calls] == [
                call for native_batch in native_calls for call in native_batch
            ]
            outputs = [
                item for item in requests[-1]["input"] if item.get("type") == "function_call_output"
            ]
            assert [json.loads(item["output"])["tool_call_id"] for item in outputs] == [
                str(call.id) for call in calls
            ]
            approvals = ApprovalRepository(session).list_for_run(run_id)
            assert len(approvals) == 2
            assert all(item.status is ApprovalStatus.APPROVED for item in approvals)
            events = RunRepository(session).list_events(run_id)
            assert [
                event.payload["tool_call_id"]
                for event in events
                if event.type is RunEventType.TOOL_CALL_COMPLETED
            ] == [str(call.id) for call in calls]
            assert events[-1].type is RunEventType.RUN_COMPLETED
    finally:
        engine.dispose()


class WireTool:
    def __init__(
        self,
        name: str,
        *,
        write: bool,
        effects: list[tuple[str, str]],
        trace: list[str],
    ) -> None:
        self.metadata = ToolMetadata(
            name=name,
            description=f"Synthetic {name} operation; no external I/O.",
            input_schema={
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
                "additionalProperties": False,
            },
            risk_level=RiskLevel.EXTERNAL_WRITE if write else RiskLevel.READ_ONLY,
        )
        self.effects = effects
        self.trace = trace

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        key = arguments["key"]
        assert isinstance(key, str)
        effect = (self.metadata.name, key)
        assert effect not in self.effects, "A previously executed native call was replayed"
        self.effects.append(effect)
        self.trace.append(f"tool:{self.metadata.name}:{key}")
        return {"tool": self.metadata.name, "key": key, "ordinal": len(self.effects)}


def _native_call(round_number: int, index: int, name: str, key: str) -> dict[str, Any]:
    return {
        "type": "function_call",
        "id": f"fc_item_round_{round_number}_{index}",
        "call_id": f"call_round_{round_number}_{index}",
        "name": name,
        "arguments": json.dumps({"key": key}, separators=(", ", " : ")),
        "status": "completed",
    }


def _native_batch(
    round_number: int, calls: list[dict[str, Any]], reasoning_mode: str
) -> list[dict[str, Any]]:
    reasoning: dict[str, Any] = {
        "type": "reasoning",
        "id": f"rs_round_{round_number}",
        "status": "completed",
        "summary": [{"type": "summary_text", "text": f"Synthetic summary {round_number}."}],
    }
    if reasoning_mode == "encrypted":
        reasoning["encrypted_content"] = f"synthetic-opaque-content-{round_number}"
    else:
        reasoning["content"] = [
            {"type": "reasoning_text", "text": f"Synthetic reasoning fixture {round_number}."}
        ]
    message = {
        "type": "message",
        "id": f"msg_round_{round_number}",
        "role": "assistant",
        "status": "completed",
        "content": [
            {
                "type": "output_text",
                "text": f"Preparing batch {round_number}.",
                "annotations": [],
            }
        ],
    }
    # Different native item orders detect reconstruction that moves reasoning/messages.
    if round_number == 1:
        return [reasoning, calls[0], message, *calls[1:]]
    return [message, reasoning, *calls]


@pytest.mark.asyncio
@pytest.mark.parametrize("reasoning_mode", ["stored", "encrypted"])
async def test_two_native_batches_preserve_wire_history_across_approval_reopens(
    native_wire_url: URL, reasoning_mode: str
) -> None:
    specifications = [
        ("wire_lookup", "lookup-one", False),
        ("wire_write_note", "draft-one", True),
        ("wire_verify", "verify-one", False),
        ("wire_summarize", "summary-two", False),
        ("wire_publish", "release-two", True),
        ("wire_audit", "audit-two", False),
    ]
    native_calls = [
        [
            _native_call(round_number + 1, index, name, key)
            for index, (name, key, _) in enumerate(
                specifications[round_number * 3 : (round_number + 1) * 3]
            )
        ]
        for round_number in range(2)
    ]
    native_batches = [
        _native_batch(index + 1, calls, reasoning_mode) for index, calls in enumerate(native_calls)
    ]
    effects: list[tuple[str, str]] = []
    trace: list[str] = []
    requests: list[dict[str, Any]] = []
    wire_internal_ids: dict[str, str] = {}
    user_item = {
        "role": "user",
        "content": [{"type": "input_text", "text": "Complete both reviewed fixture batches."}],
    }
    usage = [(11, 2), (13, 3), (17, 5)]

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://native-wire.invalid/v1/responses"
        assert request.headers["authorization"] == "Bearer synthetic-native-wire-key"
        payload = json.loads(request.content)
        requests.append(payload)
        index = len(requests) - 1
        assert index < 3, "Unexpected model replay or hidden HTTP retry"
        assert len(effects) == index * 3, "Model sent before its entire approved batch completed"
        trace.append(f"provider:{index + 1}")
        assert payload["model"] == "wire-model"
        assert payload["tool_choice"] == "auto"
        assert payload["max_output_tokens"] == 64
        assert [tool["name"] for tool in payload["tools"]] == [
            name for name, _, _ in specifications
        ]
        if index:
            assert payload["tools"] == requests[0]["tools"]
        expected_input: list[dict[str, Any]] = [user_item]
        for round_number in range(index):
            expected_input.extend(native_batches[round_number])
            for call_index, call in enumerate(native_calls[round_number]):
                output = payload["input"][len(expected_input)]
                assert output["type"] == "function_call_output"
                assert output["call_id"] == call["call_id"]
                result = json.loads(output["output"])
                internal_id = result["tool_call_id"]
                assert UUID(internal_id)
                assert internal_id not in {call["id"], call["call_id"]}
                assert wire_internal_ids.setdefault(call["call_id"], internal_id) == internal_id
                ordinal = round_number * 3 + call_index + 1
                name, key, _ = specifications[ordinal - 1]
                expected_result = {
                    "tool_call_id": internal_id,
                    "provider_tool_call_id": call["call_id"],
                    "tool_name": name,
                    "result": {"tool": name, "key": key, "ordinal": ordinal},
                }
                assert result == expected_result
                expected_input.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(expected_result, sort_keys=True),
                    }
                )
        assert payload["input"] == expected_input
        if index == 2:
            assert payload["input"][: len(requests[1]["input"])] == requests[1]["input"]
        output_items = (
            native_batches[index]
            if index < 2
            else [
                {
                    "type": "message",
                    "id": "msg_final_answer",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Both reviewed batches are complete.",
                            "annotations": [],
                        }
                    ],
                }
            ]
        )
        return httpx.Response(
            200,
            json={
                "id": f"resp_fixture_{index + 1}",
                "model": "wire-model",
                "status": "completed",
                "output": output_items,
                "usage": {"input_tokens": usage[index][0], "output_tokens": usage[index][1]},
            },
        )

    run_id: UUID | None = None
    approval_ids: list[UUID] = []
    for segment in range(3):
        # Only the simulated external-effects ledger and HTTP recorder cross this boundary.
        engine = create_engine(native_wire_url)
        factory = sessionmaker(engine, expire_on_commit=False)
        registry = ToolRegistry()
        for name, _, write in specifications:
            registry.register(WireTool(name, write=write, effects=effects, trace=trace))
        service = RunExecutionService(
            provider=OpenAIProvider(
                api_key="synthetic-native-wire-key",
                base_url="https://native-wire.invalid/v1",
                transport=httpx.MockTransport(handler),
            ),
            tool_registry=registry,
            retry_policy=RetryPolicy(provider_max_attempts=1, tool_max_attempts=1),
            execution_limits=ExecutionLimits(
                max_model_calls=3, max_tool_calls=6, max_output_tokens=64
            ),
        )
        try:
            if segment == 0:
                with factory() as session:
                    agent = AgentRepository(session).create(name="native-continuation-wire")
                    runs = RunRepository(session)
                    run = runs.create(
                        agent_id=agent.id,
                        input_payload={
                            "task": "Complete both reviewed fixture batches.",
                            "model": "openai:wire-model",
                        },
                    )
                    run_id = run.id
                    runs.apply_transition(
                        run_id=run_id,
                        status=RunStatus.QUEUED,
                        event_type=RunEventType.RUN_QUEUED,
                        payload={"from_status": "created", "to_status": "queued"},
                    )
                with factory() as session:
                    result = await service.execute(run_id=run_id, repository=RunRepository(session))
            else:
                assert run_id is not None
                with factory() as session:
                    approvals = ApprovalRepository(session)
                    pending = [
                        item
                        for item in approvals.list_for_run(run_id)
                        if item.status is ApprovalStatus.REQUESTED
                    ]
                    assert len(pending) == 1
                    approval_ids.append(pending[0].id)
                    assert approvals.approve(approval_id=pending[0].id) is not None
                with factory() as session:
                    result = await service.resume(
                        run_id=run_id,
                        repository=RunRepository(session),
                        approval_repository=ApprovalRepository(session),
                        tool_call_repository=ToolCallRepository(session),
                        approval_id=approval_ids[-1],
                    )
            assert len(requests) == segment + 1
            completed_count = (1, 4, 6)[segment]
            assert effects == [(name, key) for name, key, _ in specifications[:completed_count]]
            assert result.status is (
                RunStatus.WAITING_APPROVAL if segment < 2 else RunStatus.SUCCEEDED
            ), result.error_message
            assert run_id is not None
            with factory() as session:
                calls = ToolCallRepository(session).list_for_run(run_id)
                if segment < 2:
                    assert result.output is None
                    assert [call.status for call in calls] == [
                        *([ToolCallStatus.SUCCEEDED] * completed_count),
                        ToolCallStatus.WAITING_APPROVAL,
                        ToolCallStatus.REQUESTED,
                    ]
                else:
                    assert all(call.status is ToolCallStatus.SUCCEEDED for call in calls)
        finally:
            engine.dispose()

    assert result.output is not None
    assert result.output["text"] == "Both reviewed batches are complete."
    assert result.input_tokens_total == 41 and result.output_tokens_total == 10
    assert result.output["usage"]["input_tokens"] == 41
    assert result.output["usage"]["output_tokens"] == 10
    assert len(set(approval_ids)) == 2
    assert trace == [
        "provider:1",
        "tool:wire_lookup:lookup-one",
        "tool:wire_write_note:draft-one",
        "tool:wire_verify:verify-one",
        "provider:2",
        "tool:wire_summarize:summary-two",
        "tool:wire_publish:release-two",
        "tool:wire_audit:audit-two",
        "provider:3",
    ]

    engine = create_engine(native_wire_url)
    try:
        with Session(engine) as session:
            assert run_id is not None
            stored = RunRepository(session).get(run_id)
            assert stored is not None and stored.status is RunStatus.SUCCEEDED
            calls = ToolCallRepository(session).list_for_run(run_id)
            all_native_calls = [call for batch in native_calls for call in batch]
            assert len(calls) == len(wire_internal_ids) == 6
            for ordinal, (call, native) in enumerate(zip(calls, all_native_calls, strict=True), 1):
                name, key, write = specifications[ordinal - 1]
                assert call.provider_name == "openai"
                assert call.provider_tool_call_id == native["call_id"]
                assert str(call.id) == wire_internal_ids[native["call_id"]]
                assert call.raw_provider_payload == native
                assert call.arguments == {"key": key}
                assert call.result == {"tool": name, "key": key, "ordinal": ordinal}
                assert call.requires_approval is write
            events = RunRepository(session).list_events(run_id)
            assert [
                event.payload["tool_call_id"]
                for event in events
                if event.type is RunEventType.TOOL_CALL_COMPLETED
            ] == [str(call.id) for call in calls]
            for event_type in (
                RunEventType.APPROVAL_REQUESTED,
                RunEventType.APPROVAL_APPROVED,
                RunEventType.RUN_WAITING_APPROVAL,
                RunEventType.RUN_RESUMING,
            ):
                assert sum(event.type is event_type for event in events) == 2
            assert events[-1].type is RunEventType.RUN_COMPLETED
            assert events[-1].payload["attempt_count"] == 3
            assert not any(
                event.type
                in {
                    RunEventType.MODEL_CALL_RETRYING,
                    RunEventType.TOOL_CALL_RETRYING,
                    RunEventType.MODEL_FALLBACK_SELECTED,
                }
                for event in events
            )
            model_usage = list(
                session.scalars(
                    select(ModelUsageRecord).where(ModelUsageRecord.run_id == str(run_id))
                )
            )
            assert len(model_usage) == 3
            assert sum(item.input_tokens for item in model_usage) == 41
            assert sum(item.output_tokens for item in model_usage) == 10
    finally:
        engine.dispose()
