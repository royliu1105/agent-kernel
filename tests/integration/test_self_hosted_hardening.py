"""Opt-in HTTP rehearsal against a disposable Compose deployment, never production."""

import os
import time
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest


def test_self_hosted_upload_rag_worker_and_mcp_approval() -> None:
    base_url = os.getenv("AGENT_KERNEL_TEST_DEPLOYMENT_URL", "")
    if not base_url:
        pytest.skip("Set AGENT_KERNEL_TEST_DEPLOYMENT_URL for the disposable Compose rehearsal.")
    parsed = urlsplit(base_url)
    assert parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    assert not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
    with httpx.Client(base_url=base_url, timeout=10, trust_env=False) as client:

        def request(method: str, path: str, **kwargs: Any) -> Any:
            response = client.request(method, path, **kwargs)
            assert response.is_success, f"{method} {path}: HTTP {response.status_code}"
            return response.json()

        assert request("GET", "/readyz")["status"] in {"ready", "degraded"}
        kb = request("POST", "/v1/knowledge-bases", json={"name": "disposable-smoke-kb"})
        document = request(
            "POST",
            f"/v1/knowledge-bases/{kb['id']}/documents/upload",
            files={
                "file": ("leases.md", b"Worker leases protect durable execution.", "text/markdown")
            },
        )
        for action in ("ingest", "chunk", "index"):
            request("POST", f"/v1/documents/{document['id']}/{action}")
        retrieval = request(
            "POST", f"/v1/knowledge-bases/{kb['id']}/retrieve", json={"query": "Worker leases"}
        )
        assert retrieval["results"][0]["citation"]["document_id"] == document["id"]
        agent = request("POST", "/v1/agents", json={"name": "disposable-smoke-agent"})

        def queue(payload: dict[str, Any]) -> str:
            run = request("POST", f"/v1/agents/{agent['id']}/runs", json={"input": payload})
            request("POST", f"/v1/runs/{run['id']}/queue")
            return str(run["id"])

        def wait(run_id: str, expected: str) -> dict[str, Any]:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                run = request("GET", f"/v1/runs/{run_id}")
                assert isinstance(run, dict)
                if run["status"] == expected:
                    return run
                assert run["status"] not in {"failed", "canceled"}, run.get("error_type")
                time.sleep(0.2)
            pytest.fail(f"Run did not reach {expected} within 30 seconds")

        model_id = queue({"task": "local model smoke", "model": "mock:smoke"})
        assert wait(model_id, "succeeded")["output"]["text"]
        rag_id = queue(
            {
                "tool": {
                    "name": "kb_search",
                    "arguments": {
                        "knowledge_base_id": kb["id"],
                        "query": "Worker leases",
                    },
                }
            }
        )
        assert wait(rag_id, "succeeded")["output"]["tool"]["result"]["results"]
        external_id = queue(
            {"tool": {"name": "inventory_lookup", "arguments": {"item_id": "fixture"}}}
        )
        wait(external_id, "waiting_approval")
        approval = next(a for a in request("GET", "/v1/approvals") if a["run_id"] == external_id)
        request("POST", f"/v1/approvals/{approval['id']}/approve", json={})
        result = request(
            "POST", f"/v1/runs/{external_id}/resume", json={"approval_id": approval["id"]}
        )
        assert result["status"] == "succeeded"
        events = request("GET", f"/v1/runs/{external_id}/events")
        types = [event["type"] for event in events]
        assert types.index("approval_approved") < types.index("tool_call_completed")
        assert types.count("run_completed") == 1
