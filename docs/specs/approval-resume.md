# Feature Spec: Approval and Resume

## Goal

Support human-in-the-loop approval for risky actions, including pausing a run, recording a decision, and resuming or stopping safely.

## Non-Goals

- Full enterprise approval workflows.
- Multi-person quorum approval.
- External ticketing system integration.
- Complex policy language in v0.1.

## User Stories

- As an operator, I can see pending approvals.
- As a reviewer, I can inspect tool arguments and risk level before deciding.
- As a user, I can approve a tool call and let the run continue.
- As a user, I can reject a tool call and stop the risky action.

## Domain Model

Initial entities:

- `Approval`
- `ToolCall`
- `Run`
- `RunStep`
- `PolicyDecision`

Approval states:

```text
requested
approved
rejected
expired
canceled
```

Day 11 approval persistence baseline:

- `approvals` stores human approval requests and decisions.
- Approval requests are created for persisted tool calls that require approval.
- Requested approvals can be listed and inspected.
- Requested approvals can be approved.
- Requested approvals can be rejected with a reason.
- Duplicate decisions are rejected.
- Approval request and decision events are appended to the run timeline.
- Day 11 API exposes list, get, approve, and reject endpoints.
- Day 11 CLI exposes list, inspect, approve, and reject commands.
- Day 11 does not resume runs or stop rejected runs yet.

Day 12 interrupt/resume baseline:

- Runtime execution supports explicit single-tool run input through `input.tool`.
- Risky explicit tools create a persisted tool call, record the policy decision, create an approval,
  and transition the run to `waiting_approval`.
- Waiting runs are not picked again by the queued-run worker.
- Approved approvals can resume the run through runtime, API, and CLI.
- Resume transitions `waiting_approval -> resuming -> running`.
- Resume executes the original persisted tool call arguments. Resume callers cannot supply new
  arguments.
- Successful resumed tool execution completes the run with output under `output.tool`.
- Rejected approvals fail the waiting run with `error_type = approval_rejected`.
- Requested, missing, unrelated, expired, or canceled approvals cannot resume execution.
- Day 12 remains explicit-tool only. Provider-native function calling and model-generated tool call
  parsing are deferred.

## State Transitions

Initial flow:

```text
tool_call_requested -> policy_requires_approval -> approval_requested -> run_waiting_approval
approval_approved -> run_resuming -> running
approval_rejected -> run_failed_or_stopped
```

Detailed resume semantics will be completed during Phase 2 implementation.

Day 11 decision events:

```text
approval_requested
approval_approved
approval_rejected
```

Day 12 run transition events:

```text
run_waiting_approval
run_resuming
run_started
run_completed
run_failed
```

## API / CLI

Expected API:

```http
GET  /v1/approvals
GET  /v1/approvals/{approval_id}
POST /v1/approvals/{approval_id}/approve
POST /v1/approvals/{approval_id}/reject
POST /v1/runs/{run_id}/resume
```

Expected CLI:

```bash
agent-kernel approval list
agent-kernel approval inspect <approval-id>
agent-kernel approval approve <approval-id>
agent-kernel approval reject <approval-id> --reason "Not allowed"
agent-kernel run resume <run-id> --approval-id <approval-id>
```

## Failure Modes

- Approval is rejected.
- Approval is decided twice.
- Approval references a missing tool call.
- Approval is missing.
- Run is canceled while waiting.
- Tool arguments change after approval request.
- Worker crashes while run is waiting.
- Resume is attempted before approval is decided.
- Resume references an approval from another run.

## Security

- Only authorized users can approve or reject.
- Approval decision must be audited.
- Approved arguments must match requested arguments.
- Risk and side effects must be visible to reviewers.

Day 57 approval authorization baseline:

- Approval authorization uses the authenticated API key workspace.
- Approval workspace scope is derived from the approval's run instead of storing
  a second workspace id on the approval record.
- Approval list, inspect, approve, and reject API routes only operate on
  approvals in the current workspace when API key auth is enabled.
- Approval decisions record the authenticated principal id as `reviewed_by`.
- Resume requests that reference an approval outside the current workspace are
  rejected before runtime resume logic executes.
- Local unauthenticated quickstart flows keep the previous unscoped approval
  behavior.

## Observability

- Approval request span/event.
- Approval wait duration.
- Decision actor.
- Decision timestamp.
- Decision note.

## Test Plan

- Risky tool creates approval.
- Approval can be listed and inspected.
- Approval decision is recorded once.
- Duplicate decision is rejected.
- Run pauses while waiting.
- Approval resumes run.
- Rejection stops run safely.
- Duplicate decision is rejected.
- Resume uses persisted tool call arguments.
- Approval wait time is recorded.

## Acceptance Criteria

- A risky tool call can pause a run.
- A user can approve or reject through CLI/API.
- Approved runs resume from persisted state.
- Approval decisions are auditable.
