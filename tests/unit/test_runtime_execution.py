import pytest
from kernel_core import RunEventType, RunStatus
from kernel_providers import LLMProviderError, MockLLMProvider
from kernel_runtime import ModelRouter, RunExecutionService
from kernel_storage import AgentRepository, RunRepository
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
