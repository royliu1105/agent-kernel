"""Frozen-limit, actual API/Worker admission and guarded-HTTP fixture matrix."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from cf2_runtime import EVIDENCE, guard, save
from cf2_scenario import api, cli, lines, read, snapshot, wait_for
from pv2_profile import MODEL, ledger

from scripts.pv1_harness import read_events, reconcile


def create(agent_id: str, case: str, status: str = "waiting_approval") -> str:
    value = {
        "model": f"deepseek:{MODEL}",
        "fallback_models": [],
        "messages": [
            {
                "role": "system",
                "content": Path("/prompts/pv1-runbook-assistant-v1.txt").read_text(),
            },
            {"role": "user", "content": json.dumps({"case": case})},
        ],
    }
    save(f"profile-input-{case}.json", value)
    run_id = cli("run", "create", agent_id, "--input", f"@/evidence/profile-input-{case}.json")[
        "id"
    ]
    cli("run", "queue", run_id)
    wait_for(run_id, status)
    return str(run_id)


def prepare() -> None:
    agent = cli("agent", "create", "--name", "PV2 frozen-profile fixture")
    kb = cli("kb", "create", "--name", "PV2 synthetic indexing")
    path = EVIDENCE / "profile-corpus.md"
    path.write_text("# Synthetic offline acceptance\n\nThis text contains no real user data.\n")
    document = cli("document", "upload", kb["id"], str(path))
    cli("document", "ingest", document["id"])
    cli("document", "chunk", document["id"])
    indexed = cli("document", "index", document["id"])
    assert indexed["model"] == "text-embedding-v3" and indexed["dimensions"] == 1024
    cases = {}
    for case in ("approve", "reject", "concurrent", "retry_before"):
        run_id = create(agent["id"], case)
        stored = snapshot(run_id, f"profile-waiting-{case}")
        assert len(stored["calls"]) == 1
        call = stored["calls"][0]
        assert call["status"] == "waiting_approval"
        cases[case] = {"run_id": run_id, "tool_id": call["id"], "approval_id": call["approval_id"]}
    for path in (EVIDENCE / "journals").glob("*.jsonl"):
        assert not any(row.event == "dispatch_start" for row in read_events(path))
    first = cases["approve"]
    cli("approval", "approve", first["approval_id"], "--note", "synthetic fixture")
    save("profile-cases.json", {"agent_id": agent["id"], "cases": cases})
    print(
        "PV2 exact profile prepared: v3/1024 indexed; four persisted approvals; zero HTTP dispatch."
    )


def finish() -> None:
    data = read("profile-cases.json")
    assert read("profile-api.json") == read("profile-worker.json")
    for case, item in data["cases"].items():
        approval = item["approval_id"]
        action = "reject" if case == "reject" else "approve"
        body = {"reason": "synthetic rejection"} if action == "reject" else {}
        first = api("POST", f"/v1/approvals/{approval}/{action}", body=body)
        assert api("POST", f"/v1/approvals/{approval}/{action}", body=body) == first
        endpoint = f"/v1/runs/{item['run_id']}/resume"
        if case == "concurrent":
            import httpx

            def invoke(_: int, endpoint: str = endpoint, approval: str = approval) -> int:
                return httpx.post(
                    "http://127.0.0.1:8000" + endpoint,
                    headers={
                        "Authorization": "Bearer " + read("credentials.json")["operator"]["key"]
                    },
                    json={"approval_id": approval},
                    timeout=60,
                ).status_code

            with ThreadPoolExecutor(max_workers=2) as pool:
                assert sorted(pool.map(invoke, range(2))) == [200, 409]
        else:
            cli("run", "resume", item["run_id"], "--approval-id", approval)
        api("POST", endpoint, body={"approval_id": approval}, status=409)
        stored = snapshot(item["run_id"], f"profile-finished-{case}")
        assert stored["run"]["status"] == ("failed" if case == "reject" else "succeeded")
        assert stored["calls"][0]["status"] == ("denied" if case == "reject" else "succeeded")
        if case != "reject":
            requests = [row for row in lines("profile-requests.jsonl") if row["case"] == case]
            assert any(message["role"] == "tool" for message in requests[-1]["request"]["messages"])
            assert requests[-1]["request"]["messages"][0] == requests[0]["request"]["messages"][0]
    uncertain = create(data["agent_id"], "retry_after", "failed")
    snapshot(uncertain, "profile-unknown-charge")
    requests = lines("profile-requests.jsonl")
    dispatches = lines("profile-dispatches.jsonl")
    assert sum(row["case"] == "retry_after" for row in requests) == 2
    assert sum(row["case"] == "retry_after" for row in dispatches) == 1
    assert sum(row["case"] == "retry_before" for row in requests) == 3
    assert sum(row["case"] == "retry_before" for row in dispatches) == 2
    print(
        "PV2 exact profile matrix passed: restart/concurrent/repeated resume, "
        "reject and automatic retries."
    )


def verify() -> None:
    state = ledger()
    current = state.snapshot()
    cases = read("profile-cases.json")["cases"]
    expected = {UUID(item["tool_id"]): int(case != "reject") for case, item in cases.items()}
    observation = reconcile(
        EVIDENCE / "journals",
        case_id=state.case_id,
        executors=frozenset(current.executors),
        expected=expected,
    )
    assert observation.verdict == "pass"
    assert len(current.executors) == 3
    assert list(current.executors.values()).count("api") == 2
    assert list(current.executors.values()).count("worker") == 1
    assert all(
        UUID(row["executor"]) in current.executors for row in lines("profile-requests.jsonl")
    )
    assert len(current.attempts) == 9  # eight generation + one embedding, across all processes
    assert sum(not value.complete for value in current.attempts.values()) == 1
    assert sum(value.reserved for value in current.attempts.values()) == Decimal("1.10")
    # Unknown charge deliberately prevents a green budget window, even with known HTTP counts.
    assert state.observation(EVIDENCE / "journals", expected).verdict == "unknown"
    save(
        "profile-result.json",
        {
            "status": "passed",
            "evidence_class": "fixture",
            "http_counts": "pass",
            "unknown_charge_window": "unknown",
            "live_calls": False,
            "authenticated_web": False,
        },
    )
    print(
        "PV2 exact-profile safety checks passed: all three executor journals closed; "
        "HTTP counts 1/0/1/1; unknown charge blocks retry."
    )


if __name__ == "__main__":
    guard()
    {"prepare": prepare, "finish": finish, "verify": verify}[sys.argv[1]]()
