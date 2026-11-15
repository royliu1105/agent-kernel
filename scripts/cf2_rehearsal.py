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
    for path in sorted(private.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("Symlink in private evidence; refusing out-of-tree evidence")
        if not path.is_file() or path.name in {"credentials.json", "compose.json", "manifest.json"}:
            continue
        content = path.read_bytes()
        if any(secret.encode() in content for secret in secret_values):
            for secret in secret_values:
                content = content.replace(secret.encode(), b"<redacted>")
            path.write_bytes(content)
            raise RuntimeError("Credential appeared in CF2 evidence; redacted, acceptance refused")
        files[str(path.relative_to(private))] = hashlib.sha256(content).hexdigest()
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


def claim_evidence(private: Path, compose: list[str], env: dict[str, str]) -> None:
    """Linux bind mounts retain container ownership; preserve 0600/0700 modes."""
    credentials = private / "credentials.json"
    if credentials.exists() and not os.access(credentials, os.R_OK):
        run(
            [
                *compose,
                "run",
                "--rm",
                "--no-deps",
                "--user",
                "0",
                "api",
                "python",
                "-c",
                "import os,sys; sys.path.insert(0, '/fixture'); "
                "from cf2_runtime import guard,EVIDENCE; guard(); "
                "paths=[EVIDENCE,*EVIDENCE.rglob('*')]; "
                "[(os.chown(p,int(sys.argv[1]),int(sys.argv[2]),follow_symlinks=False)) "
                "for p in paths if not p.is_symlink()]",
                str(os.getuid()),
                str(os.getgid()),
            ],
            env,
        )


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


def add_web_service(config: dict[str, Any], project: str) -> None:
    """Expose only the disposable browser entrypoint on the CI runner loopback."""
    if not re.fullmatch(PROJECT_PATTERN, project):
        raise ValueError("Refusing a non-disposable Web project name")
    config["services"]["web"] = {
        "image": project + ":web",
        "build": {"context": str(ROOT), "dockerfile": "apps/web/Dockerfile"},
        "environment": {
            "AGENT_KERNEL_API_URL": "http://api:8000",
            "NEXT_TELEMETRY_DISABLED": "1",
        },
        "ports": ["127.0.0.1:3101:3000"],
        "restart": "no",
        "healthcheck": {
            "test": [
                "CMD",
                "node",
                "-e",
                "fetch('http://127.0.0.1:3000/api/agent-kernel/health')"
                ".then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))",
            ],
            "interval": "2s",
            "timeout": "5s",
            "retries": 60,
        },
    }
    for name in ("api", "worker", "bootstrap"):
        config["services"][name]["environment"].update(
            {"DEEPSEEK_API_KEY": "", "DASHSCOPE_API_KEY": "", "PV2_REHEARSAL": "1"}
        )
        config["services"][name]["volumes"].append(
            f"{ROOT / 'docs/pilots/prompts'}:/prompts:ro"
        )


def main(*, pv2: bool = False, profile: bool = False, web: bool = False) -> int:
    pv2 = pv2 or profile
    if web and pv2:
        raise ValueError("Web and frozen-profile rehearsals are separate evidence scopes")
    if (pv2 or web) and os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("PV2 container acceptance is remote-CI-only")
    os.umask(0o077)
    env = clean_environment(dict(os.environ))
    project = "agent-kernel-cf2-" + secrets.token_hex(8)
    private = ROOT / ".agent-kernel" / project
    private.mkdir(parents=True, mode=0o700)
    write_json(private / "guard.json", {"project": project})
    password = secrets.token_urlsafe(32)
    config = compose_config(project, private, password)
    if web:
        add_web_service(config, project)
    if pv2:
        for name in ("api", "worker", "bootstrap"):
            service = config["services"][name]
            service["environment"]["PV2_REHEARSAL"] = "1"
            service["environment"]["DEEPSEEK_API_KEY"] = ""
            service["environment"]["DASHSCOPE_API_KEY"] = ""
            service["volumes"] = [
                *service["volumes"],
                f"{ROOT / 'docs/pilots/prompts'}:/prompts:ro",
            ]
            if profile:
                service["volumes"].append(f"{ROOT / 'scripts'}:/app/scripts:ro")
                service["environment"].update(
                    {
                        "PV2_PROFILE": "1",
                        "PYTHONPATH": "/app:/fixture",
                        "AGENT_KERNEL_EMBEDDING_PROVIDER": "dashscope",
                        "AGENT_KERNEL_MAX_MODEL_CALLS": "2",
                        "AGENT_KERNEL_MAX_TOOL_CALLS": "8",
                        "AGENT_KERNEL_MAX_ACTIVE_SECONDS": "120",
                        "AGENT_KERNEL_MAX_TOTAL_TOKENS": "32000",
                        "AGENT_KERNEL_MAX_OUTPUT_TOKENS": "2048",
                        "AGENT_KERNEL_MAX_HISTORY_BYTES": "262144",
                    }
                )
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
                "package.json",
                "package-lock.json",
                ".github/workflows/ci.yml",
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
    if pv2:
        paths += [
            "tests/fixtures/pv2_controls.py",
            "docs/pilots/prompts/pv1-runbook-assistant-v1.txt",
        ]
    if profile:
        paths += [
            "tests/fixtures/pv2_profile.py",
            "tests/fixtures/pv2_profile_scenario.py",
            "scripts/pv1_harness.py",
            "scripts/pv2_offline_harness.py",
        ]
    if web:
        paths += [
            "tests/fixtures/pv2_web_observer.py",
            "docs/pilots/prompts/pv1-runbook-assistant-v1.txt",
        ]
    source = {
        "git_head": run(["git", "rev-parse", "HEAD"], env).strip(),
        "working_tree": "file hashes identify exact source; git_head records checkout",
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
        run([*compose, "build", "api", *(["web"] if web else [])], env, timeout=1200)
        image_id = run(
            ["docker", "image", "inspect", project + ":candidate", "--format", "{{.Id}}"], env
        ).strip()
        write_json(private / "image.json", {"id": image_id})
        run([*compose, "up", "-d", "--wait", "postgres", "redis"], env)
        run([*compose, "run", "--rm", "--no-deps", "bootstrap"], env)
        run([*compose, "up", "-d", "--wait", "--wait-timeout", "120", "api", "worker"], env)
        if web:
            run([*compose, "up", "-d", "--wait", "--wait-timeout", "120", "web"], env)
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
        if web:
            claim_evidence(private, compose, env)
            browser_env = {
                **env,
                "CI": "1",
                "GITHUB_ACTIONS": "true",
                "CF2_WEB_PROJECT": project,
                "CF2_WEB_EVIDENCE": str(private),
                "PLAYWRIGHT_BASE_URL": "http://127.0.0.1:3101",
            }
            print("PV2 Web: actual authenticated browser first-use journey", flush=True)
            print(
                run(
                    [
                        "npm",
                        "--workspace",
                        "apps/web",
                        "exec",
                        "--",
                        "playwright",
                        "test",
                        "--config",
                        "playwright.pv2.config.ts",
                    ],
                    browser_env,
                    timeout=600,
                ).strip(),
                flush=True,
            )
        for stage in () if web else ("prepare", "finish"):
            print(f"CF2: {stage} authenticated CLI/API scenario", flush=True)
            scenario = "pv2_profile_scenario.py" if profile else "cf2_scenario.py"
            output = run(
                [*compose, "exec", "-T", "api", "python", f"/fixture/{scenario}", stage], env
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
        if profile:
            run([*compose, "stop", "api", "worker"], env)
            print(
                run(
                    [
                        *compose,
                        "run",
                        "--rm",
                        "--no-deps",
                        "api",
                        "python",
                        "/fixture/pv2_profile_scenario.py",
                        "verify",
                    ],
                    env,
                ).strip(),
                flush=True,
            )
        elif pv2:
            print("PV2: stopping isolated Worker; preserving queued records", flush=True)
            run([*compose, "stop", "worker"], env)
            run([*compose, "exec", "-T", "api", "python", "/fixture/pv2_controls.py", "queue"], env)
            run([*compose, "stop", "api"], env)
            for service in ("api", "worker"):
                identity = run([*compose, "ps", "-aq", service], env).strip()
                if (
                    run(
                        ["docker", "inspect", identity, "--format", "{{.State.Running}}"], env
                    ).strip()
                    != "false"
                ):
                    raise RuntimeError("PV2 operator stop failed")
            write_json(private / "pv2-stopped.json", {"api": "stopped", "worker": "stopped"})
            run([*compose, "up", "-d", "--wait", "--wait-timeout", "120", "api", "worker"], env)
            print(
                run(
                    [*compose, "exec", "-T", "api", "python", "/fixture/pv2_controls.py", "verify"],
                    env,
                ).strip(),
                flush=True,
            )
        succeeded = True
    except subprocess.CalledProcessError as error:
        claim_evidence(private, compose, env)
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
            claim_evidence(private, compose, env)
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
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--pv2", action="store_true")
    parser.add_argument("--pv2-profile", action="store_true")
    parser.add_argument("--web", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(pv2=args.pv2, profile=args.pv2_profile, web=args.web))
