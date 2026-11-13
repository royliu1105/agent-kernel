from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from kernel_storage import (
    DocumentRepository,
    EvalRunRepository,
    KnowledgeBaseRepository,
    MemoryRepository,
    WorkspaceRepository,
    create_session_factory,
)
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine.reflection import Inspector

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_DIR = REPO_ROOT / "packages" / "kernel-storage" / "src" / "kernel_storage" / "migrations"
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
LATEST_REVISION = "0018_usage_attribution"


def test_sqlite_migrations_upgrade_to_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "agent_kernel.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    command.upgrade(_alembic_config(), "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        assert {
            "agents",
            "runs",
            "workspaces",
            "api_keys",
            "worker_leases",
            "eval_runs",
            "model_usage",
        }.issubset(table_names)
        assert "workspace_id" in _column_names(inspector, "agents")
        assert "workspace_id" in _column_names(inspector, "runs")
        assert "principal_id" in _column_names(inspector, "runs")
        assert "workspace_id" in _column_names(inspector, "knowledge_bases")
        assert "workspace_id" in _column_names(inspector, "memory_items")
        assert "workspace_id" in _column_names(inspector, "eval_runs")

        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    finally:
        engine.dispose()

    assert version == LATEST_REVISION


def test_migration_revision_ids_fit_alembic_version_column() -> None:
    for migration_file in (MIGRATION_DIR / "versions").glob("*.py"):
        tree = ast.parse(migration_file.read_text())
        revision = _find_string_assignment(tree, "revision")

        assert revision is not None, f"{migration_file.name} is missing revision"
        assert len(revision) <= 32, (
            f"{migration_file.name} revision id {revision!r} exceeds Alembic's "
            "default version_num VARCHAR(32) column"
        )


def test_sqlite_knowledge_upgrade_preserves_unowned_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.upgrade(_alembic_config(), "0014_create_eval_runs")
    engine = create_engine(database_url)
    legacy_id = uuid4()
    document_id = uuid4()
    try:
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
            connection.execute(
                text("""
                INSERT INTO documents
                    (id, knowledge_base_id, title, source_uri, status,
                     metadata, created_at, updated_at)
                VALUES (:id, :kb, 'legacy document', :uri, 'uploaded', '{}',
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
                {
                    "id": str(document_id),
                    "kb": str(legacy_id),
                    "uri": f"object://local/knowledge-bases/{legacy_id}/documents/legacy.md",
                },
            )
        command.upgrade(_alembic_config(), "head")
        with create_session_factory(engine)() as session:
            local = KnowledgeBaseRepository(session).get(legacy_id)
            assert local is not None and local.workspace_id is None
            workspace = WorkspaceRepository(session).create(name="a", slug="a")
            assert MemoryRepository(session).get(legacy_id) is not None
            assert EvalRunRepository(session).get(legacy_id) is not None
            assert MemoryRepository(session, workspace_id=workspace.id).get(legacy_id) is None
            assert EvalRunRepository(session, workspace_id=workspace.id).get(legacy_id) is None
            scoped = KnowledgeBaseRepository(session, workspace_id=workspace.id)
            assert scoped.get(legacy_id) is None
            assert scoped.list() == []
            documents = DocumentRepository(session, workspace_id=workspace.id)
            assert documents.get(document_id) is None
            assert DocumentRepository(session).get(document_id) is not None
            session.execute(
                text("""
                UPDATE knowledge_bases SET workspace_id = :workspace_id
                WHERE id = :id AND workspace_id IS NULL
                    AND EXISTS (SELECT 1 FROM workspaces WHERE id = :workspace_id)
            """),
                {"workspace_id": str(workspace.id), "id": str(legacy_id)},
            )
            session.commit()
            assert scoped.get(legacy_id) is not None
            assert documents.get(document_id) is not None
        command.downgrade(_alembic_config(), "0014_create_eval_runs")
        assert "workspace_id" not in _column_names(inspect(engine), "knowledge_bases")
        command.upgrade(_alembic_config(), "head")
    finally:
        engine.dispose()


def test_pgvector_migration_is_guarded_for_postgres() -> None:
    migration_file = MIGRATION_DIR / "versions" / "0013_pgvector_embeddings.py"

    content = migration_file.read_text()

    assert 'bind.dialect.name != "postgresql"' in content
    assert "CREATE EXTENSION IF NOT EXISTS vector" in content
    assert "vector_pg vector" in content
    assert "vector_pg::vector(1536)" in content
    assert "WHERE dimensions = 1536" in content
    assert "USING hnsw" in content


def _alembic_config() -> Config:
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATION_DIR))
    return config


def _column_names(inspector: Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _find_string_assignment(tree: ast.Module, name: str) -> str | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    return None
