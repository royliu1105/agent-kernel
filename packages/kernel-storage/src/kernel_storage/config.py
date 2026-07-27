"""Storage configuration helpers."""

from __future__ import annotations

import os

DEFAULT_DATABASE_URL = "sqlite:///./.agent-kernel/agent_kernel.db"
DATABASE_URL_ENV = "DATABASE_URL"


def get_database_url() -> str:
    """Return the configured database URL.

    The default is intentionally local and lightweight so new contributors can
    run the API without Docker. Production deployments should set DATABASE_URL.
    """

    return os.getenv(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)
