"""The optional collector sink must preserve redaction and bounded storage."""

import json
import logging
import logging.config
import os
import subprocess
import sys
from pathlib import Path

import pytest
from kernel_observability.logging import create_file_log_handler, uvicorn_log_config


def test_private_file_sink_rotates_and_redacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "api.jsonl"
    monkeypatch.setenv("AGENT_KERNEL_LOG_FILE", str(path))
    monkeypatch.setenv("AGENT_KERNEL_LOG_MAX_BYTES", "1024")
    monkeypatch.setenv("AGENT_KERNEL_LOG_BACKUP_COUNT", "2")
    handler = create_file_log_handler()
    try:
        for _ in range(100):
            record = logging.LogRecord("sdk", logging.WARNING, "", 0, "PRIVATE_SENTINEL", (), None)
            handler.emit(record)
    finally:
        handler.close()
    files = list(tmp_path.glob("api.jsonl*"))
    assert len(files) == 3
    for file in files:
        assert file.stat().st_size <= 1024
        assert file.stat().st_mode & 0o777 == 0o600
        text = file.read_text()
        assert "PRIVATE_SENTINEL" not in text
        assert all(json.loads(line)["event"] == "log.unstructured" for line in text.splitlines())


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("AGENT_KERNEL_LOG_MAX_BYTES", "0"),
        ("AGENT_KERNEL_LOG_MAX_BYTES", "bad"),
        ("AGENT_KERNEL_LOG_BACKUP_COUNT", "0"),
        ("AGENT_KERNEL_LOG_BACKUP_COUNT", "21"),
    ],
)
def test_rotation_cannot_be_unbounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    monkeypatch.setenv("AGENT_KERNEL_LOG_FILE", str(tmp_path / "api.jsonl"))
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="Log rotation limits"):
        create_file_log_handler()


def test_file_sink_requires_absolute_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_KERNEL_LOG_FILE", "relative.jsonl")
    with pytest.raises(ValueError, match="absolute path"):
        create_file_log_handler()


def test_file_sink_rejects_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "unrelated.txt"
    target.write_text("unchanged")
    link = tmp_path / "api.jsonl"
    link.symlink_to(target)
    monkeypatch.setenv("AGENT_KERNEL_LOG_FILE", str(link))
    with pytest.raises(OSError):
        create_file_log_handler()
    assert target.read_text() == "unchanged"


def test_default_uvicorn_has_no_file_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_KERNEL_LOG_FILE", raising=False)
    assert uvicorn_log_config()["root"]["handlers"] == ["safe"]


def test_entrypoint_reconfiguration_writes_once(tmp_path: Path) -> None:
    path = tmp_path / "api.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import logging, logging.config
from kernel_observability.logging import configure_safe_logging, uvicorn_log_config
configure_safe_logging()
configure_safe_logging()
logging.warning('FIRST_PRIVATE_SENTINEL')
logging.config.dictConfig(uvicorn_log_config())
configure_safe_logging()
logging.getLogger('uvicorn.error').warning('SECOND_PRIVATE_SENTINEL')
""",
        ],
        env={**os.environ, "AGENT_KERNEL_LOG_FILE": str(path)},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = path.read_text().splitlines()
    assert len(lines) == 2
    assert "PRIVATE_SENTINEL" not in path.read_text() + result.stderr
