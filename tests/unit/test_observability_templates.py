import json
from pathlib import Path

from kernel_observability import METRIC_DEFINITIONS

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "deploy" / "observability"


def test_dashboard_provisioning_and_metric_inventory() -> None:
    dashboard = json.loads((CONFIG / "grafana/dashboards/agent-kernel.json").read_text())
    datasource = json.loads(
        (CONFIG / "grafana/provisioning/datasources/agent-kernel.yaml").read_text()
    )
    assert datasource["datasources"][0]["uid"] == "agent-kernel-prometheus"
    assert len({panel["id"] for panel in dashboard["panels"]}) == len(dashboard["panels"])
    expressions = "\n".join(
        target["expr"] for panel in dashboard["panels"] for target in panel["targets"]
    )
    assert "workspace_id" not in expressions and "run_id" not in expressions
    assert "llm_model_call_duration_seconds_bucket" in expressions
    names = {definition.export_name or definition.name for definition in METRIC_DEFINITIONS}
    for metric in (
        "llm_model_calls_total",
        "llm_model_call_duration_seconds",
        "tool_calls_total",
        "tool_call_duration_seconds",
        "rag_retrievals_total",
        "rag_retrieval_duration_seconds",
        "llm_tokens_total",
        "llm_estimated_cost_total",
        "run_queue_errors_total",
        "api_requests_total",
        "api_request_duration_seconds",
        "agent_run_segments_total",
    ):
        assert metric in names and metric in expressions
    for panel in dashboard["panels"]:
        assert panel["datasource"]["uid"] == "agent-kernel-prometheus"
    for metric in (
        "agent_kernel_queue_backlog",
        "agent_kernel_queue_oldest_wait_seconds",
        "agent_kernel_approval_oldest_wait_seconds",
        "agent_kernel_runs",
        "agent_kernel_evals",
    ):
        assert metric in expressions


def test_scraping_uses_dedicated_secret_and_alerts_have_firing_tests() -> None:
    config = json.loads((CONFIG / "prometheus.json").read_text())
    for job in config["scrape_configs"]:
        if job["job_name"] in {"agent-kernel-api", "agent-kernel-worker"}:
            assert job["authorization"] == {
                "type": "Bearer",
                "credentials_file": "/run/secrets/monitoring_token",
            }
    rules = json.loads((CONFIG / "alerts.json").read_text())["groups"][0]["rules"]
    scenarios = json.loads((CONFIG / "alert-tests.json").read_text())["tests"]
    covered = {
        test["alertname"]
        for case in scenarios
        for test in case["alert_rule_test"]
        if test["exp_alerts"]
    }
    assert {rule["alert"] for rule in rules} == covered
    assert all(rule["for"] and rule["annotations"]["summary"] for rule in rules)
