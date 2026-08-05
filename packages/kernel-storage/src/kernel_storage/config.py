"""Storage configuration helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

DEFAULT_DATABASE_URL = "sqlite:///./.agent-kernel/agent_kernel.db"
DATABASE_URL_ENV = "DATABASE_URL"
DEFAULT_VECTOR_STORE_MODE = "auto"
VECTOR_STORE_MODE_ENV = "AGENT_KERNEL_VECTOR_STORE"
SUPPORTED_VECTOR_STORE_MODES = frozenset({"auto", "json", "pgvector"})


def get_database_url() -> str:
    """Return the configured database URL.

    The default is intentionally local and lightweight so new contributors can
    run the API without Docker. Production deployments should set DATABASE_URL.
    """

    return os.getenv(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)


def get_vector_store_mode(env: Mapping[str, str] | None = None) -> str:
    values = env or os.environ
    mode = values.get(VECTOR_STORE_MODE_ENV, DEFAULT_VECTOR_STORE_MODE).strip().lower()
    if mode == "":
        return DEFAULT_VECTOR_STORE_MODE
    if mode not in SUPPORTED_VECTOR_STORE_MODES:
        supported = ", ".join(sorted(SUPPORTED_VECTOR_STORE_MODES))
        raise ValueError(f"{VECTOR_STORE_MODE_ENV} must be one of: {supported}.")
    return mode


def prepare_database_url(database_url: str | None = None) -> str:
    """Return a database URL after preparing local filesystem prerequisites."""

    url = database_url or get_database_url()
    if url.startswith("sqlite:///"):
        database_path = Path(url.removeprefix("sqlite:///"))
        if str(database_path) not in {":memory:", ""}:
            database_path.parent.mkdir(parents=True, exist_ok=True)
    return url
