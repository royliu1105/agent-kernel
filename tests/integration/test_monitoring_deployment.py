"""Opt-in checks for the disposable Compose monitoring stack after HTTP smoke."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_KERNEL_TEST_MONITORING") != "1",
    reason="Set AGENT_KERNEL_TEST_MONITORING=1 for the disposable monitoring deployment.",
)


def _local_url(variable: str, default: str) -> str:
    value = os.getenv(variable, default)
    parsed = urlsplit(value)
    assert parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    assert not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
    assert parsed.path in {"", "/"}
    return value.rstrip("/")


def _get(client: httpx.Client, path: str, **kwargs: Any) -> dict[str, Any]:
    response = client.get(path, **kwargs)
    assert response.is_success, f"GET {path}: HTTP {response.status_code}"
    result = response.json()
    assert isinstance(result, dict)
    return result


def _query(client: httpx.Client, expression: str) -> list[dict[str, Any]]:
    result = _get(client, "/api/v1/query", params={"query": expression})
    assert result["status"] == "success"
    values = result["data"]["result"]
    assert isinstance(values, list)
    return values


def _wait_for_positive_query(client: httpx.Client, expression: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        values = _query(client, expression)
        if values and all(float(value["value"][1]) > 0 for value in values):
            return
        time.sleep(1)
    pytest.fail(f"No positive scraped sample within 60 seconds: {expression}")


def _wait_for_grafana(client: httpx.Client) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            response = client.get("/api/health")
            if response.status_code == 200 and response.json().get("database") == "ok":
                return
        except httpx.TransportError:
            pass
        time.sleep(1)
    pytest.fail("Grafana did not become ready within 60 seconds.")


def test_prometheus_scrapes_real_application_metrics_and_loads_rules() -> None:
    url = _local_url("AGENT_KERNEL_TEST_PROMETHEUS_URL", "http://127.0.0.1:9090")
    with httpx.Client(base_url=url, timeout=10, trust_env=False) as client:
        for job in ("api", "worker"):
            _wait_for_positive_query(client, f'up{{job="agent-kernel-{job}"}}')
        _wait_for_positive_query(client, 'probe_success{job="agent-kernel-readiness"}')
        for metric, job in (
            ("llm_model_calls_total", "worker"),
            ("tool_calls_total", "worker"),
            ("tool_calls_total", "api"),
            ("rag_retrievals_total", "api"),
        ):
            _wait_for_positive_query(client, f'sum({metric}{{job="agent-kernel-{job}"}})')

        targets = _get(client, "/api/v1/targets")["data"]["activeTargets"]
        assert {target["labels"]["job"] for target in targets} == {
            "agent-kernel-api",
            "agent-kernel-worker",
            "agent-kernel-readiness",
        }
        assert all(target["health"] == "up" and not target["lastError"] for target in targets)
        loaded = _get(client, "/api/v1/rules")["data"]["groups"]
        rules = [rule for group in loaded for rule in group["rules"]]
        configured = json.loads((ROOT / "deploy/observability/alerts.json").read_text())
        assert {rule["name"] for rule in rules} == {
            rule["alert"] for group in configured["groups"] for rule in group["rules"]
        }
        deadline = time.monotonic() + 60
        while not all(rule["health"] == "ok" for rule in rules):
            assert time.monotonic() < deadline, "Prometheus rules did not evaluate successfully."
            time.sleep(1)
            groups = _get(client, "/api/v1/rules")["data"]["groups"]
            refreshed = [rule for group in groups for rule in group["rules"]]
            assert {rule["name"] for rule in refreshed} == {rule["name"] for rule in rules}
            rules = refreshed

        dashboard = json.loads(
            (ROOT / "deploy/observability/grafana/dashboards/agent-kernel.json").read_text()
        )
        for panel in dashboard["panels"]:
            for target in panel["targets"]:
                _query(client, target["expr"].replace("$__range", "1h"))


def test_grafana_provisions_dashboard_and_reaches_prometheus() -> None:
    url = _local_url("AGENT_KERNEL_TEST_GRAFANA_URL", "http://127.0.0.1:3090")
    password = os.getenv("AGENT_KERNEL_TEST_GRAFANA_PASSWORD")
    assert password, "Provide the disposable Grafana admin password through the test environment."
    with httpx.Client(base_url=url, timeout=10, trust_env=False) as anonymous:
        _wait_for_grafana(anonymous)
        assert anonymous.get("/api/search").status_code == 401
    with httpx.Client(
        base_url=url, auth=("admin", password), timeout=10, trust_env=False
    ) as client:
        health = _get(client, "/api/health")
        assert health["database"] == "ok"
        dashboard = _get(client, "/api/dashboards/uid/agent-kernel-operations")
        assert dashboard["meta"]["provisioned"] is True
        assert len(dashboard["dashboard"]["panels"]) == 14
        datasource = _get(client, "/api/datasources/uid/agent-kernel-prometheus")
        assert datasource["url"] == "http://prometheus:9090"
        assert datasource["readOnly"] is True
        assert _get(client, "/api/datasources/uid/agent-kernel-prometheus/health")["status"] == "OK"
        result = _get(
            client,
            "/api/datasources/proxy/uid/agent-kernel-prometheus/api/v1/query",
            params={"query": 'up{job=~"agent-kernel-(api|worker)"}'},
        )
        assert result["status"] == "success"
        assert {item["metric"]["job"] for item in result["data"]["result"]} == {
            "agent-kernel-api",
            "agent-kernel-worker",
        }
        assert all(float(item["value"][1]) == 1 for item in result["data"]["result"])


def test_disposable_worker_has_restart_supervision() -> None:
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{"project":{{json (index .Config.Labels "com.docker.compose.project")}},'
            '"policy":{{json .HostConfig.RestartPolicy.Name}}}',
            "agent-kernel-hardening-worker-1",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, "The disposable Compose Worker must be running."
    assert json.loads(result.stdout) == {
        "project": "agent-kernel-hardening",
        "policy": "unless-stopped",
    }
