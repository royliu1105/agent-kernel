# Phase 2 Summary: Tools, Policy, Approval, Retry, and Fallback

## Status

Phase 2 is complete.

Agent Kernel now has the first production-shaped safe tool execution path:

```text
create agent
-> create run with explicit tool input
-> queue run
-> worker starts run
-> runtime persists tool call
-> policy evaluates tool risk
-> safe tool executes automatically
-> risky tool pauses for approval
-> operator approves or rejects
-> approved run resumes from persisted tool call
-> rejected run fails safely
-> retry/fallback attempts are audited
```

This moves Agent Kernel from "agent can call a model" to "agent can safely call tools with policy,
human approval, durable interruption, resume, and conservative retry/fallback."

## Phase Goal

Phase 2 goal:

```text
Let agents call tools safely with policy checks and human approval.
```

The implementation had to be:

- Schema-validated.
- Policy-aware.
- Risk-level driven.
- Persisted.
- Auditable through run events.
- Safe by default.
- Human-reviewable.
- Recoverable after approval.
- Conservative about retries and side effects.
- Covered by deterministic tests.

## Daily Delivery

### Day 8: Tool Interface and Safe Execution Foundation

Delivered:

- `Tool` protocol.
- `ToolMetadata`, `ToolRequest`, and `ToolResult`.
- `ToolRegistry`.
- `ToolExecutor`.
- JSON Schema input validation.
- Tool output shape and size checks.
- Timeout handling.
- First safe built-in tool: `EchoTool`.

Outcome:

```text
The runtime gained a validated, bounded, deterministic tool execution primitive.
```

### Day 9: Policy Decisions for Tool Execution

Delivered:

- `RiskLevel` domain model.
- `PolicyDecisionType`.
- `PolicyDecision`.
- `ToolPolicy`.
- `ToolPolicyEvaluator`.
- `PolicyAwareToolExecutor`.
- Default risk policy:
  - `read_only` -> `allow`
  - `external_write` -> `require_approval`
  - `filesystem_write` -> `require_approval`
  - `network` -> `require_approval`
  - `dangerous` -> `deny`

Outcome:

```text
Tool execution became governed by explicit allow, deny, and require-approval decisions.
```

### Day 10: Persisted Tool Calls and Audit Timeline

Delivered:

- `ToolCall` domain model.
- `tool_calls` storage model.
- Alembic migration `0002_create_tool_calls`.
- `ToolCallRepository`.
- Tool call lifecycle persistence.
- Policy decision persistence.
- Tool success/failure persistence.
- Run timeline events:
  - `tool_call_requested`
  - `policy_evaluated`
  - `tool_call_completed`
  - `tool_call_failed`

Outcome:

```text
Tool requests and outcomes became inspectable and recoverable from storage.
```

### Day 11: Approval Records, API, and CLI

Delivered:

- `Approval` domain model.
- `approvals` storage model.
- Alembic migration `0003_create_approvals`.
- `ApprovalRepository`.
- Approval list/get/approve/reject operations.
- Duplicate decision protection.
- Approval request and decision audit events.
- API endpoints:
  - `GET /v1/approvals`
  - `GET /v1/approvals/{approval_id}`
  - `POST /v1/approvals/{approval_id}/approve`
  - `POST /v1/approvals/{approval_id}/reject`
- CLI commands:
  - `agent-kernel approval list`
  - `agent-kernel approval inspect <approval-id>`
  - `agent-kernel approval approve <approval-id>`
  - `agent-kernel approval reject <approval-id> --reason "..."`

Outcome:

```text
Human approval decisions became real operator workflows instead of in-memory placeholders.
```

### Day 12: Approval Interrupt and Resume

Delivered:

- Run transition events:
  - `run_waiting_approval`
  - `run_resuming`
- Run state machine helpers:
  - `wait_for_approval`
  - `resume`
- Runtime support for explicit single-tool input under `input.tool`.
- Safe explicit tool execution path.
- Risky explicit tool interrupt path.
- Approval-required tool call persistence.
- Run transition to `waiting_approval`.
- Approved run resume from persisted tool call arguments.
- Rejected approval safe failure with `error_type = approval_rejected`.
- API endpoint:
  - `POST /v1/runs/{run_id}/resume`
- CLI command:
  - `agent-kernel run resume <run-id> --approval-id <approval-id>`

