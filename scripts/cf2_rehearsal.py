"""Run the scoped CF2 API/CLI rehearsal without changing the active Docker project."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_PATTERN = r"agent-kernel-cf2-[0-9a-f]{16}"


def clean_environment(environ: dict[str, str]) -> dict[str, str]:
    # Docker connection settings are needed on Desktop; application/Compose/proxy settings aren't.
    allowed = {
        "PATH",
        "HOME",
        "TMPDIR",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_CONFIG",
        "DOCKER_TLS_VERIFY",
        "DOCKER_CERT_PATH",
        "LANG",
        "LC_ALL",
    }
    return {key: value for key, value in environ.items() if key in allowed}


def compose_config(project: str, private: Path, password: str) -> dict[str, Any]:
    if not re.fullmatch(PROJECT_PATTERN, project):
        raise ValueError("Refusing a non-disposable CF2 project name")
    settings = {
        "CF2_PROJECT": project,
        "DATABASE_URL": f"postgresql+psycopg://cf2:{password}@postgres/cf2",
        "REDIS_URL": "redis://redis:6379/0",
        "AGENT_KERNEL_RUN_QUEUE_BACKEND": "redis",
        "AGENT_KERNEL_API_KEY_AUTH_ENABLED": "true",
        "AGENT_KERNEL_EMBEDDING_PROVIDER": "mock",
        "AGENT_KERNEL_OBJECT_STORE_BACKEND": "local",
        "AGENT_KERNEL_OBJECT_STORE_ROOT": "/objects",
        "AGENT_KERNEL_EXTERNAL_TOOLS_CONFIG": "/evidence/tools.json",
        "AGENT_KERNEL_API_HOST": "0.0.0.0",
        "AGENT_KERNEL_API_PORT": "8000",
        "AGENT_KERNEL_MAX_MODEL_CALLS": "8",
        "AGENT_KERNEL_MAX_TOOL_CALLS": "16",
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "OTEL_SDK_DISABLED": "true",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "ALL_PROXY": "",
        "http_proxy": "",
        "https_proxy": "",
        "all_proxy": "",
        "NO_PROXY": "*",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    application = {
        "image": project + ":candidate",
        "build": {"context": str(ROOT), "dockerfile": "deploy/Dockerfile.python"},
        "volumes": [
            f"{ROOT / 'tests/fixtures'}:/fixture:ro",
            f"{private}:/evidence",
            "objects:/objects",
        ],
        "restart": "no",
        "logging": {"driver": "local", "options": {"max-size": "5m", "max-file": "3"}},
    }
    health = {"interval": "1s", "timeout": "3s", "retries": 90}
    return {
        "services": {
            "postgres": {
                "image": "pgvector/pgvector:pg16",
                "environment": {
                    "POSTGRES_USER": "cf2",
                    "POSTGRES_DB": "cf2",
                    "POSTGRES_PASSWORD": password,
                },
                "volumes": ["postgres:/var/lib/postgresql/data"],
                "healthcheck": {**health, "test": ["CMD-SHELL", "pg_isready -U cf2 -d cf2"]},
            },
            "redis": {
                "image": "redis:7-alpine",
                "volumes": ["redis:/data"],
                "healthcheck": {**health, "test": ["CMD", "redis-cli", "ping"]},
            },
            "bootstrap": {
                **application,
                "environment": {**settings, "CF2_ROLE": "bootstrap"},
                "command": ["python", "/fixture/cf2_runtime.py", "bootstrap"],
            },
            "api": {
                **application,
                "environment": {**settings, "CF2_ROLE": "api"},
                "command": ["python", "/fixture/cf2_runtime.py", "api"],
                "healthcheck": {
                    **health,
                    "test": [
                        "CMD",
                        "python",
                        "-c",
                        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz')",
                    ],
                },
            },
            "worker": {
                **application,
                "environment": {**settings, "CF2_ROLE": "worker"},
                "command": [
                    "python",
                    "/fixture/cf2_runtime.py",
                    "worker",
                    "--loop",
                    "--poll-interval",
                    "0.5",
                ],
                "depends_on": {"api": {"condition": "service_healthy"}},
            },
        },
        "networks": {"default": {"internal": True}},
        "volumes": {"postgres": {}, "redis": {}, "objects": {}},
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    path.chmod(0o600)


def seal_evidence(private: Path, source: dict[str, Any], secret_values: list[str]) -> None:
    unchanged = all(
        hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == checksum
        for name, checksum in source["files"].items()
    )
    if not unchanged:
        raise RuntimeError(
            "Source changed during CF2 rehearsal; evidence is not a frozen candidate"
        )
    files = {}
    for path in sorted(private.iterdir()):
        if not path.is_file() or path.name in {"credentials.json", "compose.json", "manifest.json"}:
            continue
        content = path.read_bytes()
        if any(secret.encode() in content for secret in secret_values):
            for secret in secret_values:
                content = content.replace(secret.encode(), b"<redacted>")
            path.write_bytes(content)
            raise RuntimeError("Credential appeared in CF2 evidence; redacted, acceptance refused")
        files[path.name] = hashlib.sha256(content).hexdigest()
    configuration = json.loads((private / "configuration.json").read_text())
    canonical_config = json.dumps(
        configuration, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    write_json(
        private / "manifest.json",
        {
            "revision": "cf2-api-cli-offline-v1",
            "source_unchanged_during_run": True,
            "configuration_sha256": hashlib.sha256(canonical_config).hexdigest(),
            "file_bytes_sha256": files,
            "credential_scan": "passed",
            "request_digest": "UTF-8 JSON, sorted keys, compact, finite, preserved array order",
            "scope": "Synthetic Docker API/CLI rehearsal, not authenticated Web or live quality",
        },
    )


def run(args: list[str], env: dict[str, str], *, timeout: int = 300) -> str:
    result = subprocess.run(
        args, env=env, cwd=ROOT, text=True, capture_output=True, timeout=timeout
    )
    if result.returncode:
        # Do not echo rendered Compose configuration or private subprocess output.
        raise subprocess.CalledProcessError(
            result.returncode, args, output=result.stdout, stderr=result.stderr
        )
    return result.stdout


def active_identity(env: dict[str, str]) -> list[dict[str, Any]]:
    ids = run(
        ["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=agent-kernel-local"],
        env,
    ).split()
    if not ids:
        return []
    values = json.loads(run(["docker", "inspect", *ids], env))
    return sorted(
        [
            {
                "id": value["Id"],
                "name": value["Name"],
                "image": value["Image"],
                "started_at": value["State"]["StartedAt"],
                "status": value["State"]["Status"],
            }
            for value in values
        ],
        key=lambda value: value["name"],
    )


def main() -> int:
    os.umask(0o077)
    env = clean_environment(dict(os.environ))
    project = "agent-kernel-cf2-" + secrets.token_hex(8)
    private = ROOT / ".agent-kernel" / project
    private.mkdir(parents=True, mode=0o700)
    write_json(private / "guard.json", {"project": project})
    password = secrets.token_urlsafe(32)
    config = compose_config(project, private, password)
    compose_file = private / "compose.json"
    write_json(compose_file, config)
    compose = [
        "docker",
        "compose",
        "--env-file",
        "/dev/null",
        "-f",
        str(compose_file),
        "-p",
        project,
    ]
    # Refuse collisions before build/up or cleanup. Never attach external/named existing volumes.
    for command in (
        ["docker", "ps", "-aq"],
        ["docker", "volume", "ls", "-q"],
        ["docker", "network", "ls", "-q"],
    ):
        if run([*command, "--filter", f"label=com.docker.compose.project={project}"], env).strip():
            raise RuntimeError("Refusing to reuse existing CF2 resources")
    before = active_identity(env)
    write_json(private / "active-before.json", before)
    tracked = run(["git", "ls-files", "-z"], env).split("\0")
    paths = [
        path
        for path in tracked
        if path
        and (
            path.startswith(("apps/", "packages/", "evals/", "examples/"))
            or path
            in {
                "pyproject.toml",
                "uv.lock",
                "alembic.ini",
                "README.md",
                "deploy/Dockerfile.python",
                ".dockerignore",
            }
        )
    ]
    paths += [
        "scripts/cf2_rehearsal.py",
        "tests/fixtures/cf2_runtime.py",
        "tests/fixtures/cf2_scenario.py",
    ]
    source = {
        "git_head": run(["git", "rev-parse", "HEAD"], env).strip(),
        "working_tree": "uncommitted harness/documentation candidate; hashes identify exact files",
        "files": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in sorted(set(paths))
        },
    }
    write_json(private / "source.json", source)
    redacted = json.loads(json.dumps(config).replace(password, "<redacted>"))
    write_json(private / "configuration.json", redacted)
    succeeded = False
    try:
        run([*compose, "config", "--quiet"], env)
        print("CF2: building isolated candidate; no active-stack operations", flush=True)
        run([*compose, "build", "api"], env, timeout=900)
        image_id = run(
            ["docker", "image", "inspect", project + ":candidate", "--format", "{{.Id}}"], env
        ).strip()
        write_json(private / "image.json", {"id": image_id})
        run([*compose, "up", "-d", "--wait", "postgres", "redis"], env)
        run([*compose, "run", "--rm", "--no-deps", "bootstrap"], env)
        run([*compose, "up", "-d", "--wait", "--wait-timeout", "120", "api", "worker"], env)
        network_ids = run(
            [
                "docker",
                "network",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ],
            env,
        ).split()
        networks = json.loads(run(["docker", "network", "inspect", *network_ids], env))
        if len(networks) != 1 or not networks[0]["Internal"]:
            raise RuntimeError("CF2 requires an isolated internal Docker network")
        containers = run([*compose, "ps", "-q"], env).split()
        inspected = json.loads(run(["docker", "inspect", *containers], env))
        write_json(
            private / "runtime.json",
            [
                {
                    "service": item["Config"]["Labels"]["com.docker.compose.service"],
                    "id": item["Id"],
                    "image": item["Image"],
                    "networks": sorted(item["NetworkSettings"]["Networks"]),
                }
                for item in inspected
            ],
        )
        for stage in ("prepare", "finish"):
            print(f"CF2: {stage} authenticated CLI/API scenario", flush=True)
            output = run(
                [*compose, "exec", "-T", "api", "python", "/fixture/cf2_scenario.py", stage], env
            )
            print(output.strip(), flush=True)
            if stage == "prepare":
                run([*compose, "restart", "api"], env)
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    identity = run([*compose, "ps", "-q", "api"], env).strip()
                    state = run(
                        ["docker", "inspect", identity, "--format", "{{.State.Health.Status}}"], env
                    ).strip()
                    if state == "healthy":
                        break
                    time.sleep(1)
                else:
                    raise TimeoutError("Isolated API did not become healthy after restart")
        succeeded = True
    except subprocess.CalledProcessError as error:
        detail = str(error.stderr or "") + "\n" + str(error.output or "")
        secret_values = [password]
        credentials = private / "credentials.json"
        if credentials.exists():
            secret_values += [item["key"] for item in json.loads(credentials.read_text()).values()]
        for secret in secret_values:
            detail = detail.replace(secret, "<redacted>")
        (private / "failure.log").write_text(detail)
        raise RuntimeError("CF2 command failed; see restricted failure.log") from None
    finally:
        # Logs and raw evidence remain private. No secrets/headers are captured by instrumentation.
        try:
            logs = run(
                [*compose, "logs", "--no-color", "--tail", "150", "api", "worker", "bootstrap"], env
            )
            (private / "containers.log").write_text(logs)
        finally:
            run([*compose, "down", "--volumes", "--remove-orphans"], env)
            after = active_identity(env)
            write_json(private / "active-after.json", after)
            unchanged = before == after
            remaining = {}
            for kind, command in (
                ("containers", ["docker", "ps", "-aq"]),
                ("volumes", ["docker", "volume", "ls", "-q"]),
                ("networks", ["docker", "network", "ls", "-q"]),
            ):
                remaining[kind] = run(
                    [*command, "--filter", f"label=com.docker.compose.project={project}"], env
                ).split()
            write_json(
                private / "cleanup.json", {"active_unchanged": unchanged, "remaining": remaining}
            )
            credentials = private / "credentials.json"
            secret_values = [password]
            if credentials.exists():
                secret_values += [
                    item["key"] for item in json.loads(credentials.read_text()).values()
                ]
            (private / "credentials.json").unlink(missing_ok=True)
            compose_file.unlink(missing_ok=True)
            print(f"CF2 private evidence: {private}", flush=True)
            if not unchanged or any(remaining.values()):
                raise RuntimeError("CF2 active identity or cleanup verification failed")
            if succeeded:
                seal_evidence(private, source, secret_values)
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
