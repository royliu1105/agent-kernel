"""Showcase overlay config stays mock-only and approval-gated."""

from __future__ import annotations

import hashlib
from pathlib import Path

from kernel_core import RiskLevel
from kernel_tools.external.config import read_external_tools_config

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "deploy/local-showcase-tools/tools.json"
SERVER = ROOT / "deploy/local-showcase-tools/showcase_mcp_server.py"
COMPOSE = ROOT / "deploy/local-showcase.compose.yml"
DOC = ROOT / "docs/showcase/mock-happy-path.md"


def test_showcase_tools_config_requires_approval_and_absolute_stdio() -> None:
    config = read_external_tools_config(TOOLS)
    assert len(config.mcp) == 1
    assert config.openapi == ()
    server = config.mcp[0]
    assert server.stdio is not None
    assert server.http is None
    assert Path(server.stdio.command).is_absolute()
    assert server.stdio.args == (
        "/etc/agent-kernel/showcase-tools/showcase_mcp_server.py",
    )
    binding = server.bindings[0]
    assert binding.contract.name == "showcase_inventory_lookup"
    assert binding.contract.policy_decision == "require_approval"
    assert binding.contract.risk_level is RiskLevel.READ_ONLY
    assert binding.contract.read_only is True
    assert SERVER.is_file()
    assert "github" not in TOOLS.read_text().casefold()
    assert "api.github.com" not in TOOLS.read_text()


def test_showcase_overlay_is_opt_in_and_documented() -> None:
    compose = COMPOSE.read_text()
    assert "AGENT_KERNEL_EXTERNAL_TOOLS_CONFIG" in compose
    assert "local-showcase-tools" in compose
    assert "Never loaded by ordinary docker-up" in compose
    makefile = (ROOT / "Makefile").read_text()
    assert "docker-showcase-up" in makefile
    assert "showcase-happy-path" in makefile
    doc = DOC.read_text()
    assert "make docker-showcase-up" in doc
    assert "cf1_disposition_claimed" in (ROOT / "docs/showcase/evidence-template.json").read_text()
    # Stable fixture fingerprint for operators comparing evidence hashes.
    digest = hashlib.sha256(TOOLS.read_bytes()).hexdigest()
    assert len(digest) == 64