Outcome:

```text
Risky tool calls became durable interrupt points that can be approved, resumed, or rejected.
```

### Day 13: Phase 2 Retry and Fallback Closure

Delivered:

- `RetryPolicy`.
- Conservative provider retry.
- Explicit model fallback through `fallback_models`.
- Safe/read-only tool retry.
- Retry/fallback run events:
  - `model_call_retrying`
  - `model_fallback_selected`
  - `tool_call_retrying`
- No retry for invalid tool arguments.
- No automatic retry for denied tools.
- No automatic retry for approval-required tools.
- No automatic retry for side-effecting risk levels.
- Phase 2 milestone closure.

Outcome:

```text
Retry/fallback became observable execution policy without adding unsafe side-effect repetition.
```

## Current Capabilities

### Explicit Tool Input

Implemented input shape:

```json
{
  "tool": {
    "name": "echo",
    "arguments": {
      "message": "hello"
    }
  }
}
```

If no `tool` object is present, the existing model-call execution path remains unchanged.

### API

Phase 2 added:

```http
GET  /v1/approvals
GET  /v1/approvals/{approval_id}
POST /v1/approvals/{approval_id}/approve
POST /v1/approvals/{approval_id}/reject
POST /v1/runs/{run_id}/resume
```

The complete API surface now includes Phase 1 run lifecycle plus Phase 2 approval operations.

### CLI

Phase 2 added:

```bash
agent-kernel approval list
agent-kernel approval inspect <approval-id>
agent-kernel approval approve <approval-id> --note "..."
agent-kernel approval reject <approval-id> --reason "..."
agent-kernel run resume <run-id> --approval-id <approval-id>
```

### Runtime

Implemented:

- Explicit tool request detection.
- Tool registry lookup.
- Tool schema validation.
- Policy evaluation.
- Tool call persistence.
- Approval persistence.
- Run interruption.
- Resume from persisted approval/tool call.
- Rejected approval failure.
- Provider retry.
- Explicit model fallback.
- Safe tool retry.

### Policy

Implemented default policy:

```text
read_only        -> allow
external_write   -> require_approval
filesystem_write -> require_approval
network          -> require_approval
dangerous        -> deny
```

This is intentionally conservative. The default install exposes only safe built-in tools.

### Audit Timeline

Phase 2 added these event types:

```text
tool_call_requested
policy_evaluated
tool_call_completed
tool_call_failed
tool_call_retrying
approval_requested
approval_approved
approval_rejected
run_waiting_approval
run_resuming
model_call_retrying
model_fallback_selected
```

Run events remain the MVP audit log. A dedicated audit-event table is deferred.

## Persistence Model

Phase 2 persists:

- Tool call request.
- Tool name.
- Tool arguments.
- Tool result.
- Tool risk level.
- Tool status.
- Tool approval linkage.
- Tool error type/message.
- Approval request.
- Approval status.
- Approval decision note.
- Approval reviewer fields for future auth integration.
- Approval resolved timestamp.
- Run timeline events for policy, tool, approval, retry, fallback, and resume behavior.

Phase 2 migrations:

```text
0002_create_tool_calls
0003_create_approvals
```

## Quality Status

Latest Phase 2 verification:

```text
uv sync
uv run pytest              -> 88 passed, 1 known warning
uv run ruff check .        -> passed
uv run mypy .              -> passed
docker compose config      -> passed
pre-commit run --all-files -> passed
```

Known warning:

- FastAPI/Starlette `TestClient` emits a deprecation warning about `httpx`. Tests pass; revisit when
  the dependency ecosystem settles.

## Test Coverage

Phase 2 added coverage for:

- Tool registry behavior.
- Tool schema validation.
- Tool timeout and failure handling.
- Tool result size limits.
- Policy evaluator decisions.
- Policy-aware execution.
- Tool call persistence.
- Tool call audit events.
- Approval repository behavior.
- Approval API behavior.
- Approval CLI commands.
- Duplicate approval decisions.
- Runtime safe tool execution.
- Runtime risky tool approval pause.
- Runtime approved resume.
- Runtime rejected approval failure.
- Worker waiting-run behavior.
- Provider retry.
- Explicit model fallback.
- Safe tool retry.
- Invalid tool argument no-retry behavior.

