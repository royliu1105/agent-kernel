from uuid import UUID, uuid4

import pytest
from kernel_core import ApprovalStatus, RiskLevel, RunEventType, ToolCall, ToolCallStatus
from kernel_storage import (
    AgentRepository,
    ApprovalDecisionError,
    ApprovalRepository,
    RunRepository,
    ToolCallRepository,
    WorkspaceRepository,
)
from sqlalchemy.orm import Session, sessionmaker


def test_approval_repository_creates_requested_approval_and_event(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        tool_call = _create_waiting_tool_call(session)
        repository = ApprovalRepository(session)

        approval = repository.create_requested(
            tool_call_id=tool_call.id,
            reason="Network tool requires approval.",
        )
        events = RunRepository(session).list_events(tool_call.run_id)
        updated_tool_call = ToolCallRepository(session).get(tool_call.id)

    assert approval is not None
    assert approval.status is ApprovalStatus.REQUESTED
    assert approval.tool_call_id == tool_call.id
    assert approval.reason == "Network tool requires approval."
    assert updated_tool_call is not None
    assert updated_tool_call.status is ToolCallStatus.WAITING_APPROVAL
    assert updated_tool_call.approval_id == approval.id
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.POLICY_EVALUATED,
        RunEventType.APPROVAL_REQUESTED,
    ]
    assert events[-1].payload["approval_id"] == str(approval.id)


def test_approval_repository_lists_and_gets_approvals(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        tool_call = _create_waiting_tool_call(session)
        repository = ApprovalRepository(session)
        approval = repository.create_requested(tool_call_id=tool_call.id, reason="Review needed.")
        assert approval is not None

        approvals = repository.list()
        requested_approvals = repository.list(status=ApprovalStatus.REQUESTED)
        loaded = repository.get(approval.id)

    assert [item.id for item in approvals] == [approval.id]
    assert [item.id for item in requested_approvals] == [approval.id]
    assert loaded is not None
    assert loaded.id == approval.id


def test_approval_repository_filters_approvals_by_workspace(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        first_workspace = WorkspaceRepository(session).create(name="First", slug="first-approval")
        second_workspace = WorkspaceRepository(session).create(
            name="Second",
            slug="second-approval",
        )
        first_tool_call = _create_waiting_tool_call(session, workspace_id=first_workspace.id)
        second_tool_call = _create_waiting_tool_call(session, workspace_id=second_workspace.id)
        repository = ApprovalRepository(session)
        first_approval = repository.create_requested(
            tool_call_id=first_tool_call.id,
            reason="First workspace approval.",
        )
        second_approval = repository.create_requested(
            tool_call_id=second_tool_call.id,
            reason="Second workspace approval.",
        )
        assert first_approval is not None
        assert second_approval is not None

        first_workspace_approvals = repository.list(workspace_id=first_workspace.id)
        loaded_from_first = repository.get(
            first_approval.id,
            workspace_id=first_workspace.id,
        )
        hidden_from_second = repository.get(
            first_approval.id,
            workspace_id=second_workspace.id,
        )

    assert [approval.id for approval in first_workspace_approvals] == [first_approval.id]
    assert loaded_from_first is not None
    assert loaded_from_first.id == first_approval.id
    assert hidden_from_second is None


def test_approval_repository_approves_and_rejects_with_events(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        first_tool_call = _create_waiting_tool_call(session)
        second_tool_call = _create_waiting_tool_call(session)
        repository = ApprovalRepository(session)
        approval = repository.create_requested(
            tool_call_id=first_tool_call.id,
            reason="Approve me.",
        )
        rejection = repository.create_requested(
            tool_call_id=second_tool_call.id,
            reason="Reject me.",
        )
        assert approval is not None
        assert rejection is not None
        reviewer_id = uuid4()

        approved = repository.approve(
            approval_id=approval.id,
            reviewed_by=reviewer_id,
            decision_note="Looks safe.",
        )
        rejected = repository.reject(
            approval_id=rejection.id,
            reviewed_by=reviewer_id,
            decision_note="Not allowed.",
        )
        events = RunRepository(session).list_events(first_tool_call.run_id)

    assert approved is not None
    assert approved.status is ApprovalStatus.APPROVED
    assert approved.reviewed_by == reviewer_id
    assert approved.decision_note == "Looks safe."
    assert approved.resolved_at is not None
    assert rejected is not None
    assert rejected.status is ApprovalStatus.REJECTED
    assert rejected.decision_note == "Not allowed."
    assert RunEventType.APPROVAL_APPROVED in [event.type for event in events]


def test_approval_repository_decisions_are_workspace_scoped(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        first_workspace = WorkspaceRepository(session).create(
            name="First Decision",
            slug="first-decision",
        )
        second_workspace = WorkspaceRepository(session).create(
            name="Second Decision",
            slug="second-decision",
        )
        tool_call = _create_waiting_tool_call(session, workspace_id=first_workspace.id)
        repository = ApprovalRepository(session)
        approval = repository.create_requested(
            tool_call_id=tool_call.id,
            reason="Review needed.",
        )
        assert approval is not None

        hidden_decision = repository.approve(
            approval_id=approval.id,
            workspace_id=second_workspace.id,
        )
        scoped_decision = repository.approve(
            approval_id=approval.id,
            decision_note="Same workspace.",
            workspace_id=first_workspace.id,
        )

    assert hidden_decision is None
    assert scoped_decision is not None
    assert scoped_decision.status is ApprovalStatus.APPROVED
    assert scoped_decision.decision_note == "Same workspace."


def test_approval_repository_rejects_duplicate_decisions(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        tool_call = _create_waiting_tool_call(session)
        repository = ApprovalRepository(session)
        approval = repository.create_requested(tool_call_id=tool_call.id, reason="Review needed.")
        assert approval is not None
        repository.approve(approval_id=approval.id)

        with pytest.raises(ApprovalDecisionError, match="already been decided"):
            repository.reject(approval_id=approval.id, decision_note="Too late.")


def test_approval_repository_returns_none_for_missing_records(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        repository = ApprovalRepository(session)

        assert repository.create_requested(tool_call_id=uuid4(), reason="Missing.") is None
        assert repository.get(uuid4()) is None
        assert repository.approve(approval_id=uuid4()) is None
        assert repository.reject(approval_id=uuid4(), decision_note="Missing.") is None


def _create_waiting_tool_call(session: Session, *, workspace_id: UUID | None = None) -> ToolCall:
    agent = AgentRepository(session).create(name="approval-agent", workspace_id=workspace_id)
    run = RunRepository(session).create(
        agent_id=agent.id,
        workspace_id=workspace_id,
        input_payload={"task": "approve"},
    )
    repository = ToolCallRepository(session)
    tool_call = repository.create_requested(
        run_id=run.id,
        tool_name="network-tool",
        arguments={},
        risk_level=RiskLevel.NETWORK,
    )
    assert tool_call is not None
    waiting = repository.record_policy_decision(
        tool_call_id=tool_call.id,
        decision="require_approval",
        reason="Network tool requires approval.",
        status=ToolCallStatus.WAITING_APPROVAL,
        requires_approval=True,
    )
    assert waiting is not None
    return waiting
