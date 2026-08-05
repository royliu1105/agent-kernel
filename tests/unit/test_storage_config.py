from __future__ import annotations

from pathlib import Path

import pytest
from kernel_storage.config import get_vector_store_mode, prepare_database_url


def test_prepare_database_url_creates_sqlite_parent(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "agent_kernel.db"
    url = f"sqlite:///{database_path}"

    prepared_url = prepare_database_url(url)

    assert prepared_url == url
    assert database_path.parent.exists()


def test_prepare_database_url_leaves_memory_sqlite_alone() -> None:
    url = "sqlite:///:memory:"

    assert prepare_database_url(url) == url


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
