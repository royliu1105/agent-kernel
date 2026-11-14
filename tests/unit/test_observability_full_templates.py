import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "deploy/observability"


def test_full_monitoring_preserves_base_scrape_contract() -> None:
    base = json.loads((CONFIG / "prometheus.json").read_text())
    full = json.loads((CONFIG / "prometheus-full.json").read_text())
    assert full["scrape_configs"][:3] == base["scrape_configs"]
    assert full["alerting"]["alertmanagers"][0]["static_configs"][0]["targets"] == [
        "alertmanager:9093"
    ]
    assert "/etc/prometheus/telemetry-alerts.json" in full["rule_files"]


def test_smtp_production_and_local_contracts_are_separate() -> None:
    production = json.loads((CONFIG / "alertmanager.smtp.example.json").read_text())
    local = json.loads((CONFIG / "alertmanager.local.json").read_text())
    assert production["global"]["smtp_require_tls"] is True
    assert production["global"]["smtp_auth_password_file"] == "/run/secrets/smtp_password"
    assert "smtp_auth_password" not in production["global"]
    assert local["global"]["smtp_smarthost"] == "mailpit:1025"
    assert local["global"]["smtp_require_tls"] is False
    for config in (production, local):
        assert config["route"]["group_by"] == ["alertname", "job"]
        receiver = config["receivers"][0]["email_configs"][0]
        assert receiver["send_resolved"] is True
        assert receiver["to"].endswith(".invalid")
    compose = (CONFIG / "local-mail.compose.yml").read_text()
    assert "MP_SMTP_RELAY" not in compose
    assert "1025:1025" not in compose


def test_collector_has_no_control_socket_and_bounded_export() -> None:
    compose = (CONFIG / "full-stack.compose.yml").read_text()
    collector = (CONFIG / "config.alloy").read_text()
    assert "docker.sock" not in compose
    assert "telemetry_logs:/var/log/agent-kernel:ro" in compose
    assert ":latest" not in compose
    assert "queue_size = 256" in collector
    assert 'max_elapsed_time = "5m"' in collector
    assert "drop_malformed = true" in collector
    assert "stage.labels" not in collector  # IDs stay in JSON, not indexed labels.


def test_log_trace_retention_and_crosslinks() -> None:
    loki = json.loads((CONFIG / "loki.json").read_text())
    tempo = json.loads((CONFIG / "tempo.json").read_text())
    assert loki["limits_config"]["retention_period"] == "72h"
    assert loki["compactor"]["retention_enabled"] is True
    assert tempo["overrides"]["defaults"]["compaction"]["block_retention"] == "72h"
    datasources = json.loads((CONFIG / "grafana/full-datasources.yaml").read_text())["datasources"]
    assert {source["uid"] for source in datasources} == {"agent-kernel-loki", "agent-kernel-tempo"}
    assert all(not source["editable"] for source in datasources)
    assert datasources[0]["jsonData"]["derivedFields"][0]["url"] == "$${__value.raw}"


def test_completion_ledger_does_not_accept_external_email() -> None:
    plan = (ROOT / "docs/observability-completion-plan.md").read_text()
    assert "External" in plan and "SMTP" in plan
    assert "Blocked: SMTP settings and inbox confirmation absent" in plan
    assert "- [ ] Real SMTP configured" in plan
    assert "No commit, push, paid model call" in plan
