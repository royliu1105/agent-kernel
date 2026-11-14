"""Isolated PostgreSQL schemas for tests and local regression scripts."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from kernel_storage.config import prepare_database_url
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]


def test_database_url() -> URL:
    raw = os.environ.get("AGENT_KERNEL_TEST_POSTGRES_URL", "")
    if not raw:
        raise ValueError("Set AGENT_KERNEL_TEST_POSTGRES_URL to a disposable PostgreSQL test DB.")
    url = make_url(prepare_database_url(raw))
    if url.host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Test database must use an explicit loopback host.")
    if not url.database or not (
        url.database.endswith("_test") or url.database.startswith("agent_kernel_test_")
    ):
        raise ValueError("Test database name must end in _test or start with agent_kernel_test_.")
    overrides = {"options", "service", "host", "hostaddr", "port", "dbname", "user", "password"}
    if overrides.intersection(url.query):
        raise ValueError("Test database URL must not override connection routing or search_path.")
    return url


def migration_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option(
        "script_location", str(ROOT / "packages/kernel-storage/src/kernel_storage/migrations")
    )
    return config


def migrate(engine: Engine, revision: str = "head", *, downgrade: bool = False) -> None:
    config = migration_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        config.attributes["version_table_schema"] = connection.scalar(
            text("SELECT current_schema()")
        )
        if downgrade:
            command.downgrade(config, revision)
        else:
            command.upgrade(config, revision)


@contextmanager
def isolated_database(*, migrated: bool = True) -> Iterator[Engine]:
    """Never use DATABASE_URL; create/drop only this call's random schema."""
    source = test_database_url()
    schema = f"test_kernel_{uuid4().hex}"
    admin = create_engine(source, poolclass=NullPool, connect_args={"connect_timeout": 5})
    engine = create_engine(
        source.update_query_dict({"options": f"-csearch_path={schema},public"}),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    created = False
    try:
        with admin.begin() as connection:
            if connection.scalar(text("SELECT current_database()")) != source.database:
                raise ValueError("Unexpected test database; refusing schema creation.")
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        created = True
        if migrated:
            migrate(engine)
        yield engine
    finally:
        engine.dispose()
        try:
            if created:
                with admin.begin() as connection:
                    connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        finally:
            admin.dispose()
