from uuid import UUID

import pytest
from kernel_core import DocumentStatus, IngestionJobStatus
from kernel_storage import (
    DocumentRepository,
    IngestionJobRepository,
    IngestionJobStateError,
    KnowledgeBaseRepository,
)
from sqlalchemy.orm import Session, sessionmaker


def test_ingestion_job_repository_transitions_document_to_parsed(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Deploy",
            source_uri="object://local/source.md",
            status=DocumentStatus.UPLOADED,
        )
        assert document is not None

        job_repository = IngestionJobRepository(session)
        job = job_repository.create(document_id=document.id)
        assert job is not None
        parsing = job_repository.mark_parsing(job_id=job.id, parser_name="text-markdown")
        completed = job_repository.complete_parsed(
            job_id=job.id,
            parsed_text_uri="object://local/parsed.txt",
            parsed_text_checksum="sha256:abc",
            parsed_text_size_bytes=12,
            content_char_count=12,
        )
        loaded_document = DocumentRepository(session).get(document.id)
        jobs = job_repository.list_for_document(document.id)

    assert parsing is not None
    assert parsing.status is IngestionJobStatus.PARSING
    assert completed is not None
    assert completed.status is IngestionJobStatus.PARSED
    assert completed.parser_name == "text-markdown"
    assert completed.parsed_text_uri == "object://local/parsed.txt"
    assert completed.content_char_count == 12
    assert loaded_document is not None
    assert loaded_document.status is DocumentStatus.PARSED
    assert jobs is not None
    assert [item.id for item in jobs] == [job.id]


def test_ingestion_job_repository_failure_marks_document_failed(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Deploy",
            source_uri="object://local/source.md",
            status=DocumentStatus.UPLOADED,
        )
        assert document is not None
        job = IngestionJobRepository(session).create(document_id=document.id)
        assert job is not None

        failed = IngestionJobRepository(session).fail(
            job_id=job.id,
            error_type="parser_error",
            error_message="bad text",
        )
        loaded_document = DocumentRepository(session).get(document.id)

    assert failed is not None
    assert failed.status is IngestionJobStatus.FAILED
    assert failed.error_type == "parser_error"
    assert loaded_document is not None
    assert loaded_document.status is DocumentStatus.FAILED
    assert loaded_document.error_message == "bad text"


def test_ingestion_job_repository_rejects_invalid_transition(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Deploy",
            source_uri="object://local/source.md",
            status=DocumentStatus.UPLOADED,
        )
        assert document is not None
        job = IngestionJobRepository(session).create(document_id=document.id)
        assert job is not None

        with pytest.raises(IngestionJobStateError):
            IngestionJobRepository(session).complete_parsed(
                job_id=job.id,
                parsed_text_uri="object://local/parsed.txt",
                parsed_text_checksum="sha256:abc",
                parsed_text_size_bytes=12,
                content_char_count=12,
            )


def test_ingestion_job_repository_returns_none_for_missing_document(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    missing_document_id = UUID("00000000-0000-0000-0000-000000000012")

    with sqlite_session_factory() as session:
        created = IngestionJobRepository(session).create(document_id=missing_document_id)
        jobs = IngestionJobRepository(session).list_for_document(missing_document_id)

    assert created is None
    assert jobs is None
