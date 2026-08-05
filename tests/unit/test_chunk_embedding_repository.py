from uuid import UUID

import pytest
from kernel_core import ChunkEmbedding, Document, DocumentChunk, DocumentStatus, KnowledgeBase
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
    VectorStoreConfigError,
)
from kernel_storage.repositories import _pgvector_literal
from sqlalchemy.orm import Session, sessionmaker


def test_chunk_embedding_repository_replaces_embeddings_for_document_and_model(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base, document, chunks = _create_chunked_document(session)
        repository = ChunkEmbeddingRepository(session)

        first = repository.replace_for_document(
            document_id=document.id,
            model="mock",
            embeddings=[
                ChunkEmbedding(
                    document_id=document.id,
                    chunk_id=chunks[0].id,
                    model="mock",
                    dimensions=2,
                    vector=[1.0, 0.0],
                    checksum="sha256:a",
                )
            ],
        )
        second = repository.replace_for_document(
            document_id=document.id,
            model="mock",
            embeddings=[
                ChunkEmbedding(
                    document_id=document.id,
                    chunk_id=chunks[1].id,
                    model="mock",
                    dimensions=2,
                    vector=[0.0, 1.0],
                    checksum="sha256:b",
                )
            ],
        )
        loaded_document = DocumentRepository(session).get(document.id)

    assert knowledge_base.id == document.knowledge_base_id
    assert first is not None
    assert [embedding.chunk_id for embedding in first] == [chunks[0].id]
    assert second is not None
    assert [embedding.chunk_id for embedding in second] == [chunks[1].id]
    assert loaded_document is not None
    assert loaded_document.status is DocumentStatus.INDEXED


def test_chunk_embedding_repository_similarity_search_ranks_vectors(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base, document, chunks = _create_chunked_document(session)
        repository = ChunkEmbeddingRepository(session)
        embeddings = repository.replace_for_document(
            document_id=document.id,
            model="mock",
            embeddings=[
                ChunkEmbedding(
                    document_id=document.id,
                    chunk_id=chunks[0].id,
                    model="mock",
                    dimensions=2,
                    vector=[1.0, 0.0],
                    checksum="sha256:a",
                ),
                ChunkEmbedding(
                    document_id=document.id,
                    chunk_id=chunks[1].id,
                    model="mock",
                    dimensions=2,
                    vector=[0.0, 1.0],
                    checksum="sha256:b",
                ),
            ],
        )
        assert embeddings is not None

        results = repository.similarity_search(
            knowledge_base_id=knowledge_base.id,
            query_vector=[0.9, 0.1],
            model="mock",
            limit=2,
        )

    assert [embedding.chunk_id for embedding, _score in results] == [chunks[0].id, chunks[1].id]
    assert results[0][1] > results[1][1]


def test_chunk_embedding_repository_json_mode_ranks_vectors(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        knowledge_base, document, chunks = _create_chunked_document(session)
        repository = ChunkEmbeddingRepository(session, vector_store_mode="json")
        embeddings = repository.replace_for_document(
            document_id=document.id,
            model="mock",
            embeddings=[
                ChunkEmbedding(
                    document_id=document.id,
                    chunk_id=chunks[0].id,
                    model="mock",
                    dimensions=2,
                    vector=[1.0, 0.0],
                    checksum="sha256:a",
                ),
                ChunkEmbedding(
                    document_id=document.id,
                    chunk_id=chunks[1].id,
                    model="mock",
                    dimensions=2,
                    vector=[0.0, 1.0],
                    checksum="sha256:b",
                ),
            ],
        )
        assert embeddings is not None

        results = repository.similarity_search(
            knowledge_base_id=knowledge_base.id,
            query_vector=[0.9, 0.1],
            model="mock",
            limit=2,
        )

    assert [embedding.chunk_id for embedding, _score in results] == [chunks[0].id, chunks[1].id]


def test_chunk_embedding_repository_pgvector_mode_requires_postgres(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    with sqlite_session_factory() as session:
        _knowledge_base, document, chunks = _create_chunked_document(session)
        repository = ChunkEmbeddingRepository(session, vector_store_mode="pgvector")

        with pytest.raises(VectorStoreConfigError, match="requires a PostgreSQL database"):
            repository.replace_for_document(
                document_id=document.id,
                model="mock",
                embeddings=[
                    ChunkEmbedding(
                        document_id=document.id,
                        chunk_id=chunks[0].id,
                        model="mock",
                        dimensions=2,
                        vector=[1.0, 0.0],
                        checksum="sha256:a",
                    )
                ],
            )


def test_pgvector_literal_validates_vector_values() -> None:
    assert _pgvector_literal([1, -0.25, 0.333333333333]) == "[1,-0.25,0.333333333333]"

    with pytest.raises(VectorStoreConfigError, match="non-empty"):
        _pgvector_literal([])
    with pytest.raises(VectorStoreConfigError, match="numeric"):
        _pgvector_literal([True])
    with pytest.raises(VectorStoreConfigError, match="finite"):
        _pgvector_literal([float("nan")])


def test_chunk_embedding_repository_returns_none_for_missing_document(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    missing_document_id = UUID("00000000-0000-0000-0000-000000000030")

    with sqlite_session_factory() as session:
        embeddings = ChunkEmbeddingRepository(session).replace_for_document(
            document_id=missing_document_id,
            model="mock",
            embeddings=[],
        )
        listed = ChunkEmbeddingRepository(session).list_for_document(
            document_id=missing_document_id
        )

    assert embeddings is None
    assert listed is None


def _create_chunked_document(
    session: Session,
) -> tuple[KnowledgeBase, Document, list[DocumentChunk]]:
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
    return knowledge_base, document, chunks
