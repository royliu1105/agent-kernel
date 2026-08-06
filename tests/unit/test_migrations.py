from __future__ import annotations

import ast
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine.reflection import Inspector

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_DIR = (
    REPO_ROOT
    / "packages"
    / "kernel-storage"
    / "src"
    / "kernel_storage"
    / "migrations"
)
ALEMBIC_INI = REPO_ROOT / "alembic.ini"
LATEST_REVISION = "0014_create_eval_runs"


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
        }.issubset(table_names)
        assert "workspace_id" in _column_names(inspector, "agents")
        assert "workspace_id" in _column_names(inspector, "runs")

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
