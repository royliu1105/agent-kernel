from uuid import UUID

import pytest
from kernel_core import DocumentChunk, DocumentStatus
from kernel_rag import (
    DocumentIndexingService,
    KnowledgeBaseNotFoundError,
    MockEmbeddingProvider,
    Retriever,
)
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from sqlalchemy.orm import Session, sessionmaker


def test_retriever_returns_ranked_chunks_with_citations(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Deployment Guide",
            source_uri="object://local/docs/deployment.md",
            status=DocumentStatus.CHUNKED,
            metadata={"source": "manual"},
        )
        assert document is not None
        chunks = DocumentChunkRepository(session).replace_for_document(
            document_id=document.id,
            chunks=[
                DocumentChunk(
                    document_id=document.id,
                    index=0,
                    content="alpha deployment rollback checklist",
                    start_char=0,
                    end_char=35,
                    token_count_estimate=4,
                    checksum="sha256:a",
                    metadata={"heading": "Rollback"},
                ),
                DocumentChunk(
                    document_id=document.id,
                    index=1,
                    content="beta incident communication plan",
                    start_char=36,
                    end_char=68,
                    token_count_estimate=4,
                    checksum="sha256:b",
                ),
            ],
        )
        assert chunks is not None
        DocumentIndexingService().index_document(
            document_id=document.id,
            document_repository=DocumentRepository(session),
            chunk_repository=DocumentChunkRepository(session),
            embedding_repository=ChunkEmbeddingRepository(session),
        )

        response = Retriever().retrieve(
            knowledge_base_id=knowledge_base.id,
            query="alpha deployment rollback checklist",
            top_k=1,
            knowledge_base_repository=KnowledgeBaseRepository(session),
            document_repository=DocumentRepository(session),
            chunk_repository=DocumentChunkRepository(session),
            embedding_repository=ChunkEmbeddingRepository(session),
        )

    assert response.knowledge_base_id == knowledge_base.id
    assert response.query == "alpha deployment rollback checklist"
    assert response.model == MockEmbeddingProvider.model
    assert len(response.results) == 1
    result = response.results[0]
    assert result.content == "alpha deployment rollback checklist"
    assert result.score == pytest.approx(1.0)
    assert result.citation.knowledge_base_id == knowledge_base.id
    assert result.citation.document_id == document.id
    assert result.citation.document_title == "Deployment Guide"
    assert result.citation.document_source_uri == "object://local/docs/deployment.md"
    assert result.citation.chunk_id == chunks[0].id
    assert result.citation.chunk_index == 0
    assert result.citation.start_char == 0
    assert result.citation.end_char == 35
    assert result.metadata["document_metadata"] == {"source": "manual"}
    assert result.metadata["chunk_metadata"] == {"heading": "Rollback"}


def test_retriever_returns_empty_results_for_empty_knowledge_base(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="empty")

        response = Retriever().retrieve(
            knowledge_base_id=knowledge_base.id,
            query="anything",
            knowledge_base_repository=KnowledgeBaseRepository(session),
            document_repository=DocumentRepository(session),
            chunk_repository=DocumentChunkRepository(session),
            embedding_repository=ChunkEmbeddingRepository(session),
        )

    assert response.results == []


def test_retriever_raises_for_missing_knowledge_base(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session, pytest.raises(KnowledgeBaseNotFoundError):
        Retriever().retrieve(
            knowledge_base_id=UUID("00000000-0000-0000-0000-000000000000"),
            query="anything",
            knowledge_base_repository=KnowledgeBaseRepository(session),
            document_repository=DocumentRepository(session),
            chunk_repository=DocumentChunkRepository(session),
            embedding_repository=ChunkEmbeddingRepository(session),
        )
