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
    assert str(checkout / "deploy/local-paid.compose.yml") not in command["args"]

    state = checkout / ".agent-kernel/docker-local"
    paid = state / "paid.env"
    assert invoke(checkout, "paid-config").returncode == 1
    paid.write_text("DEEPSEEK_API_KEY=test-only\nDASHSCOPE_API_KEY=test-only\n")
    paid.chmod(0o644)
    result = invoke(checkout, "paid-config")
    assert result.returncode == 0, result.stderr
    assert paid.stat().st_mode & 0o777 == 0o600
    command = json.loads(record.read_text())
    assert command["args"].count("--env-file") == 2
    assert str(paid) in command["args"]
    assert str(checkout / "deploy/local-paid.compose.yml") in command["args"]
    assert command["deepseek"] is None and command["dashscope"] is None
    assert "test-only" not in result.stdout + result.stderr

    # Merely having credentials on disk must not activate paid models.
    assert invoke(checkout, "config").returncode == 0
    command = json.loads(record.read_text())
    assert str(paid) not in command["args"]
    assert str(checkout / "deploy/local-paid.compose.yml") not in command["args"]


def test_paid_configuration_symlink_is_rejected(checkout: Path) -> None:
    assert invoke(checkout, "init").returncode == 0
    target = checkout / "credentials"
    target.write_text("private")
    (checkout / ".agent-kernel/docker-local/paid.env").symlink_to(target)
    assert invoke(checkout, "paid-config").returncode == 1
    assert target.read_text() == "private"


def test_paid_override_is_bounded_and_does_not_change_storage() -> None:
    import yaml  # type: ignore[import-untyped]

    config = yaml.safe_load((ROOT / "deploy/local-paid.compose.yml").read_text())
    assert set(config["services"]) == {"api", "worker"}
    api, worker = (config["services"][name] for name in ("api", "worker"))
    assert api == worker
    assert set(api) == {"environment", "volumes"}
    assert api["volumes"] == ["./deploy/local-paid-tools:/etc/agent-kernel/paid-tools:ro"]
    env = api["environment"]
    assert env["DEEPSEEK_API_KEY"].startswith("${DEEPSEEK_API_KEY:?")
    assert env["DASHSCOPE_API_KEY"].startswith("${DASHSCOPE_API_KEY:?")
    assert env["AGENT_KERNEL_MAX_MODEL_CALLS"] == "2"
    assert env["AGENT_KERNEL_MAX_OUTPUT_TOKENS"] == "2048"
    assert env["AGENT_KERNEL_EMBEDDING_PROVIDER"] == "dashscope"
    assert env["DASHSCOPE_EMBEDDING_DIMENSIONS"] == "1024"


def test_docker_default_is_documented_and_build_context_excludes_secrets() -> None:
    for name in ("README.md", "docs/quickstart.md", "docs/development-environment.md", "AGENTS.md"):
        assert "make docker-up" in (ROOT / name).read_text()
    ignored = (ROOT / ".dockerignore").read_text().splitlines()
    assert all(pattern in ignored for pattern in (".env", "**/.env.*"))
    local = (ROOT / "deploy/local.compose.yml").read_text()
    assert "ports: !reset []" in local
    assert '"127.0.0.1:${AGENT_KERNEL_WEB_PORT:-3000}:3000"' in local
    assert '"--appendonly", "yes"' in local
    assert "driver: local" in local
    assert "AGENT_KERNEL_RUN_QUEUE_BACKEND: redis" in local
    assert local.count('DEEPSEEK_API_KEY: ""') == 2
    assert local.count('DASHSCOPE_API_KEY: ""') == 2


def test_repository_does_not_ship_a_resource_reference_tree() -> None:
    assert not (ROOT / "resource").exists()
    gitignore = (ROOT / ".gitignore").read_text()
    dockerignore = (ROOT / ".dockerignore").read_text()
    assert "resource/" not in gitignore
    assert "resource/**" not in gitignore
    assert "resource/README.md" not in gitignore
    assert "resource/" not in dockerignore.splitlines()
    contributing = (ROOT / "CONTRIBUTING.md").read_text()
    agents = (ROOT / "AGENTS.md").read_text()
    for text in (contributing, agents):
        assert "Do not add a `resource/` directory" in text
        assert "reference-project-comparison.md" in text
    comparison = (ROOT / "docs/reference-project-comparison.md").read_text()
    assert "ship, track, or host a reference project tree" in comparison
