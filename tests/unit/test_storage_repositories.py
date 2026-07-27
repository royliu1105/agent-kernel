from kernel_core import RunEventType, RunStatus
from kernel_storage import AgentRepository, RunRepository
from sqlalchemy.orm import Session, sessionmaker


def test_agent_repository_creates_and_loads_agent(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        created = AgentRepository(session).create(
            name="research-agent",
            description="Research assistant",
        )

        loaded = AgentRepository(session).get(created.id)

    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.name == "research-agent"
    assert loaded.description == "Research assistant"


def test_run_repository_creates_run_and_initial_event(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="ops-agent")
        run = RunRepository(session).create(
            agent_id=agent.id,
            input_payload={"task": "check status"},
        )

        loaded = RunRepository(session).get(run.id)
        events = RunRepository(session).list_events(run.id)

    assert loaded is not None
    assert loaded.status is RunStatus.CREATED
    assert loaded.input == {"task": "check status"}
    assert len(events) == 1
    assert events[0].sequence == 1
    assert events[0].type is RunEventType.RUN_CREATED
    assert events[0].payload == {"status": "created"}
