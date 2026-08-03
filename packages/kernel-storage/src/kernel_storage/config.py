"""Storage configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DATABASE_URL = "sqlite:///./.agent-kernel/agent_kernel.db"
DATABASE_URL_ENV = "DATABASE_URL"


def get_database_url() -> str:
    """Return the configured database URL.

    The default is intentionally local and lightweight so new contributors can
    run the API without Docker. Production deployments should set DATABASE_URL.
    """

    return os.getenv(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)


def prepare_database_url(database_url: str | None = None) -> str:
    """Return a database URL after preparing local filesystem prerequisites."""

    url = database_url or get_database_url()
    if url.startswith("sqlite:///"):
        database_path = Path(url.removeprefix("sqlite:///"))
        if str(database_path) not in {":memory:", ""}:
            database_path.parent.mkdir(parents=True, exist_ok=True)
    return url
