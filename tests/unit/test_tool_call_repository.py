from uuid import uuid4

from kernel_core import RiskLevel, RunEventType, ToolCallStatus
from kernel_storage import AgentRepository, RunRepository, ToolCallRepository
from sqlalchemy.orm import Session, sessionmaker


def test_tool_call_repository_persists_requested_call_and_event(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="tool-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "use tool"})
        repository = ToolCallRepository(session)

        tool_call = repository.create_requested(
            run_id=run.id,
            tool_name="echo",
            arguments={"message": "hello"},
            risk_level=RiskLevel.READ_ONLY,
        )
        events = RunRepository(session).list_events(run.id)

    assert tool_call is not None
    assert tool_call.status is ToolCallStatus.REQUESTED
    assert tool_call.arguments == {"message": "hello"}
    assert tool_call.risk_level is RiskLevel.READ_ONLY
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.TOOL_CALL_REQUESTED,
    ]
    assert events[-1].payload["tool_call_id"] == str(tool_call.id)
    assert events[-1].payload["tool_name"] == "echo"


def test_tool_call_repository_lists_calls_for_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="tool-agent")
        run_repository = RunRepository(session)
        first_run = run_repository.create(agent_id=agent.id, input_payload={"task": "one"})
        second_run = run_repository.create(agent_id=agent.id, input_payload={"task": "two"})
        repository = ToolCallRepository(session)
        first_call = repository.create_requested(
            run_id=first_run.id,
            tool_name="echo",
            arguments={"message": "first"},
            risk_level=RiskLevel.READ_ONLY,
        )
        repository.create_requested(
            run_id=second_run.id,
            tool_name="echo",
            arguments={"message": "second"},
            risk_level=RiskLevel.READ_ONLY,
        )

        calls = repository.list_for_run(first_run.id)

    assert first_call is not None
    assert [call.id for call in calls] == [first_call.id]
    assert [call.run_id for call in calls] == [first_run.id]


def test_tool_call_repository_records_policy_decision_event(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="tool-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "use tool"})
        repository = ToolCallRepository(session)
        tool_call = repository.create_requested(
            run_id=run.id,
            tool_name="network-tool",
            arguments={},
            risk_level=RiskLevel.NETWORK,
        )
        assert tool_call is not None

        updated = repository.record_policy_decision(
            tool_call_id=tool_call.id,
            decision="require_approval",
            reason="Default risk policy for network.",
            status=ToolCallStatus.WAITING_APPROVAL,
            requires_approval=True,
        )
        events = RunRepository(session).list_events(run.id)

    assert updated is not None
    assert updated.status is ToolCallStatus.WAITING_APPROVAL
    assert updated.requires_approval is True
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.POLICY_EVALUATED,
    ]
    assert events[-1].payload["decision"] == "require_approval"
    assert events[-1].payload["status"] == "waiting_approval"


def test_tool_call_repository_records_denied_policy_state(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="tool-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "use tool"})
        repository = ToolCallRepository(session)
        tool_call = repository.create_requested(
            run_id=run.id,
            tool_name="dangerous-tool",
            arguments={},
            risk_level=RiskLevel.DANGEROUS,
        )
        assert tool_call is not None

        denied = repository.record_policy_decision(
            tool_call_id=tool_call.id,
            decision="deny",
            reason="Default risk policy for dangerous.",
            status=ToolCallStatus.DENIED,
        )

    assert denied is not None
    assert denied.status is ToolCallStatus.DENIED
    assert denied.requires_approval is False


def test_tool_call_repository_records_success_and_failure(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="tool-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "use tools"})
        repository = ToolCallRepository(session)
        success_call = repository.create_requested(
            run_id=run.id,
            tool_name="echo",
            arguments={"message": "ok"},
            risk_level=RiskLevel.READ_ONLY,
        )
        failed_call = repository.create_requested(
            run_id=run.id,
            tool_name="echo",
            arguments={"message": "fail"},
            risk_level=RiskLevel.READ_ONLY,
        )
        assert success_call is not None
        assert failed_call is not None

        succeeded = repository.complete(
            tool_call_id=success_call.id,
            result={"message": "ok"},
            latency_ms=12,
        )
        failed = repository.fail(
            tool_call_id=failed_call.id,
            error_type="tool_execution_failed",
            error_message="boom",
            latency_ms=7,
        )
        events = RunRepository(session).list_events(run.id)

    assert succeeded is not None
    assert succeeded.status is ToolCallStatus.SUCCEEDED
    assert succeeded.result == {"message": "ok"}
    assert succeeded.latency_ms == 12
    assert failed is not None
    assert failed.status is ToolCallStatus.FAILED
    assert failed.error_type == "tool_execution_failed"
    assert failed.error_message == "boom"
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.TOOL_CALL_COMPLETED,
        RunEventType.TOOL_CALL_FAILED,
    ]


def test_tool_call_repository_returns_none_for_missing_run_or_call(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        repository = ToolCallRepository(session)

        missing_run_call = repository.create_requested(
            run_id=uuid4(),
            tool_name="echo",
            arguments={},
            risk_level=RiskLevel.READ_ONLY,
        )
        missing_update = repository.complete(tool_call_id=uuid4(), result={})

    assert missing_run_call is None
    assert missing_update is None
