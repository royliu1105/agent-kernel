"""Cancellation and late-result fencing with independent persisted sessions."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Literal
from uuid import UUID

import pytest
from kernel_core import RiskLevel, Run, RunEventType, RunStatus, WorkerLease, utc_now
from kernel_providers import (
    LLMFinishReason,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
)
from kernel_runtime import (
    QueuedRunWorker,
    RetryPolicy,
    RunExecutionService,
    StuckRunRecoveryService,
)
from kernel_storage import (
    AgentRepository,
    ApprovalRepository,
    ExecutionOwnershipError,
    RunRepository,
    ToolCallRepository,
    WorkerLeaseRepository,
)
from kernel_storage.models import WorkerLeaseRecord
from kernel_tools import ToolMetadata, ToolRegistry
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_execution_ownership import ownership_db as ownership_db

OperationKind = Literal["provider", "tool"]


class SuspendedOperation:
    """Release an actual awaited provider/tool result at a chosen race boundary."""

    name = "suspended"

    def __init__(self, *, suppress_cancellation: bool = False) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.cancel_seen = asyncio.Event()
        self.suppress_cancellation = suppress_cancellation
        self.calls = 0
        self.returned = 0
        self.metadata = ToolMetadata(
            name="suspended_tool",
            description="In-memory cancellation fixture; no external side effect.",
            input_schema={"type": "object", "additionalProperties": False},
            timeout_ms=30_000,
        )

    async def _wait(self) -> None:
        self.calls += 1
        self.started.set()
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancel_seen.set()
            if not self.suppress_cancellation:
                raise
            # Models a client returning a response after cancellation was requested.
            await self.release.wait()
        self.returned += 1

    async def complete(self, request: LLMRequest) -> LLMResponse:
        await self._wait()
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text="late provider result",
            usage=LLMUsage(input_tokens=12, output_tokens=3, estimated_cost=0.001),
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        await self._wait()
        return {"late_tool_result": True}


def _queued(factory: sessionmaker[Session], kind: OperationKind) -> UUID:
    with factory() as session:
        agent = AgentRepository(session).create(name="cancellation-fixture")
        repository = RunRepository(session)
        payload: dict[str, Any] = {"task": "wait", "model": "suspended:fixture"}
        if kind == "tool":
            payload["tool"] = {"name": "suspended_tool", "arguments": {}}
        run = repository.create(agent_id=agent.id, input_payload=payload)
        repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        return run.id


def _service(operation: SuspendedOperation) -> RunExecutionService:
    registry = ToolRegistry()
    registry.register(operation)
    return RunExecutionService(provider=operation, tool_registry=registry, lease_ttl_seconds=60)


async def _execute(
    factory: sessionmaker[Session], service: RunExecutionService, run_id: UUID
) -> Run:
    with factory() as session:
        return await service.execute(run_id=run_id, repository=RunRepository(session))


async def _cleanup(task: asyncio.Task[Run], operation: SuspendedOperation) -> None:
    operation.release.set()
    if not task.done():
        task.cancel()
    await asyncio.wait_for(asyncio.gather(task, return_exceptions=True), timeout=5)


def _lease(factory: sessionmaker[Session], run_id: UUID) -> WorkerLease:
    with factory() as session:
        lease = WorkerLeaseRepository(session).get_active(run_id=run_id)
        assert lease is not None
        return lease


def _expire(factory: sessionmaker[Session], lease: WorkerLease) -> None:
    with factory() as session:
        record = session.get(WorkerLeaseRecord, str(lease.id))
        assert record is not None
        record.expires_at = utc_now() - timedelta(seconds=1)
        session.commit()


def _assert_no_late_result(
    factory: sessionmaker[Session], run_id: UUID, *, status: RunStatus
) -> None:
    with factory() as session:
        repository = RunRepository(session)
        run = repository.get(run_id)
        assert run is not None
        assert run.status is status
        assert run.output is None, "Late output was committed after execution lost ownership."
        events = repository.list_events(run_id)
        assert RunEventType.RUN_COMPLETED not in [event.type for event in events]
        assert RunEventType.TOOL_CALL_COMPLETED not in [event.type for event in events]
        assert [event.sequence for event in events] == list(range(1, len(events) + 1))
        calls = ToolCallRepository(session).list_for_run(run_id)
        assert all(call.result is None for call in calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["provider", "tool"])
@pytest.mark.parametrize("boundary", ["cancel", "recovery", "replacement"])
async def test_late_result_cannot_cross_persisted_fence(
    ownership_db: sessionmaker[Session], kind: OperationKind, boundary: str
) -> None:
    run_id = _queued(ownership_db, kind)
    operation = SuspendedOperation()
    task = asyncio.create_task(_execute(ownership_db, _service(operation), run_id))
    try:
        await asyncio.wait_for(operation.started.wait(), timeout=5)
        old_lease = _lease(ownership_db, run_id)
        if boundary == "cancel":
            with ownership_db() as session:
                RunRepository(session).apply_transition(
                    run_id=run_id,
                    status=RunStatus.CANCELED,
                    event_type=RunEventType.RUN_CANCELED,
                    payload={"from_status": "running", "to_status": "canceled"},
                )
        elif boundary == "recovery":
            _expire(ownership_db, old_lease)
            recovered = StuckRunRecoveryService(session_factory=ownership_db).recover_once()
            assert recovered.recovered_count == 1
        else:
            _expire(ownership_db, old_lease)
            with ownership_db() as session:
                # Exercise the persisted fencing boundary, not automatic replay:
                # runtime does not normally requeue uncertain running executions.
                replacement = WorkerLeaseRepository(session).acquire(
                    run_id=run_id, worker_id="replacement", expected_status=RunStatus.RUNNING
                )
                assert replacement is not None
                RunRepository(session, lease_token=replacement.lease_token).complete(
                    run_id=run_id,
                    output_payload={"owner": "replacement"},
                    input_tokens_total=100,
                    output_tokens_total=20,
                    estimated_cost_total=0.025,
                    event_payload={"from_status": "running", "to_status": "succeeded"},
                )
                WorkerLeaseRepository(session).release(lease_token=replacement.lease_token)
        with ownership_db() as session:
            before = RunRepository(session).list_events(run_id)
        operation.release.set()
        with pytest.raises(ExecutionOwnershipError):
            await asyncio.wait_for(task, timeout=5)
        assert operation.calls == 1
        assert operation.returned == 1, "The late result must actually arrive at the write fence."
        with ownership_db() as session:
            repository = RunRepository(session)
            assert repository.list_events(run_id) == before, "Stale owner appended audit events."
            assert WorkerLeaseRepository(session).get_active(run_id=run_id) is None
            if boundary == "replacement":
                run = repository.get(run_id)
                assert run is not None and run.status is RunStatus.SUCCEEDED
                assert run.output == {"owner": "replacement"}
                assert (run.input_tokens_total, run.output_tokens_total) == (100, 20)
                assert run.estimated_cost_total == pytest.approx(0.025)
                assert all(
                    call.result is None for call in ToolCallRepository(session).list_for_run(run_id)
                )
        if boundary != "replacement":
            _assert_no_late_result(
                ownership_db,
                run_id,
                status=RunStatus.CANCELED if boundary == "cancel" else RunStatus.FAILED,
            )
    finally:
        await _cleanup(task, operation)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["provider", "tool"])
async def test_async_task_cancellation_leaves_recoverable_lease_without_replay(
    ownership_db: sessionmaker[Session], kind: OperationKind
) -> None:
    run_id = _queued(ownership_db, kind)
    operation = SuspendedOperation()
    service = _service(operation)
    initial_tasks = asyncio.all_tasks()
    task = asyncio.create_task(_execute(ownership_db, service, run_id))
    try:
        await asyncio.wait_for(operation.started.wait(), timeout=5)
        lease = _lease(ownership_db, run_id)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)
        assert operation.cancel_seen.is_set()
        assert operation.returned == 0
        assert not (asyncio.all_tasks() - initial_tasks), "Execution leaked a live heartbeat/task."
        _assert_no_late_result(ownership_db, run_id, status=RunStatus.RUNNING)
        with ownership_db() as session:
            retained = session.get(WorkerLeaseRecord, str(lease.id))
            assert retained is not None and retained.released_at is None
        _expire(ownership_db, lease)
        recovery = StuckRunRecoveryService(session_factory=ownership_db)
        assert recovery.recover_once().recovered_count == 1
        assert recovery.recover_once().recovered_count == 0
        _assert_no_late_result(ownership_db, run_id, status=RunStatus.FAILED)
        restarted = await QueuedRunWorker(
            session_factory=ownership_db, execution_service=service
        ).run_once()
        assert restarted.processed_count == 0
        assert operation.calls == 1
    finally:
        await _cleanup(task, operation)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["provider", "tool"])
async def test_cancellation_resistant_operation_cannot_commit_after_task_cancel(
    ownership_db: sessionmaker[Session], kind: OperationKind
) -> None:
    run_id = _queued(ownership_db, kind)
    operation = SuspendedOperation(suppress_cancellation=True)
    task = asyncio.create_task(_execute(ownership_db, _service(operation), run_id))
    try:
        await asyncio.wait_for(operation.started.wait(), timeout=5)
        lease = _lease(ownership_db, run_id)
        task.cancel()
        await asyncio.wait_for(operation.cancel_seen.wait(), timeout=5)
        with ownership_db() as session:
            leases = WorkerLeaseRepository(session)
            assert leases.get_active(run_id=run_id) is None
            assert leases.heartbeat(lease_token=lease.lease_token) is None
        operation.release.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=5)
        assert operation.returned == 1
        _assert_no_late_result(ownership_db, run_id, status=RunStatus.RUNNING)
        with ownership_db() as session:
            retained = session.get(WorkerLeaseRecord, str(lease.id))
            assert retained is not None and retained.released_at is None
        _expire(ownership_db, lease)
        assert (
            StuckRunRecoveryService(session_factory=ownership_db).recover_once().recovered_count
            == 1
        )
        _assert_no_late_result(ownership_db, run_id, status=RunStatus.FAILED)
    finally:
        await _cleanup(task, operation)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["provider", "tool"])
async def test_cancellation_fails_closed_when_lease_invalidation_is_unavailable(
    ownership_db: sessionmaker[Session], kind: OperationKind, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable(_self: WorkerLeaseRepository, *, lease_token: str) -> None:
        raise RuntimeError("invalidation unavailable")

    run_id = _queued(ownership_db, kind)
    operation = SuspendedOperation(suppress_cancellation=True)
    task = asyncio.create_task(_execute(ownership_db, _service(operation), run_id))
    try:
        await asyncio.wait_for(operation.started.wait(), timeout=5)
        lease = _lease(ownership_db, run_id)
        monkeypatch.setattr(WorkerLeaseRepository, "invalidate", unavailable)
        task.cancel()
        await asyncio.wait_for(operation.cancel_seen.wait(), timeout=5)
        operation.release.set()
        with pytest.raises(RuntimeError, match="invalidation unavailable"):
            await asyncio.wait_for(task, timeout=5)
        assert operation.returned == 1
        _assert_no_late_result(ownership_db, run_id, status=RunStatus.RUNNING)
        _expire(ownership_db, lease)
        assert (
            StuckRunRecoveryService(session_factory=ownership_db).recover_once().recovered_count
            == 1
        )
    finally:
        await _cleanup(task, operation)


def test_old_recovery_snapshot_cannot_fail_replacement_owner(
    ownership_db: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _queued(ownership_db, "provider")
    with ownership_db() as session:
        old = WorkerLeaseRepository(session).acquire(run_id=run_id, worker_id="old")
        assert old is not None
        RunRepository(session, lease_token=old.lease_token).apply_transition(
            run_id=run_id,
            status=RunStatus.RUNNING,
            event_type=RunEventType.RUN_STARTED,
            payload={"from_status": "queued", "to_status": "running"},
        )
    _expire(ownership_db, old)
    with ownership_db() as scanner_session:
        scanner = WorkerLeaseRepository(scanner_session)
        stale_snapshot = scanner.list_expired()
        assert [lease.id for lease in stale_snapshot] == [old.id]
        # Keep the old ORM lease cached in this session across replacement.
        cached = scanner_session.scalar(
            select(WorkerLeaseRecord).where(WorkerLeaseRecord.id == str(old.id))
        )
        assert cached is not None and cached.released_at is None
        with ownership_db() as replacement_session:
            replacement = WorkerLeaseRepository(replacement_session).acquire(
                run_id=run_id, worker_id="replacement", expected_status=RunStatus.RUNNING
            )
            assert replacement is not None
        assert scanner.recover_expired(lease_token=old.lease_token) == (
            False,
            RunStatus.RUNNING,
            "lease_no_longer_expired",
        )
    monkeypatch.setattr(WorkerLeaseRepository, "list_expired", lambda _self, **_: stale_snapshot)
    result = StuckRunRecoveryService(session_factory=ownership_db).recover_once()
    assert result.recovered_count == 0
    assert result.results[0].reason == "lease_no_longer_expired"
    with ownership_db() as session:
        active = WorkerLeaseRepository(session).get_active(run_id=run_id)
        assert active is not None and active.id == replacement.id
        repository = RunRepository(session, lease_token=replacement.lease_token)
        repository.assert_owned(run_id)
        run = repository.get(run_id)
        assert run is not None and run.status is RunStatus.RUNNING
        assert [event.type for event in repository.list_events(run_id)] == [
            RunEventType.RUN_CREATED,
            RunEventType.RUN_QUEUED,
            RunEventType.RUN_STARTED,
        ]


class SourceUsageProvider:
    """Synthetic nonzero accounting from the successful source-model response."""

    name = "suspended"

    def __init__(self, failure: str) -> None:
        self.failure = failure
        self.calls = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        if self.calls > 1:
            raise LLMProviderError(
                "fixture followup unavailable", error_type="provider_unavailable"
            )
        return LLMResponse(
            provider=self.name,
            model=request.model,
            text="",
            finish_reason=LLMFinishReason.TOOL_CALLS,
            tool_calls=(
                LLMToolCall(
                    id="usage-call",
                    name="missing_tool" if self.failure == "unknown_tool" else "cost_tool",
                    arguments={},
                ),
            ),
            usage=LLMUsage(input_tokens=17, output_tokens=4, estimated_cost=0.0125),
        )


class SourceUsageTool:
    def __init__(self, failure: str) -> None:
        self.failure = failure
        self.calls = 0
        self.metadata = ToolMetadata(
            name="cost_tool",
            description="Synthetic accounting fixture; no paid or external calls.",
            input_schema={"type": "object", "additionalProperties": False},
            risk_level=(
                RiskLevel.EXTERNAL_WRITE if failure == "approval_rejected" else RiskLevel.READ_ONLY
            ),
            retry_safe=False,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self.failure == "tool_execution_failed":
            raise RuntimeError("fixture tool failure")
        return {"ok": True}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    ["tool_execution_failed", "unknown_tool", "provider_unavailable", "approval_rejected"],
)
async def test_source_model_usage_survives_downstream_failure(
    ownership_db: sessionmaker[Session], failure: str
) -> None:
    run_id = _queued(ownership_db, "provider")
    provider = SourceUsageProvider(failure)
    tool = SourceUsageTool(failure)
    registry = ToolRegistry()
    registry.register(tool)
    policy = RetryPolicy()
    service = RunExecutionService(provider=provider, tool_registry=registry, retry_policy=policy)
    result = await _execute(ownership_db, service, run_id)
    if failure == "approval_rejected":
        assert result.status is RunStatus.WAITING_APPROVAL
        assert result.estimated_cost_total == pytest.approx(0.0125)
        with ownership_db() as session:
            approvals = ApprovalRepository(session)
            approval = approvals.list_for_run(run_id)[0]
            approvals.reject(approval_id=approval.id, decision_note="fixture refusal")
        with ownership_db() as session:
            result = await service.resume(
                run_id=run_id,
                repository=RunRepository(session),
                approval_repository=ApprovalRepository(session),
                tool_call_repository=ToolCallRepository(session),
            )
    assert result.status is RunStatus.FAILED
    assert result.error_type == failure
    with ownership_db() as session:
        repository = RunRepository(session)
        persisted = repository.get(run_id)
        assert persisted is not None
        assert (persisted.input_tokens_total, persisted.output_tokens_total) == (17, 4)
        assert persisted.estimated_cost_total == pytest.approx(0.0125)
        summary = repository.usage_summary()
        assert summary["input_tokens"] == 17
        assert summary["output_tokens"] == 4
        assert summary["estimated_cost"] == pytest.approx(0.0125)
        assert repository.list_events(run_id)[-1].type is RunEventType.RUN_FAILED
    assert provider.calls == (
        1 + policy.provider_max_attempts if failure == "provider_unavailable" else 1
    )
    assert tool.calls == (0 if failure in {"unknown_tool", "approval_rejected"} else 1)
