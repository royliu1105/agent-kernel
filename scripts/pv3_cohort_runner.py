#!/usr/bin/env python3
"""PV3 frozen cohort runner: 30 questions x 2 separate Runs (paid DeepSeek).

Writes private evidence under .agent-kernel/pv3-evidence/. Does not score answers.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "docs/pilots/pv1-materials/questions.json"
DEFAULT_PROMPT = ROOT / "docs/pilots/prompts/pv1-runbook-assistant-v3.txt"
DEFAULT_EVIDENCE = ROOT / ".agent-kernel/pv3-evidence"


def call(api: str, method: str, path: str, body: object | None = None, timeout: float = 180.0):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        api + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> {exc.code}: {detail[:1000]}") from exc


def wait_terminal(api: str, run_id: str, timeout_s: float = 360.0) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        _, run = call(api, "GET", f"/v1/runs/{run_id}")
        assert run is not None
        if run["status"] in {"succeeded", "failed", "canceled", "waiting_approval"}:
            return run
        time.sleep(1.5)
    raise TimeoutError(f"run {run_id} not terminal within {timeout_s}s")


def one_attempt(
    api: str,
    agent_id: str,
    kb_id: str,
    prompt: str,
    case: dict,
    attempt: int,
    evidence: Path,
) -> dict:
    # X cohort is cross-workspace denial: do not hand a searchable KB id that
    # encourages dumping the current corpus as a "helpful" substitute.
    task: dict = {
        "question": case["question"],
        "case_id": case["id"],
        "attempt": attempt,
    }
    if case.get("cohort") != "X":
        task["knowledge_base_id"] = kb_id
        task["top_k"] = 5
    _, created = call(
        api,
        "POST",
        f"/v1/agents/{agent_id}/runs",
        {
            "input": {
                "model": "deepseek:deepseek-flash",
                "fallback_models": [],
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(task, ensure_ascii=False)},
                ],
            }
        },
    )
    assert created is not None
    run_id = created["id"]
    call(api, "POST", f"/v1/runs/{run_id}/queue", {})
    started = time.time()
    final = wait_terminal(api, run_id)
    elapsed = time.time() - started
    _, events = call(api, "GET", f"/v1/runs/{run_id}/events")
    if isinstance(events, dict):
        events = events.get("items") or events.get("events") or []
    output = final.get("output")
    text = None
    if isinstance(output, dict):
        text = output.get("text")
    elif isinstance(output, str):
        text = output
    record = {
        "case_id": case["id"],
        "cohort": case["cohort"],
        "attempt": attempt,
        "question": case["question"],
        "run_id": run_id,
        "status": final["status"],
        "error_type": final.get("error_type"),
        "error_message": final.get("error_message"),
        "input_tokens_total": final.get("input_tokens_total"),
        "output_tokens_total": final.get("output_tokens_total"),
        "elapsed_s": round(elapsed, 3),
        "event_types": [e.get("type") for e in events],
        "output_text": text,
        "output": output,
    }
    out_path = evidence / "attempts" / f"{case['id']}-a{attempt}-{run_id}.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--kb-id", required=True)
    parser.add_argument(
        "--evidence-dir",
        default=str(DEFAULT_EVIDENCE),
        help="Private evidence directory (default: .agent-kernel/pv3-evidence)",
    )
    parser.add_argument(
        "--prompt",
        default=str(DEFAULT_PROMPT),
        help="Task prompt file (default: pv1-runbook-assistant-v3.txt)",
    )
    parser.add_argument("--only", default="", help="Comma-separated case ids (optional)")
    parser.add_argument("--attempts", type=int, default=2, choices=(1, 2))
    parser.add_argument("--start-after", default="", help="Skip until after this case id")
    args = parser.parse_args()

    evidence = Path(args.evidence_dir)
    if not evidence.is_absolute():
        evidence = ROOT / evidence
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "attempts").mkdir(parents=True, exist_ok=True)
    prompt_path = Path(args.prompt)
    if not prompt_path.is_absolute():
        prompt_path = ROOT / prompt_path
    prompt = prompt_path.read_text(encoding="utf-8")
    cases = json.loads(QUESTIONS.read_text(encoding="utf-8"))["cases"]
    if args.only:
        wanted = {x.strip() for x in args.only.split(",") if x.strip()}
        cases = [c for c in cases if c["id"] in wanted]
    if args.start_after:
        idx = next(i for i, c in enumerate(cases) if c["id"] == args.start_after)
        cases = cases[idx + 1 :]

    summary_path = evidence / "cohort-summary.jsonl"
    if summary_path.exists():
        summary_path.unlink()
    ledger: list[dict] = []
    for case in cases:
        for attempt in range(1, args.attempts + 1):
            print(f"RUN {case['id']} attempt={attempt} ...", flush=True)
            try:
                record = one_attempt(
                    args.api,
                    args.agent_id,
                    args.kb_id,
                    prompt,
                    case,
                    attempt,
                    evidence,
                )
            except Exception as exc:  # noqa: BLE001 - persist and continue/stop policy
                record = {
                    "case_id": case["id"],
                    "cohort": case["cohort"],
                    "attempt": attempt,
                    "status": "runner_error",
                    "error_message": str(exc)[:2000],
                }
                print(f"  ERROR {exc}", flush=True)
            else:
                print(
                    f"  {record['status']} tokens="
                    f"{record.get('input_tokens_total')}/{record.get('output_tokens_total')} "
                    f"elapsed={record.get('elapsed_s')}s",
                    flush=True,
                )
            ledger.append(
                {
                    k: record.get(k)
                    for k in (
                        "case_id",
                        "cohort",
                        "attempt",
                        "run_id",
                        "status",
                        "input_tokens_total",
                        "output_tokens_total",
                        "elapsed_s",
                        "error_type",
                        "error_message",
                    )
                }
            )
            with summary_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(ledger[-1], ensure_ascii=False) + "\n")
            if record.get("status") == "runner_error":
                print("Stopping on runner_error to protect budget.", flush=True)
                break
        else:
            continue
        break

    (evidence / "cohort-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n"
    )
    succeeded = sum(1 for row in ledger if row.get("status") == "succeeded")
    print(f"DONE attempts={len(ledger)} succeeded={succeeded}", flush=True)
    return 0 if succeeded == len(ledger) and ledger else 1


if __name__ == "__main__":
    raise SystemExit(main())
