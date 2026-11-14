"""Build and verify an isolated full observability deployment, then clean up."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    project = "agent-kernel-observability-" + secrets.token_hex(4)
    parent = ROOT / ".agent-kernel"
    parent.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="observability-drill-", dir=parent) as directory:
        private = Path(directory)
        token = secrets.token_urlsafe(36)
        password = secrets.token_urlsafe(24)
        token_file = private / "monitoring-token"
        token_file.write_text(token)
        token_file.chmod(0o644)  # Container UID reads it; host parent is 0700.
        smtp_file = private / "smtp-password"
        smtp_file.write_text("")
        smtp_file.chmod(0o644)
        override = private / "override.json"
        override.write_text(
            json.dumps(
                {
                    "services": {
                        "api": {"ports": ["127.0.0.1:28080:8000"]},
                        "worker": {"environment": {"AGENT_KERNEL_LOG_MAX_BYTES": "4096"}},
                    }
                }
            )
        )
        files = [
            ROOT / "docker-compose.yml",
            ROOT / "deploy/hardening-smoke.compose.yml",
            ROOT / "deploy/observability/docker-compose.yml",
            ROOT / "deploy/observability/full-stack.compose.yml",
            ROOT / "deploy/observability/local-mail.compose.yml",
            override,
        ]
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("AGENT_KERNEL_", "OPENAI_", "ANTHROPIC_", "OTEL_"))
            and key not in {"DATABASE_URL", "REDIS_URL"}
        }
        env.update(
            {
                "OPENAI_API_KEY": "",
                "AGENT_KERNEL_API_PORT": "28080",
                "AGENT_KERNEL_POSTGRES_PORT": "25432",
                "AGENT_KERNEL_REDIS_PORT": "26379",
                "AGENT_KERNEL_PROMETHEUS_PORT": "39090",
                "AGENT_KERNEL_GRAFANA_PORT": "33090",
                "AGENT_KERNEL_LOKI_PORT": "33100",
                "AGENT_KERNEL_TEMPO_PORT": "33200",
                "AGENT_KERNEL_OTLP_PORT": "34318",
                "AGENT_KERNEL_ALERTMANAGER_PORT": "39093",
                "AGENT_KERNEL_MAILPIT_PORT": "38025",
                "AGENT_KERNEL_MONITORING_TOKEN": token,
                "AGENT_KERNEL_MONITORING_TOKEN_FILE": str(token_file),
                "AGENT_KERNEL_GRAFANA_ADMIN_PASSWORD": password,
                "AGENT_KERNEL_ALERTMANAGER_CONFIG_FILE": str(
                    ROOT / "deploy/observability/alertmanager.local.json"
                ),
                "AGENT_KERNEL_SMTP_PASSWORD_FILE": str(smtp_file),
                "AGENT_KERNEL_RUN_QUEUE_BACKEND": "redis",
                "AGENT_KERNEL_TEST_OBSERVABILITY_FULL": "1",
                "AGENT_KERNEL_TEST_OBSERVABILITY_PROJECT": project,
                "AGENT_KERNEL_TEST_DEPLOYMENT_URL": "http://127.0.0.1:28080",
                "AGENT_KERNEL_TEST_PROMETHEUS_URL": "http://127.0.0.1:39090",
                "AGENT_KERNEL_TEST_GRAFANA_URL": "http://127.0.0.1:33090",
                "AGENT_KERNEL_TEST_GRAFANA_PASSWORD": password,
            }
        )
        compose = ["docker", "compose", "-p", project]
        for file in files:
            compose += ["-f", str(file)]
        compose += ["--profile", "observability"]
        existing = subprocess.run(
            ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"],
            capture_output=True,
            text=True,
            check=True,
        )
        if existing.stdout.strip():
            raise RuntimeError("Refusing to reuse an existing rehearsal project.")
        try:
            subprocess.run([*compose, "config", "--quiet"], env=env, cwd=ROOT, check=True)
            validators = [
                ["loki", "-config.file=/etc/loki/config.json", "-verify-config=true"],
                ["tempo", "-config.file=/etc/tempo/config.json", "-config.verify=true"],
                ["alloy", "validate", "/etc/alloy/config.alloy"],
                [
                    "--entrypoint",
                    "amtool",
                    "alertmanager",
                    "check-config",
                    "/etc/alertmanager/config.json",
                ],
                [
                    "--entrypoint",
                    "promtool",
                    "prometheus",
                    "check",
                    "config",
                    "/etc/prometheus/prometheus.json",
                ],
            ]
            for validator in validators:
                subprocess.run(
                    [*compose, "run", "--rm", "--no-deps", *validator],
                    env=env,
                    cwd=ROOT,
                    check=True,
                )
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--entrypoint",
                    "promtool",
                    "-v",
                    f"{ROOT / 'deploy/observability'}:/work:ro",
                    "-w",
                    "/work",
                    "prom/prometheus:v3.5.0",
                    "test",
                    "rules",
                    "telemetry-alert-tests.json",
                ],
                env=env,
                cwd=ROOT,
                check=True,
            )
            subprocess.run(
                [
                    *compose,
                    "up",
                    "--build",
                    "-d",
                    "--wait",
                    "--wait-timeout",
                    "240",
                    "api",
                    "worker",
                    "prometheus",
                    "blackbox",
                    "grafana",
                    "loki",
                    "tempo",
                    "alloy",
                    "alertmanager",
                    "mailpit",
                ],
                env=env,
                cwd=ROOT,
                check=True,
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-v",
                    "-x",
                    "--tb=short",
                    "tests/integration/test_self_hosted_hardening.py",
                    "tests/integration/test_observability_full_stack.py",
                ],
                env=env,
                cwd=ROOT,
                check=False,
            )
            if result.returncode:
                subprocess.run(
                    [
                        *compose,
                        "logs",
                        "--no-color",
                        "--tail",
                        "30",
                        "alloy",
                        "loki",
                        "tempo",
                        "alertmanager",
                    ],
                    env=env,
                    cwd=ROOT,
                    check=False,
                )
            return result.returncode
        except subprocess.CalledProcessError:
            subprocess.run(
                [
                    *compose,
                    "logs",
                    "--no-color",
                    "--tail",
                    "30",
                    "api",
                    "worker",
                    "alloy",
                    "loki",
                    "tempo",
                    "alertmanager",
                ],
                env=env,
                cwd=ROOT,
                check=False,
            )
            raise
        finally:
            # Only the random project created by this invocation is removed.
            subprocess.run(
                [*compose, "down", "--volumes", "--remove-orphans"], env=env, cwd=ROOT, check=True
            )


if __name__ == "__main__":
    raise SystemExit(main())
