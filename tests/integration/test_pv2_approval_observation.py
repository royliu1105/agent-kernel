"""PostgreSQL-required fixture observation; never counts as live GitHub evidence."""

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from kernel_core import ApprovalStatus, RunStatus, ToolCallStatus
from kernel_runtime import RunExecutionService
from kernel_runtime.execution import RunExecutionError
from kernel_storage import ApprovalRepository, RunRepository, ToolCallRepository
from kernel_tools import ToolExecutionContext, ToolRegistry
from sqlalchemy.orm import Session, sessionmaker
from test_bounded_native_execution import CountingTool, ScriptedProvider, call, queued, reply

from scripts.pv1_harness import Journal, read_events
from scripts.pv2_offline_harness import FixtureLedger


class ObservedTool(CountingTool):
    def __init__(self, journal: Journal) -> None:
        super().__init__("write", write=True)
        self.journal = journal

    async def execute_with_context(
        self, arguments: dict[str, Any], *, context: ToolExecutionContext
    ) -> dict[str, Any]:
        assert context.tool_call_id is not None
        attempt = uuid4()
        self.journal.append("dispatch_start", attempt=attempt, tool=context.tool_call_id)
        result = await super().execute(arguments)
        self.journal.append("response_headers", attempt=attempt, tool=context.tool_call_id)
        self.journal.append("response_validated", attempt=attempt, tool=context.tool_call_id)
        return result


@pytest.mark.asyncio
@pytest.mark.parametrize("approve", [True, False])
async def test_persisted_decision_matches_independent_fixture_count(
    postgres_session_factory: sessionmaker[Session], tmp_path: Path, approve: bool
) -> None:
    case, worker, api = uuid4(), uuid4(), uuid4()
    binding = "a" * 64
    ledger = FixtureLedger(tmp_path / "manifest.jsonl", case, binding)
    ledger.create()
    ledger.change("register", executor=worker, attestation=binding)
    journals = tmp_path / "journals"
    journals.mkdir()
    worker_journal = Journal(journals, case, worker)
    initial_tool = ObservedTool(worker_journal)
    registry = ToolRegistry()
    registry.register(initial_tool)
    with postgres_session_factory() as session:
        run_id = queued(session)
        result = await RunExecutionService(
            provider=ScriptedProvider([reply(call("w1", "write"))]), tool_registry=registry
        ).execute(run_id=run_id, repository=RunRepository(session))
        assert result.status is RunStatus.WAITING_APPROVAL
        approval = ApprovalRepository(session).list_for_run(run_id)[0]
        assert approval.status is ApprovalStatus.REQUESTED
        tool_id, approval_id = approval.tool_call_id, approval.id
    assert initial_tool.calls == []
    assert [event.event for event in read_events(worker_journal.path)] == ["case_open"]
    worker_journal.append("case_close")

    ledger.change("register", executor=api, role="api", attestation=binding)
    api_journal = Journal(journals, case, api)
    resumed_tool = ObservedTool(api_journal)
    resumed_registry = ToolRegistry()
    resumed_registry.register(resumed_tool)
    with postgres_session_factory() as session:
        approvals = ApprovalRepository(session)
        if approve:
            approvals.approve(approval_id=approval_id)
        else:
            approvals.reject(approval_id=approval_id, decision_note="Fixture rejection")
        decision = approvals.list_for_run(run_id)[0]
        assert decision.status is (ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED)
        service = RunExecutionService(
            provider=ScriptedProvider([reply(text="done")] if approve else []),
            tool_registry=resumed_registry,
        )
        result = await service.resume(
            run_id=run_id,
            repository=RunRepository(session),
            approval_repository=approvals,
            tool_call_repository=ToolCallRepository(session),
            approval_id=approval_id,
        )
        assert result.status is (RunStatus.SUCCEEDED if approve else RunStatus.FAILED)
        stored = ToolCallRepository(session).get(tool_id)
        assert stored is not None
        assert stored.status is (ToolCallStatus.SUCCEEDED if approve else ToolCallStatus.DENIED)
        with pytest.raises(RunExecutionError):
            await service.resume(
                run_id=run_id,
                repository=RunRepository(session),
                approval_repository=approvals,
                tool_call_repository=ToolCallRepository(session),
                approval_id=approval_id,
            )
    api_journal.append("case_close")
    ledger.change("close", executor=api)
    observation = ledger.observation(journals, {tool_id: int(approve)})
    assert observation.verdict == "pass"
    assert observation.starts.get(tool_id, 0) == int(approve)
    assert len(resumed_tool.calls) == int(approve)
