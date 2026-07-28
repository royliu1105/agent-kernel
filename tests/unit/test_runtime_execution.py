from typing import Any

import pytest
from kernel_core import ApprovalStatus, RiskLevel, RunEventType, RunStatus
from kernel_providers import LLMProviderError, MockLLMProvider
from kernel_runtime import ModelRouter, RunExecutionError, RunExecutionService
from kernel_storage import AgentRepository, ApprovalRepository, RunRepository, ToolCallRepository
from kernel_tools import ToolMetadata, ToolRegistry, create_default_tool_registry
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.asyncio
async def test_execution_service_completes_queued_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="research-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "summarize notes", "model": "mock:mock-small"},
        )
        queued = run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        assert queued is not None

        completed = await RunExecutionService(provider=MockLLMProvider()).execute(
            run_id=run.id,
            repository=run_repository,
        )
        events = run_repository.list_events(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output == {
        "text": "Mock response: summarize notes",
        "provider": "mock",
        "model": "mock-small",
        "usage": {
            "input_tokens": 2,
            "output_tokens": 4,
            "estimated_cost": 0.0,
        },
    }
    assert completed.input_tokens_total == 2
    assert completed.output_tokens_total == 4
    assert completed.estimated_cost_total == 0.0
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.RUN_COMPLETED,
    ]


@pytest.mark.asyncio
async def test_execution_service_marks_run_failed_on_provider_error(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="research-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(agent_id=agent.id, input_payload={"task": "summarize notes"})
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        provider = MockLLMProvider(
            fail_with=LLMProviderError("provider unavailable", error_type="mock_failure")
        )

        failed = await RunExecutionService(provider=provider).execute(
            run_id=run.id,
            repository=run_repository,
        )
        events = run_repository.list_events(run.id)

    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "mock_failure"
    assert failed.error_message == "provider unavailable"
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.RUN_FAILED,
    ]
    assert events[-1].payload["error_type"] == "mock_failure"


@pytest.mark.asyncio
async def test_execution_service_rejects_unqueued_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="research-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(agent_id=agent.id, input_payload={"task": "summarize notes"})

        with pytest.raises(ValueError, match="Cannot transition run from created to running"):
            await RunExecutionService(provider=MockLLMProvider()).execute(
                run_id=run.id,
                repository=run_repository,
            )


@pytest.mark.asyncio
async def test_execution_service_can_execute_through_model_router(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="research-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "route me", "model": "mock:mock-routed"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        router = ModelRouter({"mock": MockLLMProvider(response_prefix="Routed")})

        completed = await RunExecutionService(router=router).execute(
            run_id=run.id,
            repository=run_repository,
        )

    assert completed.output is not None
    assert completed.output["text"] == "Routed: route me"
    assert completed.output["model"] == "mock-routed"


@pytest.mark.asyncio
async def test_execution_service_completes_safe_explicit_tool_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="tool-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "echo", "arguments": {"message": "hello"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        completed = await RunExecutionService().execute(run_id=run.id, repository=run_repository)
        events = run_repository.list_events(run.id)
        tool_calls = ToolCallRepository(session).list_for_run(run.id)

    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output == {
        "tool": {
            "tool_call_id": str(tool_calls[0].id),
            "approval_id": None,
            "name": "echo",
            "result": {"message": "hello"},
        }
    }
    assert tool_calls[0].result == {"message": "hello"}
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.POLICY_EVALUATED,
        RunEventType.TOOL_CALL_COMPLETED,
        RunEventType.RUN_COMPLETED,
    ]


@pytest.mark.asyncio
async def test_execution_service_pauses_risky_explicit_tool_for_approval(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="approval-tool-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "draft"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

        waiting = await RunExecutionService(tool_registry=_approval_tool_registry()).execute(
            run_id=run.id,
            repository=run_repository,
        )
        approvals = ApprovalRepository(session).list_for_run(run.id)
        events = run_repository.list_events(run.id)

    assert waiting.status is RunStatus.WAITING_APPROVAL
    assert len(approvals) == 1
    assert approvals[0].status is ApprovalStatus.REQUESTED
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.TOOL_CALL_REQUESTED,
        RunEventType.POLICY_EVALUATED,
        RunEventType.APPROVAL_REQUESTED,
        RunEventType.RUN_WAITING_APPROVAL,
    ]


@pytest.mark.asyncio
async def test_execution_service_resumes_approved_tool_with_persisted_arguments(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="approval-tool-agent")
        run_repository = RunRepository(session)
        approval_repository = ApprovalRepository(session)
        tool_call_repository = ToolCallRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "original"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        service = RunExecutionService(tool_registry=_approval_tool_registry())
        waiting = await service.execute(run_id=run.id, repository=run_repository)
        approval = approval_repository.list_for_run(run.id)[0]
        approval_repository.approve(
            approval_id=approval.id,
            decision_note="Approved for test.",
        )

        resumed = await service.resume(
            run_id=waiting.id,
            repository=run_repository,
            approval_repository=approval_repository,
            tool_call_repository=tool_call_repository,
            approval_id=approval.id,
        )
        events = run_repository.list_events(run.id)
        tool_calls = tool_call_repository.list_for_run(run.id)

    assert resumed.status is RunStatus.SUCCEEDED
    assert resumed.output is not None
    assert resumed.output["tool"]["result"] == {"written": "original"}
    assert tool_calls[0].arguments == {"value": "original"}
    assert tool_calls[0].result == {"written": "original"}
    assert RunEventType.RUN_RESUMING in [event.type for event in events]
    assert events[-1].type is RunEventType.RUN_COMPLETED


@pytest.mark.asyncio
async def test_execution_service_fails_rejected_approval_on_resume(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="approval-tool-agent")
        run_repository = RunRepository(session)
        approval_repository = ApprovalRepository(session)
        tool_call_repository = ToolCallRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "draft"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        service = RunExecutionService(tool_registry=_approval_tool_registry())
        waiting = await service.execute(run_id=run.id, repository=run_repository)
        approval = approval_repository.list_for_run(run.id)[0]
        approval_repository.reject(approval_id=approval.id, decision_note="Do not write.")

        failed = await service.resume(
            run_id=waiting.id,
            repository=run_repository,
            approval_repository=approval_repository,
            tool_call_repository=tool_call_repository,
            approval_id=approval.id,
        )
        events = run_repository.list_events(run.id)

    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "approval_rejected"
    assert failed.error_message == "Do not write."
    assert events[-1].type is RunEventType.RUN_FAILED


@pytest.mark.asyncio
async def test_execution_service_rejects_resume_before_approval_decision(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="approval-tool-agent")
        run_repository = RunRepository(session)
        approval_repository = ApprovalRepository(session)
        tool_call_repository = ToolCallRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"tool": {"name": "external_write", "arguments": {"value": "draft"}}},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        service = RunExecutionService(tool_registry=_approval_tool_registry())
        waiting = await service.execute(run_id=run.id, repository=run_repository)
        approval = approval_repository.list_for_run(run.id)[0]

        with pytest.raises(RunExecutionError, match="has not been decided yet"):
            await service.resume(
                run_id=waiting.id,
                repository=run_repository,
                approval_repository=approval_repository,
                tool_call_repository=tool_call_repository,
                approval_id=approval.id,
            )


class ExternalWriteTool:
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="external_write",
            description="Test-only external write tool.",
            input_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            risk_level=RiskLevel.EXTERNAL_WRITE,
        )

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"written": arguments["value"]}


def _approval_tool_registry() -> ToolRegistry:
    registry = create_default_tool_registry()
    registry.register(ExternalWriteTool())
    return registry
