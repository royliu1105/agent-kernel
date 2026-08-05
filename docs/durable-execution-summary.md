# Durable Execution Summary: Day 59-63

## Status

The first Beta durable execution track is complete under the Day 59-63 scope.

```text
Day 59-63: Worker leases, stuck-run recovery, Redis queue adapter foundation,
retry visibility, worker restart regression coverage, and operator CLI tests.
```

This track makes queued run execution more production-shaped while keeping the
database as the source of truth. It intentionally avoids turning Agent Kernel
into a full workflow engine at this stage.

## Completed Baseline

Durable run state:

- Runs and run events are persisted in the database.
- Queued runs are selected from persisted `runs.status = queued` rows.
- Run timelines preserve created, queued, started, retrying, completed, failed,
  waiting approval, and resume events.

Worker execution:

- `QueuedRunWorker` processes persisted queued runs in created-at order.
- Worker execution works for model calls, safe tools, approval-pausing risky
  tools, RAG search tools, provider failures, and route errors.
- `agent-kernel-worker --once --limit N` is covered by regression tests and can
  execute persisted queued runs through the real CLI entrypoint.

Worker leases:

- `worker_leases` stores worker claims with worker id, lease token, heartbeat,
  expiration, and release timestamps.
- Lease acquisition rejects non-queued runs, duplicate active claims, empty
  worker ids, and invalid TTLs.
- Expired leases can be reacquired or recovered without treating Redis as
  durable state.

Stuck-run recovery:

- `StuckRunRecoveryService` inspects expired leases.
- Expired `running` and `resuming` runs are failed with
  `error_type = worker_lease_expired`.
- Expired leases on non-recoverable statuses are released without mutating the
  run.
- `agent-kernel-worker --recover-stuck --limit N` is covered by regression
  tests and uses the production recovery entrypoint.

Retry visibility:

- Provider retry and fallback events are persisted in run timelines.
- Safe tool retry events are persisted in run timelines.
- Tests reopen the database session after execution to prove retry events and
  tool results remain inspectable outside process memory.

Queue adapter foundation:

- `RunQueue` is the runtime queue coordination port.
- `InMemoryRunQueue` provides deterministic local/test behavior.
- `RedisRunQueue` provides a Redis-list-backed adapter using run ids only.
- Redis is a coordination and wakeup layer, not the durable source of truth.

## Operator Commands

Check the worker binary:

```bash
uv run agent-kernel-worker
```

Process queued runs once:

```bash
uv run agent-kernel-worker --once --limit 10
```

Recover expired in-flight leases:

```bash
uv run agent-kernel-worker --recover-stuck --limit 100
```

Run a polling worker:

```bash
uv run agent-kernel-worker --loop --limit 25 --poll-interval 2
```

## Current Semantics

The Day 59-63 recovery policy is conservative:

- A stuck in-flight run is failed rather than automatically requeued.
- This avoids blindly repeating side-effectful work.
- Operators can inspect the failed run, events, lease id, worker id, and error
  payload before deciding how to retry manually.

The worker still polls the database for queued runs by default:

- Postgres or SQLite remains authoritative for run state.
- Redis queue entries are hints and coordination records only.
- A future worker can use Redis wakeups while still verifying database state
  before execution.

## Explicit Non-Goals

These are not part of the Day 59-63 closure:

- Provider-native function calling.
- Provider-returned tool call parsing.
- Durable model/tool/model loops that continue after provider-native tool
  calls.
- Automatic requeue of expired in-flight runs.
- Delayed retry scheduling or exponential backoff.
- Public manual retry API.
- Redis-backed worker polling as the default execution path.
- Temporal or another external workflow engine.

## Follow-Up

Day 64-67 starts provider-native tool calling:

- Day 64: provider-native tool-call adapter contract.
- Day 65: OpenAI native tool-call parsing and persistence.
- Day 66: model/tool/model execution loop.
- Day 67: provider-native tool-call evals and regression tests.

These days build on the durable execution baseline rather than replacing it.
