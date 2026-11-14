"""Database fixture safety is independent of the live runtime configuration."""

import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from scripts import testing_database


def test_collection_rejects_business_database_before_loading_tests() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "tests/unit/test_storage_config.py",
        ],
        cwd=testing_database.ROOT,
        env={
            **os.environ,
            "AGENT_KERNEL_TEST_POSTGRES_URL": "postgresql://user:PRIVATE@localhost/agent_kernel",
        },
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 4
    assert "Test database name" in result.stderr
    assert "PRIVATE" not in result.stderr


def test_test_url_never_falls_back_to_runtime_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_KERNEL_TEST_POSTGRES_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@localhost/agent_kernel")
    with pytest.raises(ValueError, match="AGENT_KERNEL_TEST_POSTGRES_URL"):
        testing_database.test_database_url()


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://localhost/agent_kernel",
        "postgresql://localhost/appdata",
        "postgresql://db.example/agent_kernel_test",
        "postgresql:///agent_kernel_test",
        "postgresql://localhost/agent_kernel_test?options=-csearch_path=public",
        "postgresql://localhost/agent_kernel_test?dbname=agent_kernel",
        "postgresql://localhost/agent_kernel_test?host=remote",
        "postgresql://localhost/agent_kernel_test?service=production",
    ],
)
def test_test_url_rejects_unsafe_targets_before_connecting(
    monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    monkeypatch.setenv("AGENT_KERNEL_TEST_POSTGRES_URL", url)
    monkeypatch.setattr(
        testing_database, "create_engine", lambda *a, **kw: pytest.fail("Must not connect")
    )
    with pytest.raises(ValueError), testing_database.isolated_database():
        pytest.fail("Invalid target was accepted")


def test_test_url_normalizes_explicit_postgres_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "AGENT_KERNEL_TEST_POSTGRES_URL", "postgresql://test:secret@localhost/agent_kernel_test"
    )
    assert testing_database.test_database_url().drivername == "postgresql+psycopg"


def test_isolated_schemas_do_not_share_rows_or_migration_state() -> None:
    source = testing_database.test_database_url()
    admin = create_engine(source, poolclass=NullPool)
    first_schema = second_schema = None
    try:
        with testing_database.isolated_database() as first:
            with first.begin() as connection:
                first_schema = connection.scalar(text("SELECT current_schema()"))
                connection.execute(text("CREATE TABLE isolation_sentinel (value text)"))
                connection.execute(text("INSERT INTO isolation_sentinel VALUES ('keep')"))
                version = connection.scalar(text("SELECT version_num FROM alembic_version"))
            with testing_database.isolated_database(migrated=False) as second:
                with second.connect() as connection:
                    second_schema = connection.scalar(text("SELECT current_schema()"))
                    assert first_schema != second_schema
                    assert (
                        connection.scalar(text("SELECT to_regclass('isolation_sentinel')")) is None
                    )
                    assert connection.scalar(text("SELECT to_regclass('alembic_version')")) is None
                testing_database.migrate(second)
                with second.connect() as connection:
                    assert (
                        connection.scalar(text("SELECT version_num FROM alembic_version"))
                        == version
                    )
            with first.connect() as connection:
                assert connection.scalar(text("SELECT value FROM isolation_sentinel")) == "keep"
                assert connection.scalar(text("SELECT version_num FROM alembic_version")) == version
        with admin.connect() as connection:
            for schema in (first_schema, second_schema):
                assert (
                    connection.scalar(
                        text("SELECT count(*) FROM pg_namespace WHERE nspname=:schema"),
                        {"schema": schema},
                    )
                    == 0
                )
    finally:
        admin.dispose()


def test_isolated_schema_is_removed_after_failure() -> None:
    schema = None
    with (
        pytest.raises(RuntimeError, match="synthetic fixture failure"),
        testing_database.isolated_database(migrated=False) as engine,
    ):
        with engine.connect() as connection:
            schema = connection.scalar(text("SELECT current_schema()"))
        raise RuntimeError("synthetic fixture failure")
    admin = create_engine(testing_database.test_database_url(), poolclass=NullPool)
    try:
        with admin.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM pg_namespace WHERE nspname=:schema"),
                    {"schema": schema},
                )
                == 0
            )
    finally:
        admin.dispose()
