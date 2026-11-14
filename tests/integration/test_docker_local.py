"""Opt-in, non-destructive acceptance of the maintained Docker-only local stack."""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".agent-kernel/docker-local"
pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_KERNEL_TEST_DOCKER_LOCAL") != "1",
    reason="Run make docker-up, then explicitly opt into Docker-local acceptance.",
)


def wait(check: Callable[[], Any]) -> Any:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (httpx.HTTPError, AssertionError):
            pass
        time.sleep(1)
    pytest.fail("Docker local acceptance timed out.")


def get(client: httpx.Client, path: str, **kwargs: Any) -> Any:
    response = client.get(path, **kwargs)
    response.raise_for_status()
    return response.json()


def test_all_services_are_containerized_and_private() -> None:
    services = {
        "api",
        "worker",
        "web",
        "postgres",
        "redis",
        "prometheus",
        "blackbox",
        "grafana",
        "alloy",
        "loki",
        "tempo",
        "alertmanager",
        "mailpit",
    }
    names = subprocess.check_output(
        [
            "docker",
            "ps",
            "--filter",
            "label=com.docker.compose.project=agent-kernel-local",
            "--format",
            "{{.Names}}",
        ],
        text=True,
    ).splitlines()
    assert set(names) == {f"agent-kernel-local-{name}-1" for name in services}
    details = json.loads(subprocess.check_output(["docker", "inspect", *names], text=True))
    for container in details:
        assert container["State"]["Running"] is True
        assert container["HostConfig"]["LogConfig"]["Type"] == "local"
        assert container["HostConfig"]["RestartPolicy"]["Name"] == "unless-stopped"
        for bindings in container["NetworkSettings"]["Ports"].values():
            assert not bindings or all(item["HostIp"] == "127.0.0.1" for item in bindings)
        service = container["Config"]["Labels"]["com.docker.compose.service"]
        if service in {"api", "worker"}:
            env = dict(item.split("=", 1) for item in container["Config"]["Env"])
            assert env["DATABASE_URL"].startswith("postgresql+psycopg://")
            assert env["AGENT_KERNEL_RUN_QUEUE_BACKEND"] == "redis"
            assert env["OPENAI_API_KEY"] == ""
        if service in {"postgres", "redis"}:
            assert not any(container["NetworkSettings"]["Ports"].values())


def test_web_proxy_and_dependency_readiness() -> None:
    with httpx.Client(trust_env=False, timeout=5) as client:
        ready = get(client, "http://127.0.0.1:8000/readyz")
        assert ready["status"] == "ready"
        assert ready["dependencies"]["database"]["status"] == "ok"
        assert ready["dependencies"]["redis"]["status"] == "ok"
        assert ready["dependencies"]["pgvector"]["status"] == "ok"
        health = get(client, "http://127.0.0.1:3000/api/agent-kernel/health")
        assert health["state"] == "online"
        assert health["baseUrl"] == "http://api:8000"
        assert isinstance(
            get(client, "http://127.0.0.1:3000/api/agent-kernel/knowledge-bases"), list
        )


def test_real_queue_rag_logs_and_trace() -> None:
    with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False, timeout=10) as client:

        def post(path: str, **kwargs: Any) -> Any:
            response = client.post(path, **kwargs)
            response.raise_for_status()
            return response.json()

        agent = post("/v1/agents", json={"name": "Docker Local Acceptance"})
        run = post(
            f"/v1/agents/{agent['id']}/runs",
            json={
                "input": {
                    "task": "Docker local smoke",
                    "model": "mock:docker-local",
                }
            },
        )
        post(f"/v1/runs/{run['id']}/queue")
        wait(lambda: get(client, f"/v1/runs/{run['id']}")["status"] == "succeeded")
        kb = post("/v1/knowledge-bases", json={"name": "Docker Local Handbook"})
        doc = post(
            f"/v1/knowledge-bases/{kb['id']}/documents/upload",
            files={
                "file": (
                    "docker.md",
                    b"Docker keeps the local runtime reproducible. Use stop to preserve data.",
                    "text/markdown",
                ),
            },
        )
        for action in ("ingest", "chunk", "index"):
            post(f"/v1/documents/{doc['id']}/{action}")
        result = post(f"/v1/knowledge-bases/{kb['id']}/retrieve", json={"query": "Docker"})
        assert result["results"][0]["citation"]["document_id"] == doc["id"]
        proxy = get(client, f"http://127.0.0.1:3000/api/agent-kernel/runs/{run['id']}")
        assert proxy["status"] == "succeeded"
        log_query = f'{{job="agent-kernel"}} | json | run_id="{run["id"]}"'
        wait(
            lambda: get(
                client, "http://127.0.0.1:3100/loki/api/v1/query_range", params={"query": log_query}
            )["data"]["result"]
        )
        wait(
            lambda: get(
                client,
                f"http://127.0.0.1:3200/api/traces/{run['trace_id']}",
                headers={"Accept": "application/json"},
            )
        )
        record = STATE / "acceptance-sample.json"
        record.write_text(
            json.dumps(
                {
                    "agent_id": agent["id"],
                    "run_id": run["id"],
                    "trace_id": run["trace_id"],
                    "knowledge_base_id": kb["id"],
                    "document_id": doc["id"],
                },
                indent=2,
            )
            + "\n"
        )
        record.chmod(0o600)


def test_metrics_grafana_and_local_mailbox() -> None:
    with httpx.Client(trust_env=False, timeout=10) as client:

        def all_targets_up() -> bool:
            targets = get(client, "http://127.0.0.1:9090/api/v1/targets")["data"]["activeTargets"]
            return len(targets) == 7 and all(target["health"] == "up" for target in targets)

        wait(all_targets_up)
        assert isinstance(get(client, "http://127.0.0.1:8025/api/v1/messages")["messages"], list)
        assert client.get("http://127.0.0.1:9093/-/ready").status_code == 200
        assert client.get("http://127.0.0.1:3090/api/search").status_code == 401
        password = (STATE / "grafana-password").read_text().strip()
        data = get(client, "http://127.0.0.1:3090/api/datasources", auth=("admin", password))
        assert {item["uid"] for item in data} == {
            "agent-kernel-prometheus",
            "agent-kernel-loki",
            "agent-kernel-tempo",
        }
