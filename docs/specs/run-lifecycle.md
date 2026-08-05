# Feature Spec: Run Lifecycle

## Goal

Define how an Agent run is created, queued, executed, paused, resumed, retried, canceled, failed, and completed.

## Non-Goals

- Full Temporal integration in v0.1.
- Complex visual workflow graph editing.
- Distributed multi-worker scheduling guarantees beyond the MVP queue and persisted state model.

## User Stories

- As a developer, I can create a run and inspect its current state.
- As an operator, I can understand why a run is waiting, failed, or completed.
- As a worker, I can resume work from persisted state after a crash.
- As an evaluator, I can replay or compare run behavior across versions.

## Domain Model

Initial entities:

- `Run`
- `RunStep`
- `Message`
- `ToolCall`
- `Approval`
- `RunEvent`
- `WorkerLease`

Day 2 storage contract:

- IDs are UUIDs in the domain and API, stored as 36-character strings in the initial database
  schema for SQLite/Postgres portability.
- API request/response schemas are separate DTOs. Domain models stay infrastructure-free.
- `RunEvent` is append-only timeline data scoped to a run.
- Event `sequence` is monotonically increasing per run.
- The first persisted event for a run is `run_created` with payload `{ "status": "created" }`.
- The first migration is named `0001_create_execution_tables`.

Initial run states:

```text
created
queued
running
waiting_approval
resuming
succeeded
failed
canceled
```

## State Transitions

Initial lifecycle:

```text
created -> queued -> running -> succeeded
created -> queued -> running -> failed
created -> queued -> running -> waiting_approval -> resuming -> running -> succeeded
created -> queued -> running -> waiting_approval -> failed
created -> queued -> running -> canceled
```

Day 3 transition table:

| From | Allowed To |
| --- | --- |
| `created` | `queued`, `canceled` |
| `queued` | `running`, `canceled` |
| `running` | `waiting_approval`, `succeeded`, `failed`, `canceled` |
| `waiting_approval` | `resuming`, `failed`, `canceled` |
| `resuming` | `running`, `canceled` |
| `succeeded` | terminal |
| `failed` | terminal |
| `canceled` | terminal |

Transition rules:

- Runtime state transitions are validated in `kernel-runtime`.
- Storage persists state and events but does not own transition legality.
- Invalid transitions are rejected before persistence.
- Every accepted transition appends a `RunEvent`.
- Queueing is persisted as `queued` state in Postgres for v0.1; Redis-backed queueing is a later
  worker/runtime concern.

Day 3 transition events:

| Target Status | Event |
| --- | --- |
| `queued` | `run_queued` |
| `running` | `run_started` |
| `waiting_approval` | `run_waiting_approval` |
| `resuming` | `run_resuming` |
| `succeeded` | `run_completed` |
| `failed` | `run_failed` |
| `canceled` | `run_canceled` |

Day 4 execution semantics:

- The runtime execution service executes one queued run at a time.
- A run must be `queued` before execution starts.
- Execution starts by transitioning `queued -> running` and appending `run_started`.
- The initial execution service performs one non-streaming provider call.
- Day 5 execution routes provider-prefixed model strings such as `mock:mock-small` and
  `openai:gpt-4.1-mini`.
- The provider receives the model name without the routing prefix.
- Provider success persists `runs.output` with shape `{ "text": "...", "provider": "...",
  "model": "...", "usage": { ... } }`.
- Provider success transitions `running -> succeeded` and appends `run_completed`.
- Provider failure persists `error_type` and `error_message`.
- Provider failure transitions `running -> failed` and appends `run_failed`.
- Execution setup failures, such as invalid run input messages or unknown model routes, transition
  the run from `running -> failed` instead of leaving it stuck in `running`.

Day 6 worker semantics:

- The MVP worker uses persisted `runs.status = queued` rows as the durable queue.
- A worker polling pass lists queued runs in creation order and executes up to the configured limit.
- Each picked run is executed through `RunExecutionService` and `ModelRouter`.
- The worker runs each picked run with its own database session so one failure does not poison the
  rest of the batch.
- `agent-kernel-worker --once --limit 10` performs one deterministic polling pass and exits.
- `agent-kernel-worker --loop --limit 10 --poll-interval 5` keeps polling for local development.
- The worker default router registers `mock` and `openai`; mock execution requires no secrets.
- OpenAI execution remains opt-in through `openai:*` model references and `OPENAI_API_KEY`.
- Redis is not used as the Day 6 queue. Redis-backed scheduling, leasing, heartbeats, and
  distributed concurrency are explicitly deferred.

Day 59 worker lease storage semantics:

- `WorkerLease` is an internal coordination record for durable worker execution.
- A lease references one run and records `worker_id`, opaque `lease_token`,
  `acquired_at`, `heartbeat_at`, `expires_at`, and optional `released_at`.
- Only queued runs can acquire a lease.
- A run can have at most one active, unreleased, unexpired lease.
- Heartbeats extend lease expiration only when the caller presents the active
  lease token.
- Release marks the lease as no longer active.
- Expired leases can be superseded by a new lease.
- Day 59 does not change the public run status machine and does not switch the
  worker polling loop to lease-backed claiming.

Day 60 stuck-run recovery semantics:

- Recovery scans expired, unreleased worker leases.
- Expired leases for `running` and `resuming` runs transition those runs to
  `failed` with `error_type = worker_lease_expired`.
- Recovery appends `run_failed` with lease id, worker id, previous status, and
  failure reason.
