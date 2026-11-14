"""Local startup remains container-only, private and non-destructive."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copyfile(ROOT / "scripts/local-stack.sh", scripts / "local-stack.sh")
    return tmp_path


def invoke(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", str(root / "scripts/local-stack.sh"), *args],
        env={
            **os.environ,
            "OPENAI_API_KEY": "MUST_NOT_INHERIT",
            "DATABASE_URL": "wrong",
            "DEEPSEEK_API_KEY": "MUST_NOT_INHERIT",
            "DASHSCOPE_API_KEY": "MUST_NOT_INHERIT",
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def test_private_initialization_is_repeatable(checkout: Path) -> None:
    assert invoke(checkout, "init").returncode == 0
    state = checkout / ".agent-kernel/docker-local"
    files = {path.name: path.read_bytes() for path in state.iterdir()}
    assert len(files["monitoring-token"].strip()) == 64
    assert len(files["grafana-password"].strip()) == 64
    assert files["smtp-password"] == b""
    assert state.stat().st_mode & 0o777 == 0o700
    assert (state / "config.env").stat().st_mode & 0o777 == 0o600
    result = invoke(checkout, "init")
    assert result.returncode == 0
    assert files == {path.name: path.read_bytes() for path in state.iterdir()}
    assert files["grafana-password"].decode().strip() not in result.stdout


def test_symlink_and_destructive_down_are_rejected(checkout: Path) -> None:
    result = invoke(checkout, "down", "--volumes")
    assert result.returncode == 2
    assert "preserves data" in result.stderr
    target = checkout / "unrelated"
    target.mkdir()
    (checkout / ".agent-kernel").symlink_to(target)
    assert invoke(checkout, "init").returncode == 1
    assert not list(target.iterdir())


def test_compose_uses_fixed_project_and_clean_environment(
    checkout: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_dir = checkout / "bin"
    bin_dir.mkdir()
    record = checkout / "invocation.json"
    docker = bin_dir / "docker"
    docker.write_text(
        f"#!{sys.executable}\nimport json, os, sys\n"
        f"with open({str(record)!r}, 'w') as f:\n"
        " json.dump({'args': sys.argv[1:], 'provider': os.getenv('OPENAI_API_KEY'), "
        "'deepseek': os.getenv('DEEPSEEK_API_KEY'), 'dashscope': os.getenv('DASHSCOPE_API_KEY'), "
        "'db': os.getenv('DATABASE_URL')}, f)\n"
    )
    docker.chmod(0o700)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    result = invoke(checkout, "config")
    assert result.returncode == 0, result.stderr
    command = json.loads(record.read_text())
    assert command["provider"] is None and command["db"] is None
    assert command["deepseek"] is None and command["dashscope"] is None
    assert "agent-kernel-local" in command["args"]
    assert command["args"][-2:] == ["config", "--quiet"]
    assert str(checkout / "deploy/local.compose.yml") in command["args"]
    assert "--env-file" in command["args"]


def test_docker_default_is_documented_and_build_context_excludes_secrets() -> None:
    for name in ("README.md", "docs/quickstart.md", "docs/development-environment.md", "AGENTS.md"):
        assert "make docker-up" in (ROOT / name).read_text()
    ignored = (ROOT / ".dockerignore").read_text().splitlines()
    assert all(pattern in ignored for pattern in (".env", "**/.env.*", "resource/"))
    local = (ROOT / "deploy/local.compose.yml").read_text()
    assert "ports: !reset []" in local
    assert '"127.0.0.1:${AGENT_KERNEL_WEB_PORT:-3000}:3000"' in local
    assert '"--appendonly", "yes"' in local
    assert "driver: local" in local
    assert "AGENT_KERNEL_RUN_QUEUE_BACKEND: redis" in local
    assert local.count('DEEPSEEK_API_KEY: ""') == 2
    assert local.count('DASHSCOPE_API_KEY: ""') == 2
