from kernel_core import DocumentChunk, DocumentStatus
from kernel_rag import DocumentIndexingService, MockEmbeddingProvider
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from sqlalchemy.orm import Session, sessionmaker


def test_mock_embedding_provider_is_deterministic() -> None:
    provider = MockEmbeddingProvider()

    first = provider.embed_texts(["alpha", "beta"])
    second = provider.embed_texts(["alpha", "beta"])

    assert first == second
    assert len(first) == 2
    assert all(len(vector) == provider.dimensions for vector in first)
    assert first[0] != first[1]


def test_document_indexing_service_indexes_chunked_document(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    provider = MockEmbeddingProvider()

    with sqlite_session_factory() as session:
        knowledge_base = KnowledgeBaseRepository(session).create(name="kb")
        document = DocumentRepository(session).create(
            knowledge_base_id=knowledge_base.id,
            title="Chunked",
            source_uri="object://local/source.md",
            status=DocumentStatus.CHUNKED,
        )
        assert document is not None
        chunks = DocumentChunkRepository(session).replace_for_document(
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
                ),
                DocumentChunk(
                    document_id=document.id,
                    index=1,
                    content="beta",
                    start_char=6,
                    end_char=10,
                    token_count_estimate=1,
                    checksum="sha256:b",
                ),
            ],
        )
        assert chunks is not None

        result = DocumentIndexingService(embedding_provider=provider).index_document(
            document_id=document.id,
            document_repository=DocumentRepository(session),
            chunk_repository=DocumentChunkRepository(session),
            embedding_repository=ChunkEmbeddingRepository(session),
        )
        embeddings = ChunkEmbeddingRepository(session).list_for_document(document_id=document.id)
        loaded_document = DocumentRepository(session).get(document.id)

    assert result.document_id == document.id
    assert result.model == provider.model
    assert result.dimensions == provider.dimensions
    assert result.embedding_count == 2
    assert embeddings is not None
    assert len(embeddings) == 2
    assert all(embedding.model == provider.model for embedding in embeddings)
    assert loaded_document is not None
    assert loaded_document.status is DocumentStatus.INDEXED
