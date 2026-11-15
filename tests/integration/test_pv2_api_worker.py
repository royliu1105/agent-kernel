"""Actual ASGI routes and queued Worker with PostgreSQL, fixture-only delegates."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from agent_kernel_api.main import create_app
from fastapi.testclient import TestClient
from kernel_core import RunStatus, ToolCallStatus
from kernel_providers import LLMFinishReason, LLMProviderError, LLMResponse, LLMToolCall
from kernel_runtime import QueuedRunWorker, RetryPolicy, RunExecutionService
from kernel_storage import ApprovalRepository, RunRepository, ToolCallRepository
from kernel_tools import ToolRegistry
from sqlalchemy.orm import Session, sessionmaker
from test_pv2_approval_observation import ObservedTool

from scripts.pv1_harness import Journal, read_events
from scripts.pv2_offline_harness import FixtureLedger
from scripts.pv2_runtime_fixture import RuntimeFixtureProvider

TASK = "PV2 fixture task"


def reply(*, tool: bool = False) -> LLMResponse:
    return LLMResponse(
        provider="pv2-fixture",
        model="fixture",
        text="" if tool else "fixture done",
        finish_reason=LLMFinishReason.TOOL_CALLS if tool else LLMFinishReason.STOP,
        tool_calls=(LLMToolCall(id="lookup-1", name="write", arguments={"value": "fixture"}),)
        if tool
        else (),
    )


def create_queued(client: TestClient) -> UUID:
    agent = client.post("/v1/agents", json={"name": "pv2-fixture"})
    assert agent.status_code == 201
    run = client.post(
        f"/v1/agents/{agent.json()['id']}/runs",
        json={"input": {"task": TASK, "model": "pv2-fixture:fixture"}},
    )
    assert run.status_code == 201
    run_id = UUID(run.json()["id"])
    assert client.post(f"/v1/runs/{run_id}/queue").status_code == 200
    return run_id


def register(ledger: FixtureLedger, *, api: bool = False) -> UUID:
    executor = uuid4()
    ledger.change(
        "register", executor=executor, role="api" if api else "worker", attestation=ledger.binding
    )
    return executor


@pytest.fixture
def ledger(tmp_path: Path) -> FixtureLedger:
    value = FixtureLedger(tmp_path / "manifest.jsonl", uuid4(), "b" * 64)
    value.create()
    return value


def registry(tool: ObservedTool) -> ToolRegistry:
    value = ToolRegistry()
    value.register(tool)
    return value


@pytest.mark.parametrize("decision", ["approve", "reject", "concurrent", "resume_retry"])
def test_api_queue_worker_and_new_api_executor_resume(
    postgres_session_factory: sessionmaker[Session],
    tmp_path: Path,
    ledger: FixtureLedger,
    decision: str,
) -> None:
    factory = postgres_session_factory
    initial_client = TestClient(create_app(session_factory=factory, api_key_auth_enabled=False))
    run_id = create_queued(initial_client)
    journals = tmp_path / "journals"
    journals.mkdir()
    worker_id = register(ledger)
    worker_journal = Journal(journals, ledger.case_id, worker_id)
    initial_tool = ObservedTool(worker_journal)
    initial = RuntimeFixtureProvider(ledger, worker_id, run_id, [reply(tool=True)], task=TASK)
    worker = QueuedRunWorker(
        session_factory=factory,
        execution_service=RunExecutionService(
            provider=initial, tool_registry=registry(initial_tool)
        ),
    )
    result = asyncio.run(worker.run_once())
    assert result.processed_count == 1 and result.runs[0].status is RunStatus.WAITING_APPROVAL
    assert asyncio.run(worker.run_once()).processed_count == 0
    assert initial.dispatches == 1 and initial_tool.calls == []
    assert [row.event for row in read_events(worker_journal.path)] == ["case_open"]
    worker_journal.append("case_close")
    with factory() as session:
        approval = ApprovalRepository(session).list_for_run(run_id)[0]
    api_id = register(ledger, api=True)
    api_journal = Journal(journals, ledger.case_id, api_id)
    resumed_tool = ObservedTool(api_journal)
    resumed = RuntimeFixtureProvider(
        ledger,
        api_id,
        run_id,
        [LLMProviderError("fixture uncertain continuation", error_type="rate_limit"), reply()]
        if decision == "resume_retry"
        else [reply()],
        task=TASK,
    )
    service = RunExecutionService(provider=resumed, tool_registry=registry(resumed_tool))
    app = create_app(session_factory=factory, execution_service=service, api_key_auth_enabled=False)
    client = TestClient(app)
    endpoint = f"/v1/runs/{run_id}/resume"
    payload = {"approval_id": str(approval.id)}
    assert client.post(endpoint, json=payload).status_code == 409
    assert resumed.dispatches == 0 and resumed_tool.calls == []
    action = "reject" if decision == "reject" else "approve"
    body = {"reason": "fixture denial"} if action == "reject" else {}
    first_decision = client.post(f"/v1/approvals/{approval.id}/{action}", json=body)
    assert first_decision.status_code == 200
    assert (
        client.post(f"/v1/approvals/{approval.id}/{action}", json=body).json()
        == first_decision.json()
    )
    if decision == "concurrent":

        def invoke(_: int) -> int:
            with TestClient(app) as concurrent_client:
                return int(concurrent_client.post(endpoint, json=payload).status_code)

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(invoke, range(2)))
        assert sorted(statuses) == [200, 409]
    else:
        assert client.post(endpoint, json=payload).status_code == 200
    assert client.post(endpoint, json=payload).status_code == 409
    approved = action == "approve"
    assert resumed.dispatches == int(approved)
    assert len(resumed_tool.calls) == int(approved)
    if approved:
        assert resumed.requests[0].messages[0].content == TASK
        assert any(message.role.value == "tool" for message in resumed.requests[0].messages)
    with factory() as session:
        stored = ToolCallRepository(session).get(approval.tool_call_id)
        assert stored is not None
        assert stored.status is (ToolCallStatus.SUCCEEDED if approved else ToolCallStatus.DENIED)
        run = RunRepository(session).get(run_id)
        assert run is not None
        assert run.status is (
            RunStatus.SUCCEEDED if approved and decision != "resume_retry" else RunStatus.FAILED
        )
    api_journal.append("case_close")
    if decision == "resume_retry":
        assert len(resumed.requests) == 2
        assert any(not attempt.complete for attempt in ledger.snapshot().attempts.values())
        assert ledger.observation(journals, {approval.tool_call_id: 1}).verdict == "unknown"
        return
    ledger.change("close", executor=api_id)
    observed = ledger.observation(journals, {approval.tool_call_id: int(approved)})
    assert observed.verdict == "pass"


@pytest.mark.parametrize("before_dispatch", [True, False])
def test_actual_worker_retry_cannot_bypass_unresolved_reservation(
    postgres_session_factory: sessionmaker[Session],
    ledger: FixtureLedger,
    before_dispatch: bool,
) -> None:
    factory = postgres_session_factory
    client = TestClient(create_app(session_factory=factory, api_key_auth_enabled=False))
    run_id = create_queued(client)
    provider = RuntimeFixtureProvider(
        ledger,
        register(ledger),
        run_id,
        [LLMProviderError("fixture rate limit", error_type="rate_limit"), reply()],
        task=TASK,
        failure_before_dispatch=before_dispatch,
    )
    delays: list[float] = []

    async def sleep(seconds: float) -> None:
        delays.append(seconds)

    service = RunExecutionService(
        provider=provider,
        retry_policy=RetryPolicy(provider_max_attempts=3),
        retry_sleep=sleep,
        retry_random=lambda: 0.5,
    )
    worker = QueuedRunWorker(session_factory=factory, execution_service=service)
    result = asyncio.run(worker.run_once())
    assert len(delays) == 1
    assert len(provider.requests) == 2 and provider.dispatches == 1
    assert result.runs[0].status is (RunStatus.SUCCEEDED if before_dispatch else RunStatus.FAILED)
    state = ledger.snapshot()
    assert len(state.attempts) == 1
    assert next(iter(state.attempts.values())).complete is before_dispatch