Important test guarantee:

```text
Normal tests do not require network access or real API keys.
```

## Deliberate Non-Goals

Phase 2 intentionally did not implement:

- Provider-native function calling.
- Model-generated tool call parsing.
- Multi-step agent planning loop.
- Arbitrary shell tool.
- Network tool.
- Filesystem write tool.
- Web UI approval inbox.
- API key auth or RBAC.
- Dedicated audit-event table.
- External audit sink.
- Distributed durable retry queue.
- Delayed retry scheduling.
- Exponential backoff.
- Manual retry API.

These are deferred because Phase 2 needed to stabilize safety semantics before adding broader agent
autonomy and production operations.

## Key Tradeoffs

### Explicit Tool Input Before Provider-Native Tool Calling

Phase 2 uses explicit run input:

```json
{
  "tool": {
    "name": "echo",
    "arguments": {
      "message": "hello"
    }
  }
}
```

Why:

- It lets the project validate tool persistence, policy, approval, resume, and retry semantics.
- It avoids mixing model-specific function-calling APIs into the safety architecture too early.
- It keeps deterministic tests small and fast.

Deferred:

- OpenAI-native tool calling.
- Provider-agnostic tool schema conversion.
- Model-generated tool call parsing.
- Multi-tool loops.

### Run Events As MVP Audit Log

Run events are used as the audit timeline.

Why:

- They already have run scope, sequence numbers, payloads, timestamps, and trace IDs.
- They are easy to render in CLI/API/Web later.
- They avoid designing a second audit table before auth and tenancy exist.

Deferred:

- Dedicated audit-event table.
- External immutable audit sink.
- User/role authorization semantics.

### Conservative Retry Policy

Retries are intentionally narrow.

Why:

- Retrying side effects can duplicate writes.
- Approval-required actions need human review, not blind repetition.
- Invalid inputs should fail loudly rather than consume attempts.

Implemented:

- Retryable provider errors can retry.
- Explicit fallback models can be attempted.
- Safe/read-only tool execution failures can retry.

Deferred:

- Retry budgets per tenant/project.
- Delayed retries.
- Exponential backoff.
- Distributed retry orchestration.

## How To Run The Current Path

Safe explicit tool path:

```bash
uv run alembic upgrade head
uv run agent-kernel-api
uv run agent-kernel agent create --name "Tool Agent"
uv run agent-kernel run create <agent-id> --input '{"tool":{"name":"echo","arguments":{"message":"hello"}}}'
uv run agent-kernel run queue <run-id>
uv run agent-kernel-worker --once --limit 10
uv run agent-kernel run inspect <run-id>
uv run agent-kernel run events <run-id>
```

Expected safe-tool timeline:

```text
run_created
run_queued
run_started
tool_call_requested
policy_evaluated
tool_call_completed
run_completed
```

Approval path:

```bash
uv run agent-kernel approval list
uv run agent-kernel approval inspect <approval-id>
uv run agent-kernel approval approve <approval-id> --note "Approved"
uv run agent-kernel run resume <run-id> --approval-id <approval-id>
uv run agent-kernel run events <run-id>
```

Expected approval timeline:

```text
tool_call_requested
policy_evaluated
approval_requested
run_waiting_approval
approval_approved
run_resuming
run_started
tool_call_completed
run_completed
```

## Phase 3 Entry Criteria

Phase 3 can start because:

- Tools have stable contracts.
- Tool execution is schema-validated.
- Tool calls are persisted.
- Policy decisions are explicit.
- Risky tools can pause runs.
- Approval decisions are persisted.
- Approved runs can resume.
- Rejected runs fail safely.
- Safe retries and model fallback are implemented.
- Tool, policy, approval, retry, and fallback events are inspectable.
- Tests prove the full Phase 2 path.

## Next Phase

Phase 3 should focus on:

- Document model.
- Document upload.
- Local object store.
- Ingestion worker.
- Text/Markdown parser.
- Chunker.
- Embedding interface.
- OpenAI embeddings.
- Mock embeddings.
- pgvector store.
- Retriever.
- Citation builder.
- `kb_search` tool.
- Short-term memory.
- Task context.
- User preferences.
- Long-term memory.
- Memory retrieval.

The next major project shift is:

```text
from "agent can safely call tools"
to "agent can use knowledge and memory"
```
