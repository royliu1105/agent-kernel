"""Opt-in PostgreSQL contracts; each test owns a disposable schema."""

import os
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
    EvalRunRepository,
    KnowledgeBaseRepository,
    MemoryRepository,
    WorkspaceRepository,
    create_session_factory,
)
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


@pytest.mark.parametrize("legacy", [False, True], ids=["fresh", "upgrade"])
def test_real_pgvector_scope_and_knowledge_migration(
    monkeypatch: pytest.MonkeyPatch,
    legacy: bool,
) -> None:
    url = os.environ.get("AGENT_KERNEL_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set AGENT_KERNEL_TEST_POSTGRES_URL to a dedicated pgvector test database.")
    assert make_url(url).get_backend_name() == "postgresql"
    schema = f"test_knowledge_{uuid4().hex}"
    admin = create_engine(url)
    scoped_url = make_url(url).update_query_dict({"options": f"-csearch_path={schema},public"})
    engine = create_engine(scoped_url)
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option(
        "script_location", str(root / "packages/kernel-storage/src/kernel_storage/migrations")
    )
    monkeypatch.setenv("DATABASE_URL", scoped_url.render_as_string(hide_password=False))
    try:
        with admin.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            # Do not discover the application's public.alembic_version via search_path.
            connection.execute(
                text(
                    f'CREATE TABLE "{schema}".alembic_version '
                    "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                )
            )
        legacy_id = uuid4()
        if legacy:
            command.upgrade(config, "0014_create_eval_runs")
            with engine.begin() as connection:
                connection.execute(
                    text("""
                    INSERT INTO memory_items
                        (id, type, scope, content, confidence, metadata, created_at)
                    VALUES (:id, 'long_term', 'legacy', '{}', 1.0, '{}', CURRENT_TIMESTAMP)
                """),
                    {"id": str(legacy_id)},
                )
                connection.execute(
                    text("""
                    INSERT INTO eval_runs (id, name, suite_type, status, passed, case_count,
                        passed_count, failed_count, report, metadata, created_at)
                    VALUES (:id, 'legacy', 'test', 'succeeded', true, 0, 0, 0,
                        '{}', '{}', CURRENT_TIMESTAMP)
                """),
                    {"id": str(legacy_id)},
                )
                connection.execute(
                    text("""
                    INSERT INTO knowledge_bases
                        (id, name, description, status, metadata, created_at, updated_at)
                    VALUES (:id, 'legacy', '', 'active', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """),
                    {"id": str(legacy_id)},
                )
        command.upgrade(config, "head")
        assert "workspace_id" in {c["name"] for c in inspect(engine).get_columns("knowledge_bases")}
        with create_session_factory(engine)() as session:
            a = WorkspaceRepository(session).create(name="a", slug="a").id
            b = WorkspaceRepository(session).create(name="b", slug="b").id
            kb_a = KnowledgeBaseRepository(session, workspace_id=a).create(name="a")
            kb_b = KnowledgeBaseRepository(session, workspace_id=b).create(name="b")
            for kb, owner in [(kb_a, a), (kb_b, b)]:
                doc = DocumentRepository(session, workspace_id=owner).create(
                    knowledge_base_id=kb.id,
                    title=kb.name,
                    source_uri=f"s3://test/knowledge-bases/{kb.id}/documents/a.md",
                )
                assert doc is not None
                chunk = DocumentChunk(
                    document_id=doc.id,
                    index=0,
                    content=kb.name,
                    start_char=0,
                    end_char=1,
                    token_count_estimate=1,
                    checksum="test",
                )
                DocumentChunkRepository(session, workspace_id=owner).replace_for_document(
                    document_id=doc.id, chunks=[chunk]
                )
                embeddings = ChunkEmbeddingRepository(
                    session, workspace_id=owner, vector_store_mode="pgvector"
                )
                embeddings.replace_for_document(
                    document_id=doc.id,
                    model="test",
                    embeddings=[
                        ChunkEmbedding(
                            document_id=doc.id,
                            chunk_id=chunk.id,
                            model="test",
                            dimensions=3,
                            vector=[1, 0, 0],
                            checksum="test",
                        )
                    ],
                )
            scoped = ChunkEmbeddingRepository(session, workspace_id=a, vector_store_mode="pgvector")
            own_results = scoped.similarity_search(
                knowledge_base_id=kb_a.id, query_vector=[1, 0, 0], model="test"
            )
            assert len(own_results) == 1 and own_results[0][1] == pytest.approx(1.0)
            assert (
                scoped.similarity_search(
                    knowledge_base_id=kb_b.id, query_vector=[1, 0, 0], model="test"
                )
                == []
            )
            assert KnowledgeBaseRepository(session, workspace_id=a).get(kb_b.id) is None
            if legacy:
                assert MemoryRepository(session).get(legacy_id) is not None
                assert EvalRunRepository(session).get(legacy_id) is not None
                assert MemoryRepository(session, workspace_id=a).get(legacy_id) is None
                assert EvalRunRepository(session, workspace_id=a).get(legacy_id) is None
                old = KnowledgeBaseRepository(session).get(legacy_id)
                assert old is not None and old.workspace_id is None
                assert KnowledgeBaseRepository(session, workspace_id=a).get(legacy_id) is None
        command.downgrade(config, "0014_create_eval_runs")
        assert "workspace_id" not in {
            c["name"] for c in inspect(engine).get_columns("knowledge_bases")
        }
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()
