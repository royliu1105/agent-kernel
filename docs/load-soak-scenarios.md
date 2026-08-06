# Load and Soak Scenarios

This document defines the v1.0 release candidate load and soak test strategy.

Load tests answer:

```text
Does the system keep correct behavior under a larger burst of work?
```

Soak tests answer:

```text
Does the system keep correct behavior over time without accumulating stuck work,
resource leaks, or unacceptable latency?
```

## Quick Local Gate

Run:

```bash
make release-load-soak
```

The default gate runs:

```bash
uv run python scripts/release_load_soak.py --profile quick
```

Current quick profile:

| Setting | Value |
| --- | --- |
| Scenario | `queued-worker-burst` |
| Runs | 25 |
| Worker batch size | 10 |
| Backend | In-memory SQLite |
| Provider | Mock LLM provider |
| External services | None |
| Max elapsed time | 5 seconds |

The quick gate verifies:

- Runs can be created durably.
- Runs can transition to `queued`.
- The worker can poll queued runs in batches.
- The mock model route can execute every run.
- All runs reach `succeeded`.
- No run fails.
- No queued run remains after the burst.
- Persisted terminal state matches worker summary state.

## Local Extended Profile

Run:

```bash
uv run python scripts/release_load_soak.py --profile local
```

Current local profile:

| Setting | Value |
| --- | --- |
| Scenario | `queued-worker-burst` |
| Runs | 100 |
| Worker batch size | 25 |
| Backend | In-memory SQLite |
| Provider | Mock LLM provider |
| External services | None |
| Max elapsed time | 20 seconds |

Use this before larger release rehearsals when changing worker, queue, storage,
state machine, model routing, or observability code.

## Infrastructure-Backed Release Scenarios

These scenarios are release rehearsal checks, not default CI gates.

| Scenario | Target | Why It Is Not Default CI |
| --- | --- | --- |
| Postgres worker burst | 100-1,000 queued mock runs through Docker Compose Postgres. | Requires container startup and has higher runtime. |
| Redis queue adapter burst | Enqueue/dequeue burst through Redis queue adapter. | Requires Redis runtime and queue wiring selection. |
| RAG ingestion burst | Upload, parse, chunk, embed, and index many documents. | Requires object store, vector store mode, and larger fixtures. |
| pgvector retrieval soak | Repeated retrieval against pgvector-backed embeddings. | Requires Postgres/pgvector and realistic corpus setup. |
| Approval backlog soak | Many approval-required tool calls remain inspectable and resumable. | Requires operator workflow decisions and longer duration. |
| API HTTP burst | Repeated create-run, queue, inspect, and timeline requests. | Requires live API process and port management. |
| Web operator smoke loop | Repeated workbench page/API route load. | Belongs with browser e2e and clean-machine rehearsal. |
| Live provider soak | Real provider calls over a bounded time window. | Requires secrets, cost budget, rate-limit policy, and flake handling. |

## Suggested Release Thresholds

Initial v1.0 RC thresholds:

- Quick local gate: 25 queued runs, 100% success, no remaining queued runs,
  under 5 seconds.
- Local extended profile: 100 queued runs, 100% success, no remaining queued
  runs, under 20 seconds.
- Infrastructure-backed Postgres worker burst: 500 queued mock runs, 100%
  terminal state, no stuck runs after recovery, threshold recorded in release
  notes.
- Live provider soak: optional only, cost-capped, with failures recorded as
  release risk notes rather than default blockers.

Thresholds should be tightened only after repeated green release rehearsals.

## Failure Handling

If a load or soak scenario fails:

1. Identify whether the failure is correctness, latency, flake, or environment.
2. Correctness failures block release work.
3. Latency failures block release work only when they exceed the documented
   threshold for that profile.
4. Environment failures require rerun evidence and troubleshooting notes.
5. Update this document if the release contract changes.

Do not hide load/soak failures by lowering thresholds without documenting the
release risk.
