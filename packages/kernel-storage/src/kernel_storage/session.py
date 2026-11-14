"""Database engine and session helpers."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from kernel_storage.config import prepare_database_url


def create_engine_for_url(database_url: str | None = None) -> Engine:
    """Create a PostgreSQL engine from explicit configuration."""

    url = prepare_database_url(database_url)
    return create_engine(url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the application's sync session factory."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
