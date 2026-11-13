"""Usage migration preserves history without inventing attribution."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


@pytest.mark.parametrize("backend", ["sqlite", "postgres"])
def test_usage_migration_preserves_unknown_history_and_downgrades(
    backend: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = None
    schema = f"test_usage_{uuid4().hex}"
    if backend == "postgres":
        source = os.environ.get("AGENT_KERNEL_TEST_POSTGRES_URL")
        if not source:
            pytest.skip("Requires disposable PostgreSQL for migration contract.")
        admin = create_engine(source)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(
                text(
                    f'CREATE TABLE "{schema}".alembic_version '
                    "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                )
            )
        url = make_url(source).update_query_dict({"options": f"-csearch_path={schema},public"})
    else:
        url = make_url(f"sqlite:///{tmp_path / 'usage.db'}")
    monkeypatch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    engine = create_engine(url)
    run_id, agent_id = str(uuid4()), str(uuid4())
    try:
        command.upgrade(config, "0017_unique_active_lease")
        if admin is not None:
            assert "runs" in inspect(engine).get_table_names(schema=schema)
        with engine.begin() as connection:
            connection.execute(
                text("""
                INSERT INTO agents (id, name, description, status, memory_policy,
                                    tool_policy, metadata, created_at)
                VALUES (:id, 'legacy', '', 'active', '{}', '{}', '{}', CURRENT_TIMESTAMP)
            """),
                {"id": agent_id},
            )
            connection.execute(
                text("""
                INSERT INTO runs (id, agent_id, status, input, input_tokens_total,
                    output_tokens_total, estimated_cost_total, created_at)
                VALUES (:id, :agent, 'succeeded', '{"principal_id":"not-trusted"}',
                        12, 3, 0.5, CURRENT_TIMESTAMP)
            """),
                {"id": run_id, "agent": agent_id},
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            row = connection.execute(text("SELECT principal_id, estimated_cost_total FROM runs"))
            assert row.one() == (None, 0.5)
            usage = connection.execute(
                text("""
                SELECT run_id, provider, model, input_tokens, output_tokens, estimated_cost
                FROM model_usage
            """)
            ).one()
            assert usage == (run_id, "unknown", "unknown", 12, 3, 0.5)
        command.downgrade(config, "0017_unique_active_lease")
        assert "principal_id" not in {col["name"] for col in inspect(engine).get_columns("runs")}
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT estimated_cost_total FROM runs")) == 0.5
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM model_usage")) == 1
    finally:
        engine.dispose()
        if admin is not None:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()
