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
created -> queued -> running -> canceled
```

Detailed transition rules will be completed during Phase 1 implementation.

## API / CLI

Expected API:

```http
POST /v1/agents/{agent_id}/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/cancel
POST /v1/runs/{run_id}/resume
POST /v1/runs/{run_id}/retry
```

Expected CLI:

```bash
agent-kernel run create <agent-id> --input "..."
agent-kernel run watch <run-id>
agent-kernel run inspect <run-id>
agent-kernel run retry <run-id>
agent-kernel run cancel <run-id>
```

## Failure Modes

- Worker crashes mid-run.
- Model provider fails.
- Tool call fails.
- Approval is rejected.
- Run is canceled while running.
- Retry would repeat a non-idempotent side effect.

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
- Approval request transitions run to waiting state.
- Resume continues from persisted state.
- Cancel stops a run safely.

## Acceptance Criteria

- A run can be created, executed, inspected, and completed.
- Run steps are persisted.
- Run state is recoverable from storage.
- Timeline can be rendered from persisted data.
