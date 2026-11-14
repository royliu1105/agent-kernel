"""Rejected continuation ends the matching tool and Run in one fenced transaction."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from kernel_core import ApprovalStatus, RunEventType, RunStatus, ToolCallStatus, utc_now
from kernel_runtime import RunExecutionService
from kernel_runtime.execution import RunExecutionError
from kernel_storage import (
    ApprovalRepository,
    ExecutionOwnershipError,
    RunConflictError,
    RunRepository,
    ToolCallRepository,
    WorkerLeaseRepository,
)
from kernel_storage.models import (
    ApprovalRecord,
    RunEventRecord,
    RunRecord,
    ToolCallRecord,
    WorkerLeaseRecord,
)
from kernel_tools import ToolRegistry
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker
from test_bounded_native_execution import CountingTool, ScriptedProvider, call, queued, reply


@dataclass
class RejectionCase:
    run_id: UUID
    approval_id: UUID
    tool_id: UUID
    read: CountingTool
    write: CountingTool
    provider: ScriptedProvider
    registry: ToolRegistry


async def waiting(factory: sessionmaker[Session], *, native: bool = True) -> RejectionCase:
    read, write = CountingTool("read"), CountingTool("write", write=True)
    registry = ToolRegistry()
    registry.register(read)
    registry.register(write)
    provider = ScriptedProvider([reply(call("read-1"), call("write-1", "write"))] if native else [])
    with factory() as session:
        run_id = queued(
            session,
            payload=None
            if native
            else {"tool": {"name": "write", "arguments": {"value": "not permitted"}}},
        )
        result = await RunExecutionService(provider=provider, tool_registry=registry).execute(
            run_id=run_id, repository=RunRepository(session)
        )
        assert result.status is RunStatus.WAITING_APPROVAL
        approval = ApprovalRepository(session).list_for_run(run_id)[0]
        return RejectionCase(
            run_id, approval.id, approval.tool_call_id, read, write, provider, registry
        )


def reject(factory: sessionmaker[Session], case: RejectionCase) -> None:
    with factory() as session:
        approval = ApprovalRepository(session).reject(
            approval_id=case.approval_id, decision_note="No external operation."
        )
        assert approval is not None and approval.status is ApprovalStatus.REJECTED
        # Keep the existing decision-only API contract: resume processes the terminal state.
        run = RunRepository(session).get(case.run_id)
        tool = ToolCallRepository(session).get(case.tool_id)
        assert run is not None and tool is not None
        assert run.status is RunStatus.WAITING_APPROVAL
        assert tool.status is ToolCallStatus.WAITING_APPROVAL


async def resume(factory: sessionmaker[Session], case: RejectionCase) -> None:
    provider = ScriptedProvider([])
    with factory() as session:
        result = await RunExecutionService(provider=provider, tool_registry=case.registry).resume(
            run_id=case.run_id,
            repository=RunRepository(session),
            approval_repository=ApprovalRepository(session),
            tool_call_repository=ToolCallRepository(session),
            approval_id=case.approval_id,
        )
    assert result.status is RunStatus.FAILED and result.error_type == "approval_rejected"
    assert provider.requests == [] and case.write.calls == []


def assert_terminal(factory: sessionmaker[Session], case: RejectionCase, *, native: bool) -> None:
    with factory() as session:
        run = RunRepository(session).get(case.run_id)
        tool = ToolCallRepository(session).get(case.tool_id)
        assert run is not None and tool is not None
        assert run.status is RunStatus.FAILED and run.ended_at is not None
        assert tool.status is ToolCallStatus.DENIED
        assert tool.error_type == run.error_type == "approval_rejected"
        assert tool.error_message == run.error_message == "No external operation."
        assert tool.result is None and tool.latency_ms is None
        assert tool.approval_id == case.approval_id and tool.trace_id == run.trace_id
        calls = ToolCallRepository(session).list_for_run(case.run_id)
        if native:
            assert calls[0].status is ToolCallStatus.SUCCEEDED
            assert calls[0].result == {"value": "", "call_number": 1}
        events = RunRepository(session).list_events(case.run_id)
        assert [item.type for item in events[-3:]] == [
            RunEventType.APPROVAL_REJECTED,
            RunEventType.TOOL_CALL_FAILED,
            RunEventType.RUN_FAILED,
        ]
        assert sum(item.type is RunEventType.TOOL_CALL_FAILED for item in events) == 1
        assert sum(item.type is RunEventType.RUN_FAILED for item in events) == 1
        assert [item.sequence for item in events] == list(range(1, len(events) + 1))
        assert events[-2].payload["tool_call_id"] == str(case.tool_id)
        assert events[-2].payload["approval_id"] == str(case.approval_id)
        assert events[-2].payload["status"] == "denied"
        assert events[-2].payload["execution_skipped"] is True
        assert {item.trace_id for item in events} == {run.trace_id}
    assert len(case.read.calls) == int(native)
    assert len(case.provider.requests) == int(native)
    assert case.write.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True], ids=["explicit", "native"])
async def test_rejected_resume_persists_terminal_tool_and_run(
    postgres_session_factory: sessionmaker[Session], native: bool
) -> None:
    factory = postgres_session_factory
    case = await waiting(factory, native=native)
    reject(factory, case)
    await resume(factory, case)
    assert_terminal(factory, case, native=native)
    with pytest.raises(RunExecutionError):
        await resume(factory, case)
    assert_terminal(factory, case, native=native)


@pytest.mark.asyncio
async def test_rejection_terminal_commit_failure_rolls_back_states_and_events(
    postgres_session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    factory = postgres_session_factory
    case = await waiting(factory)
    reject(factory, case)
    observed = []

    def fail_before_commit(session: Session) -> None:
        if not any(
            isinstance(item, RunEventRecord) and item.type == "run_failed" for item in session.new
        ):
            return
        session.flush()
        with factory() as observer:
            run = RunRepository(observer).get(case.run_id)
            tool = ToolCallRepository(observer).get(case.tool_id)
            assert run is not None and tool is not None
            assert run.status is RunStatus.WAITING_APPROVAL
            assert tool.status is ToolCallStatus.WAITING_APPROVAL
            assert (
                RunRepository(observer).list_events(case.run_id)[-1].type
                is RunEventType.APPROVAL_REJECTED
            )
        observed.append(True)
        raise RuntimeError("injected rejection commit failure")

    with factory() as session:
        event.listen(session, "before_commit", fail_before_commit)
        with pytest.raises(RuntimeError, match="injected rejection commit failure"):
            await RunExecutionService(
                provider=ScriptedProvider([]), tool_registry=case.registry
            ).resume(
                run_id=case.run_id,
                repository=RunRepository(session),
                approval_repository=ApprovalRepository(session),
                tool_call_repository=ToolCallRepository(session),
                approval_id=case.approval_id,
            )
    assert observed == [True]
    assert not any(record.message == "agent.run.failed" for record in caplog.records)
    with factory() as session:
        run = RunRepository(session).get(case.run_id)
        tool = ToolCallRepository(session).get(case.tool_id)
        assert run is not None and tool is not None
        assert run.status is RunStatus.WAITING_APPROVAL and run.error_type is None
        assert tool.status is ToolCallStatus.WAITING_APPROVAL and tool.error_type is None
        assert (
            RunRepository(session).list_events(case.run_id)[-1].type
            is RunEventType.APPROVAL_REJECTED
        )
    await resume(factory, case)
    assert_terminal(factory, case, native=True)


@pytest.mark.asyncio
async def test_concurrent_rejected_resumes_commit_one_terminal_pair(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    factory = postgres_session_factory
    case = await waiting(factory)
    reject(factory, case)
    results = await asyncio.gather(
        resume(factory, case), resume(factory, case), return_exceptions=True
    )
    assert sum(result is None for result in results) == 1
    assert sum(isinstance(result, RunExecutionError) for result in results) == 1
    assert_terminal(factory, case, native=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", ["absent", "expired", "replaced", "canceled"])
async def test_rejection_finalization_is_fenced_by_lease(
    postgres_session_factory: sessionmaker[Session], owner: str
) -> None:
    factory = postgres_session_factory
    case = await waiting(factory)
    reject(factory, case)
    with factory() as session:
        leases = WorkerLeaseRepository(session)
        lease = leases.acquire(
            run_id=case.run_id,
            worker_id="rejection-test",
            expected_status=RunStatus.WAITING_APPROVAL,
        )
        assert lease is not None
        if owner in {"expired", "replaced"}:
            record = session.get(WorkerLeaseRecord, str(lease.id))
            assert record is not None
            record.expires_at = utc_now() - timedelta(seconds=1)
            session.commit()
            if owner == "replaced":
                assert (
                    leases.acquire(
                        run_id=case.run_id,
                        worker_id="replacement",
                        expected_status=RunStatus.WAITING_APPROVAL,
                    )
                    is not None
                )
        elif owner == "canceled":
            RunRepository(session).apply_transition(
                run_id=case.run_id,
                status=RunStatus.CANCELED,
                event_type=RunEventType.RUN_CANCELED,
                payload={"from_status": "waiting_approval"},
            )
        before = RunRepository(session).list_events(case.run_id)
        with pytest.raises(ExecutionOwnershipError):
            RunRepository(
                session, lease_token=None if owner == "absent" else lease.lease_token
            ).fail_rejected_approval(run_id=case.run_id, approval_id=case.approval_id)
        session.rollback()
        assert RunRepository(session).list_events(case.run_id) == before
        run = RunRepository(session).get(case.run_id)
        tool = ToolCallRepository(session).get(case.tool_id)
        assert run is not None and tool is not None
        assert run.status is (
            RunStatus.CANCELED if owner == "canceled" else RunStatus.WAITING_APPROVAL
        )
        assert tool.status is ToolCallStatus.WAITING_APPROVAL and tool.error_type is None
    assert case.write.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", [ApprovalStatus.REQUESTED, ApprovalStatus.EXPIRED, ApprovalStatus.CANCELED]
)
async def test_other_unapproved_statuses_still_refuse_resume_without_terminal_writes(
    postgres_session_factory: sessionmaker[Session], status: ApprovalStatus
) -> None:
    factory = postgres_session_factory
    case = await waiting(factory)
    with factory() as session:
        record = session.get(ApprovalRecord, str(case.approval_id))
        assert record is not None
        # Expiry/cancellation have no new public API in this repair; seed legacy states.
        record.status = status.value
        session.commit()
        before = RunRepository(session).list_events(case.run_id)
    with pytest.raises(RunExecutionError):
        await resume(factory, case)
    with factory() as session:
        run = RunRepository(session).get(case.run_id)
        tool = ToolCallRepository(session).get(case.tool_id)
        assert run is not None and tool is not None
        assert run.status is RunStatus.WAITING_APPROVAL
        assert tool.status is ToolCallStatus.WAITING_APPROVAL
        assert RunRepository(session).list_events(case.run_id) == before
    assert case.write.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mismatch", ["missing", "other_run", "approved", "tool_link", "completed_tool", "terminal_run"]
)
async def test_finalization_revalidates_relationships_and_terminal_states(
    postgres_session_factory: sessionmaker[Session], mismatch: str
) -> None:
    factory = postgres_session_factory
    case = await waiting(factory)
    other = await waiting(factory)
    reject(factory, case)
    reject(factory, other)
    with factory() as session:
        lease = WorkerLeaseRepository(session).acquire(
            run_id=case.run_id,
            worker_id="rejection-validation",
            expected_status=RunStatus.WAITING_APPROVAL,
        )
        assert lease is not None
        approval_id = case.approval_id
        if mismatch == "missing":
            approval_id = uuid4()
        elif mismatch == "other_run":
            approval_id = other.approval_id
        elif mismatch == "approved":
            approval = session.get(ApprovalRecord, str(case.approval_id))
            assert approval is not None
            approval.status = ApprovalStatus.APPROVED.value
        elif mismatch in {"tool_link", "completed_tool"}:
            tool = session.get(ToolCallRecord, str(case.tool_id))
            assert tool is not None
            if mismatch == "tool_link":
                tool.approval_id = str(other.approval_id)
            else:
                tool.status, tool.result = ToolCallStatus.SUCCEEDED.value, {"already": "done"}
        else:
            run = session.get(RunRecord, str(case.run_id))
            assert run is not None
            run.status = RunStatus.FAILED.value
        session.commit()
        before = (
            RunRepository(session).get(case.run_id),
            ToolCallRepository(session).get(case.tool_id),
            RunRepository(session).list_events(case.run_id),
        )
        with pytest.raises(RunConflictError):
            RunRepository(session, lease_token=lease.lease_token).fail_rejected_approval(
                run_id=case.run_id, approval_id=approval_id
            )
        session.rollback()
        assert before == (
            RunRepository(session).get(case.run_id),
            ToolCallRepository(session).get(case.tool_id),
            RunRepository(session).list_events(case.run_id),
        )
    assert case.write.calls == other.write.calls == []
