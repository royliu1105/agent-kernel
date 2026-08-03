from __future__ import annotations

from pathlib import Path

from kernel_storage.config import prepare_database_url


def test_prepare_database_url_creates_sqlite_parent(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "agent_kernel.db"
    url = f"sqlite:///{database_path}"

    prepared_url = prepare_database_url(url)

    assert prepared_url == url
    assert database_path.parent.exists()


def test_prepare_database_url_leaves_memory_sqlite_alone() -> None:
    url = "sqlite:///:memory:"

    assert prepare_database_url(url) == url
