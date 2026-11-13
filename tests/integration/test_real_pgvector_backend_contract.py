"""Native backend contracts beyond the workspace-isolation happy path."""

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from kernel_core import ChunkEmbedding, DocumentChunk
from kernel_storage import (
    ChunkEmbeddingRepository,
    DocumentChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
    create_session_factory,
)
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def pg_backend(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    url = os.environ.get("AGENT_KERNEL_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set AGENT_KERNEL_TEST_POSTGRES_URL to a dedicated pgvector test service.")
    assert make_url(url).get_backend_name() == "postgresql"
    schema = f"test_backend_{uuid4().hex}"
    admin = create_engine(url)
    scoped = make_url(url).update_query_dict({"options": f"-csearch_path={schema},public"})
    engine = create_engine(scoped)
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    monkeypatch.setenv("DATABASE_URL", scoped.render_as_string(hide_password=False))
    try:
        with admin.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(
                text(
                    f'CREATE TABLE "{schema}".alembic_version '
                    "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                )
            )
        command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()


def test_native_pgvector_model_dimension_ranking_replacement_and_rollback(
    pg_backend: Engine,
) -> None:
    with create_session_factory(pg_backend)() as session:
        kb = KnowledgeBaseRepository(session).create(name="backend-contract")
        document = DocumentRepository(session).create(
            knowledge_base_id=kb.id, title="vectors", source_uri="test-fixture"
        )
        assert document is not None
        chunks = [
            DocumentChunk(
                document_id=document.id,
                index=index,
                content=f"chunk {index}",
                start_char=index * 10,
                end_char=index * 10 + 7,
                token_count_estimate=2,
                checksum=f"fixture-{index}",
            )
            for index in range(3)
        ]
        DocumentChunkRepository(session).replace_for_document(
            document_id=document.id, chunks=chunks
        )
        repository = ChunkEmbeddingRepository(session, vector_store_mode="pgvector")
        embeddings = [
            ChunkEmbedding(
                document_id=document.id,
                chunk_id=chunk.id,
                model="contract",
                dimensions=3,
                vector=vector,
                checksum=chunk.checksum,
            )
            for chunk, vector in zip(chunks, [[1.0, 0, 0], [0, 1.0, 0], [-1.0, 0, 0]], strict=True)
        ]
        repository.replace_for_document(
            document_id=document.id, model="contract", embeddings=embeddings
        )
        repository.replace_for_document(
            document_id=document.id,
            model="other",
            embeddings=[
                ChunkEmbedding(
                    document_id=document.id,
                    chunk_id=chunks[0].id,
                    model="other",
                    dimensions=4,
                    vector=[1.0, 0, 0, 0],
                    checksum="other",
                )
            ],
        )
        hits = repository.similarity_search(
            knowledge_base_id=kb.id, query_vector=[1.0, 0, 0], model="contract", limit=2
        )
        assert [hit.id for hit, _ in hits] == [embedding.id for embedding in embeddings[:2]]
        assert [score for _, score in hits] == pytest.approx([1.0, 0.0])
        assert (
            repository.similarity_search(
                knowledge_base_id=kb.id, query_vector=[1.0, 0, 0], model="other"
            )
            == []
        )
        assert (
            repository.similarity_search(
                knowledge_base_id=kb.id, query_vector=[1.0, 0, 0, 0], model="contract"
            )
            == []
        )
        assert (
            repository.similarity_search(
                knowledge_base_id=kb.id, query_vector=[1.0, 0, 0], model="missing"
            )
            == []
        )
        with pytest.raises(IntegrityError):
            repository.replace_for_document(
                document_id=document.id, model="contract", embeddings=[embeddings[0], embeddings[0]]
            )
        session.rollback()
        assert {
            item.id
            for item in repository.list_for_document(document_id=document.id, model="contract")
            or []
        } == {item.id for item in embeddings}
        changed = embeddings[0].model_copy(update={"id": uuid4(), "vector": [0, 0, 1.0]})
        repository.replace_for_document(
            document_id=document.id, model="contract", embeddings=[changed]
        )
        hits = repository.similarity_search(
            knowledge_base_id=kb.id, query_vector=[0, 0, 1.0], model="contract"
        )
        assert len(hits) == 1 and hits[0][0].id == changed.id
        assert hits[0][1] == pytest.approx(1.0)
        assert len(repository.list_for_document(document_id=document.id, model="other") or []) == 1
        repository.replace_for_document(document_id=document.id, model="contract", embeddings=[])
        assert (
            repository.similarity_search(
                knowledge_base_id=kb.id, query_vector=[1.0, 0, 0], model="contract"
            )
            == []
        )
