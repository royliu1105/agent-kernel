"""Real Loki/Tempo/SMTP contracts. Run only through the disposable rehearsal."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from functools import partial
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_KERNEL_TEST_OBSERVABILITY_FULL") != "1",
    reason="Use scripts/observability_rehearsal.py for the isolated full stack.",
)
CANARY = "OBS_PRIVATE_CONTENT_SENTINEL"


def _wait(check: Callable[[], Any], *, timeout: int = 90) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (httpx.TransportError, AssertionError):
            pass
        time.sleep(1)
    pytest.fail("Timed out waiting for observable backend evidence.")


def _json(client: httpx.Client, path: str, **kwargs: Any) -> Any:
    response = client.get(path, **kwargs)
    assert response.is_success, f"GET {path}: HTTP {response.status_code}"
    return response.json()


def _wait_http(client: httpx.Client, path: str) -> None:
    _wait(lambda: client.get(path).status_code == 200)


def _container(service: str) -> str:
    project = os.environ["AGENT_KERNEL_TEST_OBSERVABILITY_PROJECT"]
    assert re.fullmatch(r"agent-kernel-observability-[a-f0-9]{8}", project)
    assert service in {"alloy", "loki", "tempo", "worker", "mailpit", "alertmanager"}
    name = f"{project}-{service}-1"
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{index .Config.Labels "com.docker.compose.project"}}',
            name,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert result.stdout.strip() == project
    return name


def _control(action: str, *services: str) -> None:
    assert action in {"stop", "start", "restart"}
    for service in services:
        name = _container(service)
        subprocess.run(["docker", action, name], check=True, capture_output=True, timeout=90)


@pytest.fixture(scope="module")
def clients() -> Iterator[dict[str, httpx.Client]]:
    password = os.environ["AGENT_KERNEL_TEST_GRAFANA_PASSWORD"]
    ports = {
        "api": 28080,
        "grafana": 33090,
        "prometheus": 39090,
        "loki": 33100,
        "tempo": 33200,
        "mailpit": 38025,
        "alertmanager": 39093,
    }
    result = {
        name: httpx.Client(
            base_url=f"http://127.0.0.1:{port}",
            timeout=10,
            trust_env=False,
            auth=("admin", password) if name == "grafana" else None,
        )
        for name, port in ports.items()
    }
    try:
        for name, path in (
            ("api", "/readyz"),
            ("grafana", "/api/health"),
            ("prometheus", "/-/ready"),
            ("loki", "/ready"),
            ("tempo", "/ready"),
            ("mailpit", "/api/v1/messages"),
        ):
            _wait_http(result[name], path)
        yield result
    finally:
        for client in result.values():
            client.close()


def _run(client: httpx.Client, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/v1/agents", json={"name": "observability-rehearsal"})
    assert response.status_code == 201
    agent_id = response.json()["id"]
    response = client.post(f"/v1/agents/{agent_id}/runs", json={"input": payload})
    assert response.status_code == 201
    run_id = response.json()["id"]
    assert client.post(f"/v1/runs/{run_id}/queue").is_success

    def finished() -> dict[str, Any] | None:
        run: dict[str, Any] = _json(client, f"/v1/runs/{run_id}")
        return run if run["status"] in {"succeeded", "failed"} else None

    run = _wait(finished, timeout=40)
    assert isinstance(run, dict) and run["status"] == "succeeded"
    return run


@pytest.fixture(scope="module")
def model_run(clients: dict[str, httpx.Client]) -> dict[str, Any]:
    return _run(clients["api"], {"task": CANARY, "model": "mock:observability"})


def _logs(client: httpx.Client, run_id: str | None = None) -> list[dict[str, Any]]:
    query = '{job="agent-kernel"}'
    if run_id:
        # Avoid extra query-time fields when checking stored log metadata.
        query += f' |= `"run_id":"{run_id}"`'
    data = _json(client, "/loki/api/v1/query_range", params={"query": query, "limit": 1000})
    assert data["status"] == "success"
    records = []
    for stream in data["data"]["result"]:
        assert set(stream["stream"]) <= {"job", "service_name", "detected_level"}
        for _, line in stream["values"]:
            assert CANARY not in line
            records.append(json.loads(line))
    return records


def _event_logs(client: httpx.Client, run_id: str, event: str) -> list[dict[str, Any]]:
    records = _logs(client, run_id)
    return records if any(record.get("event") == event for record in records) else []


def _spans(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        if "spanId" in value and "name" in value:
            return [value]
        return [span for item in value.values() for span in _spans(item)]
    if isinstance(value, list):
        return [span for item in value for span in _spans(item)]
    return []


def test_runtime_logs_are_stored_searchable_and_private(
    clients: dict[str, httpx.Client], model_run: dict[str, Any]
) -> None:
    records = _wait(
        lambda: _event_logs(clients["loki"], model_run["id"], "llm.model_call.completed")
    )
    assert any(record.get("trace_id") == model_run["trace_id"] for record in records)
    assert any(record.get("event") == "llm.model_call.completed" for record in records)
    # Loki's detected_level is structured metadata, not an indexed stream label.
    series = _json(
        clients["loki"], "/loki/api/v1/series", params={"match[]": '{job="agent-kernel"}'}
    )
    assert series["data"]
    assert all(set(labels) == {"job", "service_name"} for labels in series["data"])
    for field in ("id", "trace_id"):
        label = "run_id" if field == "id" else field
        parsed = _json(
            clients["loki"],
            "/loki/api/v1/query_range",
            params={
                "query": f'{{job="agent-kernel"}} | json | {label}="{model_run[field]}"',
            },
        )
        assert parsed["data"]["result"]
    result = _json(
        clients["grafana"],
        "/api/datasources/proxy/uid/agent-kernel-loki/loki/api/v1/query_range",
        params={"query": '{job="agent-kernel"}', "limit": 20},
    )
    assert result["data"]["result"]
    datasource = _json(clients["grafana"], "/api/datasources/uid/agent-kernel-loki")
    assert datasource["jsonData"]["derivedFields"][0]["datasourceUid"] == "agent-kernel-tempo"
    assert datasource["jsonData"]["derivedFields"][0]["url"] == "${__value.raw}"


def test_actual_trace_is_exported_stored_and_correlated(
    clients: dict[str, httpx.Client], model_run: dict[str, Any]
) -> None:
    path = "/api/traces/" + model_run["trace_id"]
    data = _wait(lambda: _json(clients["tempo"], path, headers={"Accept": "application/json"}))
    assert CANARY not in json.dumps(data)
    spans = _spans(data)
    root = next(span for span in spans if span["name"] == "agent.run")
    child = next(span for span in spans if span["name"] == "llm.model_call")
    assert child["parentSpanId"] == root["spanId"]
    grafana_data = _json(
        clients["grafana"],
        "/api/datasources/proxy/uid/agent-kernel-tempo" + path,
        headers={"Accept": "application/json"},
    )
    assert len(_spans(grafana_data)) == len(spans)


def test_api_approval_resume_exports_tool_span(clients: dict[str, httpx.Client]) -> None:
    client = clients["api"]
    agent = client.post("/v1/agents", json={"name": "trace-approved-lookup"})
    assert agent.status_code == 201
    created = client.post(
        f"/v1/agents/{agent.json()['id']}/runs",
        json={"input": {"tool": {"name": "inventory_lookup", "arguments": {"item_id": "fixture"}}}},
    )
    assert created.status_code == 201
    run = created.json()
    assert client.post(f"/v1/runs/{run['id']}/queue").is_success
    _wait(lambda: _json(client, f"/v1/runs/{run['id']}")["status"] == "waiting_approval")
    approval = next(item for item in _json(client, "/v1/approvals") if item["run_id"] == run["id"])
    assert client.post(f"/v1/approvals/{approval['id']}/approve", json={}).is_success
    response = client.post(f"/v1/runs/{run['id']}/resume", json={"approval_id": approval["id"]})
    assert response.is_success and response.json()["status"] == "succeeded"

    def tool_spans() -> list[dict[str, Any]] | None:
        data = _json(
            clients["tempo"],
            "/api/traces/" + run["trace_id"],
            headers={"Accept": "application/json"},
        )
        spans = _spans(data)
        return spans if any(span["name"] == "tool.call" for span in spans) else None

    spans = _wait(tool_spans)
    roots = {span["spanId"] for span in spans if span["name"] == "agent.run"}
    assert all(span["parentSpanId"] in roots for span in spans if span["name"] == "tool.call")
    records = _wait(lambda: _event_logs(clients["loki"], run["id"], "tool.call.completed"))
    assert any(record.get("event") == "tool.call.completed" for record in records)


def test_file_rotation_preserves_collection(clients: dict[str, httpx.Client]) -> None:
    # Generate real runtime events, never write into another process's active log.
    for _ in range(12):
        run = _run(clients["api"], {"task": CANARY, "model": "mock:rotation"})
        _wait(partial(_event_logs, clients["loki"], run["id"], "llm.model_call.completed"))
    result = subprocess.run(
        [
            "docker",
            "exec",
            _container("worker"),
            "/app/.venv/bin/python",
            "-c",
            "from pathlib import Path; import json; "
            "print(json.dumps({p.name: p.stat().st_size for p in "
            "Path('/var/log/agent-kernel').glob('worker.jsonl*')}))",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    files = json.loads(result.stdout)
    assert "worker.jsonl.1" in files and len(files) <= 6
    assert all(size <= 4096 for size in files.values())
    after = _run(clients["api"], {"task": CANARY, "model": "mock:after-rotation"})
    _wait(lambda: _event_logs(clients["loki"], after["id"], "llm.model_call.completed"))


def test_collector_failure_does_not_break_runtime_and_restart_preserves_data(
    clients: dict[str, httpx.Client], model_run: dict[str, Any]
) -> None:
    _control("stop", "alloy")
    try:
        fresh = _run(clients["api"], {"task": CANARY, "model": "mock:collector-outage"})
    finally:
        _control("start", "alloy")
    _wait(lambda: _logs(clients["loki"], fresh["id"]))
    _control("restart", "loki", "tempo", "alloy")
    _wait(lambda: _logs(clients["loki"], model_run["id"]))
    _wait(
        lambda: _json(
            clients["tempo"],
            "/api/traces/" + model_run["trace_id"],
            headers={"Accept": "application/json"},
        )
    )
    later = _run(clients["api"], {"task": "after collector restart", "model": "mock:restart"})
    _wait(lambda: _logs(clients["loki"], later["id"]))


def _email(
    client: httpx.Client, status: str, alert_name: str = "AgentKernelTargetDown"
) -> list[dict[str, Any]]:
    messages = _json(client, "/api/v1/messages")["messages"]
    return [
        message
        for message in messages
        if f"[Agent Kernel {status}] {alert_name}" == message["Subject"]
    ]


def test_alertmanager_groups_and_deduplicates_local_notifications(
    clients: dict[str, httpx.Client],
) -> None:
    name = "AgentKernelGroupingDrill"
    alerts = [
        {
            "labels": {"alertname": name, "job": "grouping-drill", "instance": instance},
            "annotations": {"summary": "Local grouping contract"},
            "startsAt": datetime.now(UTC).isoformat(),
        }
        for instance in ("fixture-alpha", "fixture-beta")
    ]
    assert clients["alertmanager"].post("/api/v2/alerts", json=alerts).is_success
    firing = _wait(lambda: _email(clients["mailpit"], "FIRING", name))
    assert len(firing) == 1
    message = _json(clients["mailpit"], "/api/v1/message/" + firing[0]["ID"])
    assert all(instance in message["Text"] for instance in ("fixture-alpha", "fixture-beta"))
    assert clients["alertmanager"].post("/api/v2/alerts", json=alerts).is_success
    time.sleep(15)
    assert len(_email(clients["mailpit"], "FIRING", name)) == 1
    resolved = [{**alert, "endsAt": datetime.now(UTC).isoformat()} for alert in alerts]
    assert clients["alertmanager"].post("/api/v2/alerts", json=resolved).is_success
    _wait(lambda: _email(clients["mailpit"], "RESOLVED", name))


def test_worker_fault_smtp_retry_firing_and_resolved_mail(clients: dict[str, httpx.Client]) -> None:
    def worker_alert_state() -> str | None:
        alerts = _json(clients["prometheus"], "/api/v1/alerts")["data"]["alerts"]
        return next(
            (
                alert["state"]
                for alert in alerts
                if alert["labels"].get("alertname") == "AgentKernelTargetDown"
                and alert["labels"].get("instance") == "worker:9001"
            ),
            None,
        )

    def failures() -> float:
        result = _json(
            clients["prometheus"],
            "/api/v1/query",
            params={
                "query": 'sum(alertmanager_notifications_failed_total{integration="email"})',
            },
        )["data"]["result"]
        return float(result[0]["value"][1]) if result else 0.0

    assert worker_alert_state() is None
    baseline = failures()
    # No external receiver can be selected by this rehearsal profile.
    _control("stop", "mailpit", "worker")
    try:
        _wait(lambda: worker_alert_state() == "pending", timeout=60)
        _wait(lambda: worker_alert_state() == "firing", timeout=180)
        _wait(lambda: failures() > baseline, timeout=120)
        _control("start", "mailpit")
        firing = _wait(lambda: _email(clients["mailpit"], "FIRING"), timeout=120)
        assert len(firing) == 1
        message = _json(clients["mailpit"], "/api/v1/message/" + firing[0]["ID"])
        assert "worker:9001" in message["Text"]
        assert "operator@local.invalid" in json.dumps(message["To"])
        assert CANARY not in json.dumps(message)
        time.sleep(15)  # Beyond group_interval, still before repeat_interval.
        assert len(_email(clients["mailpit"], "FIRING")) == 1
    finally:
        _control("start", "mailpit", "worker")
    resolved = _wait(lambda: _email(clients["mailpit"], "RESOLVED"), timeout=120)
    assert len(resolved) == 1
    message = _json(clients["mailpit"], "/api/v1/message/" + resolved[0]["ID"])
    assert "worker:9001" in message["Text"]
    _wait(lambda: worker_alert_state() is None)
