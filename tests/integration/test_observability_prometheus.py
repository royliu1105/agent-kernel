"""Native protocol/template checks; enabled with AGENT_KERNEL_TEST_PROMTOOL=1."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from agent_kernel_api.main import _operational_metrics
from kernel_observability import AggregatingMetricsRecorder
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "deploy" / "observability"
pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_KERNEL_TEST_PROMTOOL") != "1",
    reason="Opt-in native promtool verification requires Docker.",
)


def _promtool(*args: str, input_text: str | None = None, mount: Path | None = None) -> None:
    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        # Linux bind mounts preserve pytest's private directory ownership.
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "-i",
        "-v",
        f"{CONFIG}:/etc/prometheus:ro",
        "-w",
        "/etc/prometheus",
    ]
    if mount is not None:
        command += ["-v", f"{mount}:/validation:ro"]
    command += ["--entrypoint", "promtool", "prom/prometheus:v3.5.0", *args]
    result = subprocess.run(
        command, input=input_text, text=True, capture_output=True, timeout=90, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_promtool_validates_production_exposition(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    recorder = AggregatingMetricsRecorder()
    for name in ("echo", "kb_search"):
        recorder.increment("tool_calls_total", labels={"tool_name": name, "status": "succeeded"})
        recorder.observe("tool_call_latency_ms", 15, labels={"tool_name": name})
    recorder.increment("llm_estimated_cost_total", value=0.001)
    recorder.increment(
        "api_requests_total",
        labels={"method": "GET", "status_class": "2xx", "route_group": "health"},
    )
    recorder.observe("api_request_latency_ms", 5)
    recorder.increment(
        "agent_run_segments_total", labels={"execution_mode": "execute", "outcome": "succeeded"}
    )
    _promtool(
        "check",
        "metrics",
        input_text=recorder.prometheus_text() + _operational_metrics(postgres_session_factory),
    )


def test_promtool_validates_scrape_configuration_and_alert_scenarios() -> None:
    _promtool("check", "config", "--syntax-only", "/etc/prometheus/prometheus.json")
    _promtool("test", "rules", "alert-tests.json")


def test_promtool_validates_every_dashboard_expression(tmp_path: Path) -> None:
    dashboard = json.loads((CONFIG / "grafana/dashboards/agent-kernel.json").read_text())
    rules = [
        {
            "record": f"dashboard_query_{panel['id']}",
            "expr": target["expr"].replace("$__range", "1h"),
        }
        for panel in dashboard["panels"]
        for target in panel["targets"]
    ]
    (tmp_path / "dashboard-rules.json").write_text(
        json.dumps({"groups": [{"name": "dashboard-validation", "rules": rules}]})
    )
    _promtool("check", "rules", "/validation/dashboard-rules.json", mount=tmp_path)