- Expired leases for `queued` runs are released without failing the run.
- Non-expired leases are ignored.
- Recovery is explicit through runtime service or
  `agent-kernel-worker --recover-stuck`; it is not automatically run before
  every worker polling pass yet.
- Recovery does not automatically requeue expired running work because tool
  side effects must not be repeated blindly.

Day 61 Redis queue adapter baseline:

- `RunQueue` is the runtime port for queued run id coordination.
- `InMemoryRunQueue` provides deterministic local and test behavior.
- `RedisRunQueue` adapts a minimal redis-py-compatible client protocol.
- The default Redis list key is `agent-kernel:runs:queued`.
- Redis queue entries carry run ids only.
- Workers must still verify persisted Postgres run status and lease state before
  execution.
- Redis is a coordination and wakeup layer, not the durable source of truth.
- Day 61 does not wire Redis into API queueing or default worker polling.

Day 62 durable retry and restart visibility baseline:

- Provider retry events remain persisted and inspectable after reopening a
  database session.
- Safe tool retry events remain persisted and inspectable after reopening a
  database session.
- Worker restart recovery is covered by regression tests: an expired
  `running` lease can be recovered by a new process and the failed stuck run is
  not executed again by a restarted worker.
- Day 62 does not add delayed retry scheduling, exponential backoff, a public
  retry API, or automatic Redis-backed worker polling.

Day 12 approval interrupt/resume semantics:

- `RunExecutionService` supports explicit single-tool input under `input.tool`.
- If no `input.tool` is present, the model-call execution path remains unchanged.
- Safe explicit tools execute during the initial queued run execution path and complete the run.
- Approval-required tools persist a tool call and approval, then transition the run to
  `waiting_approval`.
- The worker still polls only `queued` runs, so waiting runs are durable interrupt points.
- `POST /v1/runs/{run_id}/resume` resumes a waiting run after approval is approved.
- Resume transitions `waiting_approval -> resuming -> running`, executes the persisted tool call,
  then completes the run.
- Rejected approval resume transitions the run to `failed` with `error_type = approval_rejected`.

Day 13 retry/fallback semantics:

- Retry/fallback is an in-process runtime policy for v0.1.
- Retry attempts do not create new run statuses; the run remains `running` until final success,
  failure, waiting approval, or cancellation.
- Retryable provider errors can be retried on the same model.
- Explicit `fallback_models` in run input can select a fallback model after retryable provider
  errors.
- Non-retryable provider errors still fail the run safely.
- Retryable safe/read-only tool errors can be retried once by default.
- Invalid tool arguments are not retried.
- Denied tools, approval-required tools, and rejected approvals are not automatically retried.
- Retry/fallback attempts are auditable through run events.
- Delayed retries, exponential backoff, external durable retry queues, and a public retry API remain
  deferred.

Day 13 retry/fallback events:

```text
model_call_retrying
model_fallback_selected
tool_call_retrying
```

## API / CLI

Day 2 API:

```http
POST /v1/agents
GET  /v1/agents/{agent_id}
POST /v1/agents/{agent_id}/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/events
```

Day 3 API:

```http
POST /v1/runs/{run_id}/queue
POST /v1/runs/{run_id}/cancel
```

Day 12 API:

```http
POST /v1/runs/{run_id}/resume
```

Expected later API:

```http
POST /v1/agents/{agent_id}/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/resume
POST /v1/runs/{run_id}/retry
```

Day 13 keeps `POST /v1/runs/{run_id}/retry` deferred because automatic retry/fallback happens
inside execution policy.

Day 3 CLI:

```bash
agent-kernel agent create --name "..."
agent-kernel run create <agent-id> --input '{"task":"..."}'
agent-kernel run inspect <run-id>
agent-kernel run events <run-id>
```

Day 7 CLI:

```bash
agent-kernel run queue <run-id>
agent-kernel run cancel <run-id>
```

Day 12 CLI:

```bash
agent-kernel run resume <run-id> --approval-id <approval-id>
```

Day 6 worker CLI:

```bash
agent-kernel-worker
agent-kernel-worker --once --limit 10
agent-kernel-worker --loop --limit 10 --poll-interval 5
```

Expected later CLI:

```bash
agent-kernel run watch <run-id>
agent-kernel run retry <run-id>
```

## Failure Modes

- Worker crashes mid-run.
- Model provider fails.
- Worker encounters invalid run input or an unknown model route.
- Tool call fails.
- Approval is rejected.
- Run is canceled while running.
- Retry would repeat a non-idempotent side effect.
- Fallback model is misconfigured.
- Retryable error keeps failing after all attempts.

## Security

- Run state changes must be authorized.
- Cancellation, retry, and resume should be auditable.
- Tool side effects must not be repeated blindly during recovery.

## Observability

- Every run has a `trace_id`.
- Every step has timing and status.
- State transitions emit events.
- Failures record error type and message.

## Test Plan

- Create run persists initial state.
- Worker transitions run to running and succeeded.
- Failed step transitions run to failed.
- Worker only picks queued runs.
- Worker records provider failures as failed runs.
- Worker records expected execution setup failures as failed runs.
- API-created queued run can be executed by a worker and inspected through the API.
- CLI queue and cancel call the API transition endpoints.
- Approval request transitions run to waiting state.
- Resume continues from persisted state.
- Cancel stops a run safely.
- Retryable provider failure retries.
- Retryable provider failure can use explicit fallback model.
- Retryable safe tool failure retries.
- Non-retryable failures are not retried.

## Acceptance Criteria

- A run can be created, executed, inspected, and completed.
- Run steps are persisted.
- Run state is recoverable from storage.
- Timeline can be rendered from persisted data.
