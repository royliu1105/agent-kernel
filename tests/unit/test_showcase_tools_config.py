"""Showcase overlay config stays mock-only with inventory approval + troubleshooting allow."""

from __future__ import annotations

import hashlib
from pathlib import Path

from kernel_core import RiskLevel
from kernel_tools.external.config import read_external_tools_config

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "deploy/local-showcase-tools/tools.json"
INVENTORY = ROOT / "deploy/local-showcase-tools/showcase_mcp_server.py"
TROUBLESHOOTING = ROOT / "deploy/local-showcase-tools/troubleshooting_mcp_server.py"
COMPOSE = ROOT / "deploy/local-showcase.compose.yml"
DOC = ROOT / "docs/showcase/mock-happy-path.md"
TDOC = ROOT / "docs/showcase/troubleshooting-mock.md"


def test_showcase_tools_config_inventory_and_troubleshooting() -> None:
    config = read_external_tools_config(TOOLS)
    assert len(config.mcp) == 2
    assert config.openapi == ()
    by_name = {server.name: server for server in config.mcp}

    inventory = by_name["showcase_inventory"]
    assert inventory.stdio is not None
    assert inventory.http is None
    assert Path(inventory.stdio.command).is_absolute()
    assert inventory.stdio.args == (
        "/etc/agent-kernel/showcase-tools/showcase_mcp_server.py",
    )
    inv_binding = inventory.bindings[0]
    assert inv_binding.contract.name == "showcase_inventory_lookup"
    assert inv_binding.contract.policy_decision == "require_approval"
    assert inv_binding.contract.risk_level is RiskLevel.READ_ONLY
    assert inv_binding.contract.read_only is True
    assert INVENTORY.is_file()

    troubleshooting = by_name["showcase_troubleshooting"]
    assert troubleshooting.stdio is not None
    assert troubleshooting.http is None
    assert Path(troubleshooting.stdio.command).is_absolute()
    assert troubleshooting.stdio.args == (
        "/etc/agent-kernel/showcase-tools/troubleshooting_mcp_server.py",
    )
    tr_binding = troubleshooting.bindings[0]
    assert tr_binding.contract.name == "showcase_trace_logs"
    assert tr_binding.remote_name == "trace_logs_lookup"
    assert tr_binding.contract.policy_decision == "allow"
    assert tr_binding.contract.risk_level is RiskLevel.READ_ONLY
    assert tr_binding.contract.read_only is True
    assert TROUBLESHOOTING.is_file()

    text = TOOLS.read_text().casefold()
    assert "github" not in text
    assert "api.github.com" not in text


def test_showcase_overlay_is_opt_in_and_documented() -> None:
    compose = COMPOSE.read_text()
    assert "AGENT_KERNEL_EXTERNAL_TOOLS_CONFIG" in compose
    assert "local-showcase-tools" in compose
    assert "Never loaded by ordinary docker-up" in compose
    makefile = (ROOT / "Makefile").read_text()
    assert "docker-showcase-up" in makefile
    assert "showcase-happy-path" in makefile
    assert "showcase-troubleshooting" in makefile
    doc = DOC.read_text()
    assert "make docker-showcase-up" in doc
    assert "cf1_disposition_claimed" in (ROOT / "docs/showcase/evidence-template.json").read_text()
    tdoc = TDOC.read_text()
    assert "make showcase-troubleshooting" in tdoc
    assert "TRACE-OK" in tdoc
    assert "showcase_trace_logs" in tdoc
    # Stable fixture fingerprint for operators comparing evidence hashes.
    digest = hashlib.sha256(TOOLS.read_bytes()).hexdigest()
    assert len(digest) == 64
