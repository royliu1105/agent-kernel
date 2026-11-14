from __future__ import annotations

from pathlib import Path

import pytest
from kernel_storage import create_engine_for_url
from kernel_storage.config import get_database_url, get_vector_store_mode, prepare_database_url


def test_sqlite_is_rejected_without_creating_files(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "agent_kernel.db"
    url = f"sqlite:///{database_path}"

    with pytest.raises(ValueError, match="PostgreSQL"):
        create_engine_for_url(url)
    assert not database_path.parent.exists()


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///:memory:",
        "mysql://host/db",
        "not-a-url",
        "postgresql+asyncpg://host/db",
        "postgresql://host/",
    ],
)
def test_rejects_unsupported_database_urls(url: str) -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        prepare_database_url(url)


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        get_database_url()
    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        create_engine_for_url(" ")


def test_normalizes_postgresql_driver() -> None:
    assert prepare_database_url("postgresql://user:secret@host/db") == (
        "postgresql+psycopg://user:secret@host/db"
    )


def test_invalid_url_error_does_not_expose_password() -> None:
    with pytest.raises(ValueError) as caught:
        prepare_database_url("postgresql://user:private-password@host:bad/db")
    assert "private-password" not in str(caught.value)


def test_get_vector_store_mode_defaults_to_auto() -> None:
    assert get_vector_store_mode({}) == "auto"
    assert get_vector_store_mode({"AGENT_KERNEL_VECTOR_STORE": ""}) == "auto"


def test_get_vector_store_mode_accepts_supported_values() -> None:
    assert get_vector_store_mode({"AGENT_KERNEL_VECTOR_STORE": "json"}) == "json"
    assert get_vector_store_mode({"AGENT_KERNEL_VECTOR_STORE": "pgvector"}) == "pgvector"
    assert get_vector_store_mode({"AGENT_KERNEL_VECTOR_STORE": " AUTO "}) == "auto"


def test_get_vector_store_mode_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="AGENT_KERNEL_VECTOR_STORE"):
        get_vector_store_mode({"AGENT_KERNEL_VECTOR_STORE": "annoy"})
