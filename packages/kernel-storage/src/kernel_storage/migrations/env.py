"""Alembic environment for Agent Kernel storage."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from kernel_storage import models as storage_models
from kernel_storage.base import Base
from kernel_storage.config import get_database_url, prepare_database_url
from sqlalchemy import Connection, engine_from_config, pool

_ = storage_models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without opening a database connection."""

    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live database connection."""

    supplied = config.attributes.get("connection")
    if supplied is not None:
        _run_on_connection(supplied)
        return

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = prepare_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            _run_on_connection(connection)
    finally:
        connectable.dispose()


def _run_on_connection(connection: Connection) -> None:
    if connection.dialect.name != "postgresql":
        raise ValueError("Migrations require PostgreSQL.")
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=config.attributes.get("version_table_schema"),
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
