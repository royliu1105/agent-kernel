from uuid import UUID

import pytest
from kernel_core import DocumentChunk, DocumentStatus
from kernel_storage import (
    DocumentChunkingError,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from sqlalchemy.orm import Session, sessionmaker


def test_document_chunk_repository_replaces_chunks_and_marks_document_chunked(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Parsed",
            source_uri="object://local/source.md",
            status=DocumentStatus.PARSED,
        )
        assert document is not None
        repository = DocumentChunkRepository(session)

        first = repository.replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=0,
                    content="alpha",
                    start_char=0,
                    end_char=5,
                    token_count_estimate=2,
                    checksum="sha256:a",
                )
            ],
        )
        second = repository.replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=0,
                    content="beta",
                    start_char=0,
                    end_char=4,
                    token_count_estimate=1,
                    checksum="sha256:b",
                ),
                DocumentChunk(
                    document_id=document.id,
                    index=1,
                    content="gamma",
                    start_char=4,
                    end_char=9,
                    token_count_estimate=2,
                    checksum="sha256:c",
                ),
            ],
        )
        loaded_document = DocumentRepository(session).get(document.id)

    assert first is not None
    assert [chunk.content for chunk in first] == ["alpha"]
    assert second is not None
    assert [chunk.index for chunk in second] == [0, 1]
    assert [chunk.content for chunk in second] == ["beta", "gamma"]
    assert loaded_document is not None
    assert loaded_document.status is DocumentStatus.CHUNKED


def test_document_chunk_repository_gets_and_lists_chunks(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Parsed",
            source_uri="object://local/source.md",
            status=DocumentStatus.PARSED,
        )
        assert document is not None
        chunks = DocumentChunkRepository(session).replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=1,
                    content="second",
                    start_char=10,
                    end_char=16,
                    token_count_estimate=2,
                    checksum="sha256:2",
                ),
                DocumentChunk(
                    document_id=document.id,
                    index=0,
                    content="first",
                    start_char=0,
                    end_char=5,
                    token_count_estimate=2,
                    checksum="sha256:1",
                ),
            ],
        )
        assert chunks is not None
        loaded = DocumentChunkRepository(session).get(chunks[0].id)
        listed = DocumentChunkRepository(session).list_for_document(document.id)

    assert loaded is not None
    assert loaded.id == chunks[0].id
    assert listed is not None
    assert [chunk.index for chunk in listed] == [0, 1]


def test_document_chunk_repository_rejects_mismatched_document_id(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Parsed",
            source_uri="object://local/source.md",
            status=DocumentStatus.PARSED,
        )
        assert document is not None

        with pytest.raises(DocumentChunkingError):
            DocumentChunkRepository(session).replace_for_document(
                document_id=document.id,
                chunks=[
                    DocumentChunk(
                        document_id=UUID("00000000-0000-0000-0000-000000000020"),
                        index=0,
                        content="wrong",
                        start_char=0,
                        end_char=5,
                        token_count_estimate=2,
                        checksum="sha256:wrong",
                    )
                ],
            )


def test_document_chunk_repository_returns_none_for_missing_document(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    missing_document_id = UUID("00000000-0000-0000-0000-000000000021")

    with sqlite_session_factory() as session:
        chunks = DocumentChunkRepository(session).replace_for_document(
            document_id=missing_document_id,
            chunks=[],
        )
        listed = DocumentChunkRepository(session).list_for_document(missing_document_id)

    assert chunks is None
    assert listed is None
