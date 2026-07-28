from typing import Any

import pytest
from kernel_core import RiskLevel, RunEventType, RunStatus
from kernel_providers import LLMProviderError, MockLLMProvider
from kernel_runtime import ModelRouter, QueuedRunWorker, RunExecutionService
from kernel_storage import AgentRepository, ApprovalRepository, RunRepository
from kernel_tools import ToolMetadata, ToolRegistry, create_default_tool_registry
from sqlalchemy.orm import Session, sessionmaker


@pytest.mark.asyncio
async def test_worker_executes_queued_runs(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="worker-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "process me", "model": "mock:mock-worker"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

    worker = QueuedRunWorker(
        session_factory=sqlite_session_factory,
        execution_service=RunExecutionService(
            router=ModelRouter({"mock": MockLLMProvider(response_prefix="Worker")})
        ),
    )

    result = await worker.run_once(limit=10)

    with sqlite_session_factory() as session:
        run_repository = RunRepository(session)
        completed = run_repository.get(run.id)
        events = run_repository.list_events(run.id)

    assert result.processed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert completed is not None
    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output is not None
    assert completed.output["text"] == "Worker: process me"
    assert [event.type for event in events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_STARTED,
        RunEventType.RUN_COMPLETED,
    ]


@pytest.mark.asyncio
async def test_worker_records_provider_failures(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="worker-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(agent_id=agent.id, input_payload={"task": "fail me"})
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

    worker = QueuedRunWorker(
        session_factory=sqlite_session_factory,
        execution_service=RunExecutionService(
            router=ModelRouter(
                {
                    "mock": MockLLMProvider(
                        fail_with=LLMProviderError(
                            "provider unavailable",
                            error_type="mock_failure",
                        )
                    )
                }
            )
        ),
    )

    result = await worker.run_once(limit=10)

    with sqlite_session_factory() as session:
        run_repository = RunRepository(session)
        failed = run_repository.get(run.id)
        events = run_repository.list_events(run.id)

    assert result.processed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1
    assert result.runs[0].error_type == "mock_failure"
    assert result.runs[0].error_message == "provider unavailable"
    assert failed is not None
    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "mock_failure"
    assert failed.error_message == "provider unavailable"
    assert events[-1].type is RunEventType.RUN_FAILED


@pytest.mark.asyncio
async def test_worker_only_picks_queued_runs(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="worker-agent")
        run_repository = RunRepository(session)
        queued_run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "queued", "model": "mock:mock-worker"},
        )
        run_repository.apply_transition(
            run_id=queued_run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        terminal_run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "already done", "model": "mock:mock-worker"},
        )
        run_repository.apply_transition(
            run_id=terminal_run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        run_repository.complete(
            run_id=terminal_run.id,
            output_payload={"text": "done"},
            input_tokens_total=0,
            output_tokens_total=0,
            estimated_cost_total=0.0,
            event_payload={"from_status": "running", "to_status": "succeeded"},
        )

    worker = QueuedRunWorker(
        session_factory=sqlite_session_factory,
        execution_service=RunExecutionService(router=ModelRouter({"mock": MockLLMProvider()})),
    )

    result = await worker.run_once(limit=10)

    with sqlite_session_factory() as session:
        run_repository = RunRepository(session)
        completed_queued_run = run_repository.get(queued_run.id)
        untouched_terminal_run = run_repository.get(terminal_run.id)
        terminal_events = run_repository.list_events(terminal_run.id)

    assert result.processed_count == 1
    assert completed_queued_run is not None
    assert completed_queued_run.status is RunStatus.SUCCEEDED
    assert untouched_terminal_run is not None
    assert untouched_terminal_run.status is RunStatus.SUCCEEDED
    assert [event.type for event in terminal_events] == [
        RunEventType.RUN_CREATED,
        RunEventType.RUN_QUEUED,
        RunEventType.RUN_COMPLETED,
    ]


@pytest.mark.asyncio
async def test_worker_marks_route_errors_failed(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="worker-agent")
        run_repository = RunRepository(session)
        run = run_repository.create(
            agent_id=agent.id,
            input_payload={"task": "unknown provider", "model": "missing:model"},
        )
        run_repository.apply_transition(
            run_id=run.id,
            status=RunStatus.QUEUED,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )

    worker = QueuedRunWorker(
        session_factory=sqlite_session_factory,
        execution_service=RunExecutionService(router=ModelRouter({"mock": MockLLMProvider()})),
    )

    result = await worker.run_once(limit=10)

    with sqlite_session_factory() as session:
        run_repository = RunRepository(session)
        failed = run_repository.get(run.id)
        events = run_repository.list_events(run.id)

    assert result.processed_count == 1
    assert result.failed_count == 1
    assert result.runs[0].error_type == "UnknownModelRouteError"
    assert failed is not None
    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "UnknownModelRouteError"
    assert events[-1].type is RunEventType.RUN_FAILED


@pytest.mark.asyncio
async def test_worker_pauses_risky_tool_run_and_does_not_repick_waiting_run(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="worker-approval-agent")
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

    worker = QueuedRunWorker(
        session_factory=sqlite_session_factory,
        execution_service=RunExecutionService(tool_registry=_approval_tool_registry()),
    )

    first_result = await worker.run_once(limit=10)
    second_result = await worker.run_once(limit=10)

    with sqlite_session_factory() as session:
        run_repository = RunRepository(session)
        waiting = run_repository.get(run.id)
        approvals = ApprovalRepository(session).list_for_run(run.id)
        events = run_repository.list_events(run.id)

    assert first_result.processed_count == 1
    assert first_result.succeeded_count == 0
    assert first_result.failed_count == 0
    assert first_result.runs[0].status is RunStatus.WAITING_APPROVAL
    assert second_result.processed_count == 0
    assert waiting is not None
    assert waiting.status is RunStatus.WAITING_APPROVAL
    assert len(approvals) == 1
    assert events[-1].type is RunEventType.RUN_WAITING_APPROVAL


@pytest.mark.asyncio
async def test_worker_rejects_invalid_limit(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    worker = QueuedRunWorker(
        session_factory=sqlite_session_factory,
        execution_service=RunExecutionService(router=ModelRouter({"mock": MockLLMProvider()})),
    )

    with pytest.raises(ValueError, match="Worker limit must be at least 1"):
        await worker.run_once(limit=0)


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
