"""Storage configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

DATABASE_URL_ENV = "DATABASE_URL"
DEFAULT_VECTOR_STORE_MODE = "auto"
VECTOR_STORE_MODE_ENV = "AGENT_KERNEL_VECTOR_STORE"
SUPPORTED_VECTOR_STORE_MODES = frozenset({"auto", "json", "pgvector"})


def get_database_url() -> str:
    """Require an explicit PostgreSQL URL; never create an implicit local database."""
    return prepare_database_url(os.getenv(DATABASE_URL_ENV, ""))


def get_vector_store_mode(env: Mapping[str, str] | None = None) -> str:
    values = os.environ if env is None else env
    mode = values.get(VECTOR_STORE_MODE_ENV, DEFAULT_VECTOR_STORE_MODE).strip().lower()
    if mode == "":
        return DEFAULT_VECTOR_STORE_MODE
    if mode not in SUPPORTED_VECTOR_STORE_MODES:
        supported = ", ".join(sorted(SUPPORTED_VECTOR_STORE_MODES))
        raise ValueError(f"{VECTOR_STORE_MODE_ENV} must be one of: {supported}.")
    return mode


def prepare_database_url(database_url: str | None = None) -> str:
    """Validate PostgreSQL configuration without connecting or exposing credentials."""
    raw = os.getenv(DATABASE_URL_ENV, "") if database_url is None else database_url
    if not raw.strip():
        raise ValueError("DATABASE_URL is required. Start the local stack with make docker-up.")
    try:
        url = make_url(raw.strip())
    except (ArgumentError, ValueError):
        raise ValueError("DATABASE_URL must be a valid PostgreSQL connection URL.") from None
    if url.drivername not in {"postgresql", "postgresql+psycopg"} or not url.database:
        raise ValueError("DATABASE_URL must use PostgreSQL with psycopg and name a database.")
    return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)
