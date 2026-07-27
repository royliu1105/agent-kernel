"""Database engine and session helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from kernel_storage.config import get_database_url


def create_engine_for_url(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine and ensure local SQLite directories exist."""

    url = database_url or get_database_url()
    if url.startswith("sqlite:///"):
        database_path = Path(url.removeprefix("sqlite:///"))
        if str(database_path) not in {":memory:", ""}:
            database_path.parent.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the application's sync session factory."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
