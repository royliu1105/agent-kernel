from uuid import UUID

from kernel_core import DocumentStatus, KnowledgeBaseStatus, RunEventType, RunStatus
from kernel_storage import (
    AgentRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
    RunRepository,
)
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


def test_run_repository_updates_status_and_appends_monotonic_events(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="ops-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "queue"})

        updated = RunRepository(session).update_status(run_id=run.id, status=RunStatus.QUEUED)
        event = RunRepository(session).append_event(
            run_id=run.id,
            event_type=RunEventType.RUN_QUEUED,
            payload={"from_status": "created", "to_status": "queued"},
        )
        events = RunRepository(session).list_events(run.id)

    assert updated is not None
    assert updated.status is RunStatus.QUEUED
    assert event is not None
    assert event.sequence == 2
    assert [timeline_event.sequence for timeline_event in events] == [1, 2]
    assert events[1].type is RunEventType.RUN_QUEUED


def test_run_repository_lists_queued_runs(sqlite_session_factory: sessionmaker[Session]) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="ops-agent")
        created_run = RunRepository(session).create(
            agent_id=agent.id,
            input_payload={"task": "stay created"},
        )
        queued_run = RunRepository(session).create(
            agent_id=agent.id,
            input_payload={"task": "queue"},
        )
        RunRepository(session).update_status(run_id=queued_run.id, status=RunStatus.QUEUED)

        queued = RunRepository(session).list_queued()

    assert [run.id for run in queued] == [queued_run.id]
    assert created_run.id not in {run.id for run in queued}


def test_run_repository_completes_run_with_output_and_usage(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="ops-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "finish"})

        completed = RunRepository(session).complete(
            run_id=run.id,
            output_payload={"text": "done"},
            input_tokens_total=3,
            output_tokens_total=2,
            estimated_cost_total=0.0,
            event_payload={"from_status": "running", "to_status": "succeeded"},
        )
        events = RunRepository(session).list_events(run.id)

    assert completed is not None
    assert completed.status is RunStatus.SUCCEEDED
    assert completed.output == {"text": "done"}
    assert completed.input_tokens_total == 3
    assert completed.output_tokens_total == 2
    assert events[-1].type is RunEventType.RUN_COMPLETED


def test_run_repository_fails_run_with_error_details(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        agent = AgentRepository(session).create(name="ops-agent")
        run = RunRepository(session).create(agent_id=agent.id, input_payload={"task": "fail"})

        failed = RunRepository(session).fail(
            run_id=run.id,
            error_type="provider_error",
            error_message="provider unavailable",
            event_payload={"from_status": "running", "to_status": "failed"},
        )
        events = RunRepository(session).list_events(run.id)

    assert failed is not None
    assert failed.status is RunStatus.FAILED
    assert failed.error_type == "provider_error"
    assert failed.error_message == "provider unavailable"
    assert events[-1].type is RunEventType.RUN_FAILED


def test_knowledge_base_repository_creates_loads_and_lists(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        repository = KnowledgeBaseRepository(session)
        created = repository.create(
            name="engineering-handbook",
            description="Internal engineering knowledge.",
            metadata={"owner": "platform"},
        )

        loaded = repository.get(created.id)
        knowledge_bases = repository.list()

    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.name == "engineering-handbook"
    assert loaded.status is KnowledgeBaseStatus.ACTIVE
    assert loaded.metadata == {"owner": "platform"}
    assert [knowledge_base.id for knowledge_base in knowledge_bases] == [created.id]


def test_document_repository_registers_and_lists_documents(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="engineering-handbook")

        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Deployment Guide",
            source_uri="object://local/docs/deployment.md",
            mime_type="text/markdown",
            checksum="sha256:abc",
            size_bytes=1234,
            metadata={"source": "manual"},
        )
        assert document is not None

        loaded = DocumentRepository(session).get(document.id)
        documents = DocumentRepository(session).list_for_knowledge_base(knowledge_base.id)

    assert loaded is not None
    assert loaded.id == document.id
    assert loaded.knowledge_base_id == knowledge_base.id
    assert loaded.title == "Deployment Guide"
    assert loaded.status is DocumentStatus.REGISTERED
    assert loaded.source_uri == "object://local/docs/deployment.md"
    assert loaded.mime_type == "text/markdown"
    assert loaded.checksum == "sha256:abc"
    assert loaded.size_bytes == 1234
    assert loaded.metadata == {"source": "manual"}
    assert documents is not None
    assert [item.id for item in documents] == [document.id]


def test_document_repository_returns_none_for_missing_knowledge_base(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    missing_knowledge_base_id = UUID("00000000-0000-0000-0000-000000000010")

    with sqlite_session_factory() as session:
        document = DocumentRepository(session).create(
            knowledge_base_id=missing_knowledge_base_id,
            title="Missing KB",
            source_uri="object://local/missing.md",
        )
        documents = DocumentRepository(session).list_for_knowledge_base(
            missing_knowledge_base_id
        )

    assert document is None
    assert documents is None
