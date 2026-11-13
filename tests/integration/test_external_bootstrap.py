"""Exercise the production API/worker bootstrap with an actual MCP subprocess."""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from agent_kernel_api.main import create_app
from agent_kernel_worker.main import _run_worker
from fastapi.testclient import TestClient
from kernel_core import RiskLevel
from kernel_tools.external import (
    ExternalAccess,
    ExternalToolContract,
    ExternalToolsConfig,
    MCPBinding,
    MCPServerConfig,
    StdioEndpoint,
)
from sqlalchemy.orm import Session, sessionmaker


def test_external_tool_queued_worker_approval_and_api_resume(
    sqlite_session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "external_mcp_server.py"
    configuration = ExternalToolsConfig(
        mcp=(
            MCPServerConfig(
                name="fixture",
                stdio=StdioEndpoint(command=sys.executable, args=(str(fixture),)),
                access=ExternalAccess(allow_unscoped=True),
                bindings=(
                    MCPBinding(
                        remote_name="record",
                        contract=ExternalToolContract(
                            name="external_record",
                            read_only=True,
                            risk_level=RiskLevel.READ_ONLY,
                            policy_decision="require_approval",
                        ),
                    ),
                ),
            ),
        )
    )
    path = tmp_path / "external-tools.json"
    path.write_text(configuration.model_dump_json())
    monkeypatch.setenv("AGENT_KERNEL_EXTERNAL_TOOLS_CONFIG", str(path))
    monkeypatch.setenv("AGENT_KERNEL_RATE_LIMIT_REQUESTS", "0")
    monkeypatch.setenv("AGENT_KERNEL_WORKER_METRICS_ENABLED", "false")
    monkeypatch.setenv("AGENT_KERNEL_RUN_QUEUE_BACKEND", "database")

    with TestClient(
        create_app(session_factory=sqlite_session_factory, api_key_auth_enabled=False)
    ) as client:
        agent_response = client.post("/v1/agents", json={"name": "external-agent"})
        assert agent_response.status_code == 201
        agent_id = agent_response.json()["id"]
        run_response = client.post(
            f"/v1/agents/{agent_id}/runs",
            json={
                "input": {
                    "tool": {
                        "name": "external_record",
                        "arguments": {"message": "approved content"},
                    },
                }
            },
        )
        assert run_response.status_code == 201
        run_id = run_response.json()["id"]
        assert client.post(f"/v1/runs/{run_id}/queue").status_code == 200
        asyncio.run(
            _run_worker(
                session_factory=sqlite_session_factory,
                once=True,
                limit=1,
                poll_interval=0.01,
            )
        )
        waiting = client.get(f"/v1/runs/{run_id}")
        assert waiting.json()["status"] == "waiting_approval"
        approvals = client.get("/v1/approvals").json()
        assert len(approvals) == 1
        approval_id = approvals[0]["id"]
        assert client.post(f"/v1/approvals/{approval_id}/approve", json={}).status_code == 200
        resumed = client.post(f"/v1/runs/{run_id}/resume", json={"approval_id": approval_id})
        assert resumed.status_code == 200, resumed.text
        assert resumed.json()["status"] == "succeeded"
        result = resumed.json()["output"]["tool"]["result"]
        assert result["untrusted"] is True
        assert result["data"]["structuredContent"]["message"] == "approved content"
        assert result["data"]["structuredContent"]["calls"] == 1
        assert "external_record" in json.dumps(client.get(f"/v1/runs/{run_id}/events").json())
