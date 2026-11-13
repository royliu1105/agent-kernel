from uuid import uuid4

import pytest
from kernel_core import ChunkEmbedding, DocumentChunk, DocumentStatus
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    IngestionJobRepository,
    KnowledgeBaseRepository,
    WorkspaceRepository,
)
from kernel_storage.models import DocumentRecord, IngestionJobRecord
from kernel_storage.repositories import DocumentChunkingError, IngestionJobStateError
from sqlalchemy.orm import Session, sessionmaker


def test_knowledge_scope_hides_foreign_and_legacy_data(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        workspace_a = WorkspaceRepository(session).create(name="a", slug="a").id
        workspace_b = WorkspaceRepository(session).create(name="b", slug="b").id
        a = KnowledgeBaseRepository(session, workspace_id=workspace_a)
        b = KnowledgeBaseRepository(session, workspace_id=workspace_b)
        own = a.create(name="a")
        foreign = b.create(name="b")
        legacy = KnowledgeBaseRepository(session).create(name="legacy")
        assert own.workspace_id == workspace_a
        assert [kb.id for kb in a.list()] == [own.id]
        assert a.get(foreign.id) is None
        assert a.get(legacy.id) is None
        assert (
            DocumentRepository(session, workspace_id=workspace_a).create(
                knowledge_base_id=foreign.id, title="forged", source_uri="secret"
            )
            is None
        )


def test_child_repository_scope_checks_before_mutation(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        a = WorkspaceRepository(session).create(name="a", slug="a").id
        b = WorkspaceRepository(session).create(name="b", slug="b").id
        kb = KnowledgeBaseRepository(session, workspace_id=b).create(name="b")
        doc = DocumentRepository(session, workspace_id=b).create(
            knowledge_base_id=kb.id,
            title="secret",
            source_uri=f"object://local/knowledge-bases/{kb.id}/documents/secret.md",
        )
        assert doc is not None
        chunk = DocumentChunk(
            document_id=doc.id,
            index=0,
            content="secret",
            start_char=0,
            end_char=6,
            token_count_estimate=1,
            checksum="sha256:test",
        )
        DocumentChunkRepository(session, workspace_id=b).replace_for_document(
            document_id=doc.id, chunks=[chunk]
        )
        embedding = ChunkEmbedding(
            document_id=doc.id,
            chunk_id=chunk.id,
            model="test",
            dimensions=2,
            vector=[1, 0],
            checksum="sha256:test",
        )
        ChunkEmbeddingRepository(session, workspace_id=b).replace_for_document(
            document_id=doc.id, model="test", embeddings=[embedding]
        )
        job = IngestionJobRepository(session, workspace_id=b).create(document_id=doc.id)
        assert job is not None
        docs = DocumentRepository(session, workspace_id=a)
        chunks = DocumentChunkRepository(session, workspace_id=a)
        embeddings = ChunkEmbeddingRepository(session, workspace_id=a)
        jobs = IngestionJobRepository(session, workspace_id=a)
        assert docs.get(doc.id) is None
        assert docs.list_for_knowledge_base(kb.id) is None
        assert docs.update_status(document_id=doc.id, status=DocumentStatus.FAILED) is None
        assert chunks.get(chunk.id) is None
        assert chunks.list_for_document(doc.id) is None
        assert chunks.replace_for_document(document_id=doc.id, chunks=[]) is None
        assert embeddings.list_for_document(document_id=doc.id) is None
        assert (
            embeddings.replace_for_document(document_id=doc.id, model="test", embeddings=[]) is None
        )
        assert (
            embeddings.similarity_search(knowledge_base_id=kb.id, query_vector=[1, 0], model="test")
            == []
        )
        assert jobs.get(job.id) is None
        assert jobs.list_for_document(doc.id) is None
        assert jobs.create(document_id=doc.id) is None
        assert jobs.mark_parsing(job_id=job.id, parser_name="forged") is None
        assert (
            jobs.complete_parsed(
                job_id=job.id,
                parsed_text_uri="forged",
                parsed_text_checksum="forged",
                parsed_text_size_bytes=1,
                content_char_count=1,
            )
            is None
        )
        assert jobs.fail(job_id=job.id, error_type="forged", error_message="forged") is None
        assert (
            len(
                ChunkEmbeddingRepository(session, workspace_id=b).list_for_document(
                    document_id=doc.id
                )
                or []
            )
            == 1
        )
        updated = DocumentRepository(session, workspace_id=b).get(doc.id)
        assert updated is not None and updated.status is DocumentStatus.INDEXED


@pytest.mark.parametrize(
    "source",
    [
        "object://local/knowledge-bases/{foreign}/documents/secret.md",
        "object://local/knowledge-bases/{own}/documents/../../secret.md",
        "object://local/knowledge-bases/{own}/documents/%2e%2e",
        "object://local/knowledge-bases/{own}/documents/x.md?key=secret",
        "object://local/knowledge-bases/{own}/documents/x.md#fragment",
        "object://local/knowledge-bases/{own}/documents/x\ny.md",
        "file:///tmp/secret",
        "https://example.com/secret",
        "s3://bucket/prefix/knowledge-bases/{foreign}/documents/secret.md",
    ],
)
def test_scoped_source_validation_and_legacy_quarantine(
    sqlite_session_factory: sessionmaker[Session],
    source: str,
) -> None:
    with sqlite_session_factory() as session:
        workspace = WorkspaceRepository(session).create(name="a", slug="a").id
        kb = KnowledgeBaseRepository(session, workspace_id=workspace).create(name="a")
        source = source.format(own=kb.id, foreign=uuid4())
        docs = DocumentRepository(session, workspace_id=workspace)
        with pytest.raises(ValueError, match="source must belong"):
            docs.create(knowledge_base_id=kb.id, title="forged", source_uri=source)
        legacy = DocumentRepository(session).create(
            knowledge_base_id=kb.id,
            title="unsafe legacy",
            source_uri=source,
            status=DocumentStatus.UPLOADED,
        )
        assert legacy is not None
        assert docs.get(legacy.id) is None
        assert docs.list_for_knowledge_base(kb.id) == []
        assert (
            IngestionJobRepository(session, workspace_id=workspace).create(document_id=legacy.id)
            is None
        )


def test_scoped_artifact_and_embedding_references_cannot_cross_documents(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        workspace = WorkspaceRepository(session).create(name="a", slug="a").id
        kb = KnowledgeBaseRepository(session, workspace_id=workspace).create(name="a")
        doc = DocumentRepository(session, workspace_id=workspace).create(
            knowledge_base_id=kb.id,
            title="a",
            source_uri=f"s3://bucket/prefix/knowledge-bases/{kb.id}/documents/a.md",
        )
        assert doc is not None
        jobs = IngestionJobRepository(session, workspace_id=workspace)
        job = jobs.create(document_id=doc.id)
        assert job is not None
        jobs.mark_parsing(job_id=job.id, parser_name="text")
        bad_uri = f"s3://bucket/documents/{uuid4()}/parsed/{job.id}.txt"
        with pytest.raises(IngestionJobStateError, match="artifact must belong"):
            jobs.complete_parsed(
                job_id=job.id,
                parsed_text_uri=bad_uri,
                parsed_text_checksum="x",
                parsed_text_size_bytes=1,
                content_char_count=1,
            )
        record = session.get(IngestionJobRecord, str(job.id))
        assert record is not None
        record.parsed_text_uri = bad_uri
        session.commit()
        assert jobs.get(job.id) is None
        assert jobs.list_for_document(doc.id) == []
        with pytest.raises(DocumentChunkingError, match="chunks must belong"):
            ChunkEmbeddingRepository(session, workspace_id=workspace).replace_for_document(
                document_id=doc.id,
                model="test",
                embeddings=[
                    ChunkEmbedding(
                        document_id=doc.id,
                        chunk_id=uuid4(),
                        model="test",
                        vector=[1.0],
                        dimensions=1,
                        checksum="sha256:test",
                    )
                ],
            )
        stored = session.get(DocumentRecord, str(doc.id))
        assert stored is not None
        assert stored.status == DocumentStatus.PARSING.value
