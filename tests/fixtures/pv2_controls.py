"""Operator stop/revoke evidence, inside the owned remote-CI fixture only."""

from __future__ import annotations

import os
import sys
import time
from uuid import UUID

from cf2_runtime import guard, save
from cf2_scenario import api, cli, lines, read, snapshot, wait_for
from kernel_storage import ApiKeyRepository, create_engine_for_url
from sqlalchemy.orm import Session


def queue() -> None:
    case = read("case.json")
    run = cli("run", "create", case["agent_id"], "--input", "@/evidence/input-approved.json")
    queued = cli("run", "queue", run["id"])
    assert queued["status"] == "queued"
    before = len(lines("provider.jsonl"))
    time.sleep(2)
    assert api("GET", f"/v1/runs/{run['id']}")["status"] == "queued"
    assert len(lines("provider.jsonl")) == before
    snapshot(run["id"], "pv2-queued-before-stop")
    save("pv2-queued.json", {"run_id": run["id"], "provider_requests": before})


def verify() -> None:
    pending = read("pv2-queued.json")
    run_id = pending["run_id"]
    assert read("pv2-stopped.json") == {"api": "stopped", "worker": "stopped"}
    wait_for(run_id, "waiting_approval")
    after = snapshot(run_id, "pv2-recovered")
    assert after["run"]["id"] == run_id
    assert len(lines("provider.jsonl")) == pending["provider_requests"] + 2
    assert len(lines("effects.jsonl")) == 1
    executors = lines("executors.jsonl")
    assert len({item["executor_id"] for item in executors}) == len(executors)
    assert sum(item["role"] == "api" for item in executors) >= 3
    assert sum(item["role"] == "worker" for item in executors) >= 2
    known = {item["executor_id"] for item in executors}
    assert all(item["executor_id"] in known for item in lines("provider.jsonl"))
    assert {item["prompt_sha256"] for item in lines("provider.jsonl")} == {
        "bf6c5329a3e3bfa8587947b53a904fe4c3193444ad1f24a947305f163b1b091b"
    }
    engine = create_engine_for_url()
    try:
        with Session(engine) as session:
            keys = ApiKeyRepository(session)
            credential = keys.authenticate(read("credentials.json")["operator"]["key"])
            assert credential is not None
            assert keys.revoke(credential.id)
    finally:
        engine.dispose()
    api("POST", "/v1/agents", body={"name": "must-not-exist"}, status=401)
    api("POST", f"/v1/runs/{run_id}/resume", body={}, status=401)
    api("GET", f"/v1/runs/{run_id}", status=401)
    # A different authorized identity in the same workspace still sees preserved evidence.
    assert api("GET", f"/v1/runs/{run_id}", role="viewer")["status"] == "waiting_approval"
    assert UUID(run_id)
    save(
        "pv2-controls.json",
        {
            "status": "passed",
            "scope": "synthetic authenticated API/CLI container controls",
            "stopped_api_and_worker": True,
            "queued_record_preserved": True,
            "revoked_key_denied": True,
            "replacement_executors_observed": True,
            "frozen_prompt_initial_and_resumed": True,
            "in_flight_effect": (
                "All stops occurred at quiescent boundaries; not forced-kill exactly-once proof"
            ),
            "live_provider": False,
            "authenticated_web": False,
        },
    )
    print("PV2 container controls passed: stop/recover/revoke and frozen prompt; no live calls.")


if __name__ == "__main__":
    guard()
    assert os.environ.get("PV2_REHEARSAL") == "1"
    {"queue": queue, "verify": verify}[sys.argv[1]]()
