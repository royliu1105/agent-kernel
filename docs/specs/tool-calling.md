# Feature Spec: Tool Calling

## Goal

Allow agents to request execution of registered tools through validated schemas, permission checks, persisted tool calls, and observable execution.

## Non-Goals

- Plugin marketplace.
- Arbitrary shell tool in the default install.
- Unbounded parallel tool execution.
- Remote tool distribution protocol in v0.1.

## User Stories

- As a developer, I can register a tool with a schema and risk level.
- As an agent, I can request a tool call through the model provider's tool calling mechanism.
- As an operator, I can inspect tool arguments, result, status, latency, and approval state.
- As a security reviewer, I can block or require approval for risky tools.

## Domain Model

Initial entities:

- `Tool`
- `ToolCall`
- `ToolResult`
- `ToolRegistry`
- `ToolExecutor`

Tool metadata:

```text
name
description
input_schema
output_schema
risk_level
timeout_ms
enabled
```

Day 8 tool package baseline:

- `ToolMetadata`
- `ToolRequest`
- `ToolResult`
- `Tool`
- `ToolRegistry`
- `ToolExecutor`
- `ToolError`
- `EchoTool`

Day 8 execution contract:

- Tools implement an async `execute(arguments)` method.
- Tool metadata carries JSON input schema, optional output schema, risk level, timeout, and enabled
  state.
- `ToolRegistry` owns in-memory registration and lookup.
- Duplicate registration fails with `duplicate_tool`.
- Unknown lookup or execution fails with `unknown_tool`.
- `ToolExecutor` validates arguments with JSON Schema before calling the tool.
- Invalid arguments fail with `invalid_tool_arguments` and the tool is not executed.
- Tool exceptions are converted to `tool_execution_failed`.
- Tool timeout is converted to `tool_timeout`.
- Tool output must be a JSON object.
- Tool output must be JSON serializable.
- Tool output has a serialized size limit.
- The first built-in tool is `EchoTool`, a deterministic `read_only` tool.

Deferred from Day 8:

- Provider-native tool/function calling.
- Agent run loop integration.
- Persisted `ToolCall` records.
- Timeline events for tool calls.
- Policy engine decisions.
- Human approval.
- Retry/fallback.
- Network, shell, filesystem write, or other side-effecting tools.

Day 9 policy-aware execution:

- `PolicyAwareToolExecutor` evaluates policy before `ToolExecutor`.
- Allowed tools continue to schema validation and execution.
- Denied tools fail before execution.
- Approval-required tools fail before execution until approval persistence exists.
- Policy decisions are currently in-memory and typed; persistence and audit events are deferred.

## State Transitions

Initial tool call states:

```text
requested -> policy_checked -> running -> succeeded
requested -> policy_checked -> waiting_approval
requested -> policy_checked -> denied
running -> failed
running -> timed_out
```

Detailed transition rules will be completed during Phase 2 implementation.

## API / CLI

Expected API:

```http
GET   /v1/tools
POST  /v1/tools
GET   /v1/tools/{tool_name}
PATCH /v1/tools/{tool_name}
```

Tool calls are inspected through run detail and run events.

## Failure Modes

- Unknown tool requested.
- Invalid arguments.
- Tool times out.
- Tool raises an error.
- Tool output is too large.
- Tool output is not JSON serializable.
- Tool output is not a JSON object.
- Tool requires approval.
- Tool is denied by policy.
- Approval-required tool is requested before approval persistence exists.

## Security

- Tool arguments must be schema validated.
- Tool outputs should be size-limited.
- Risky tools require policy evaluation.
- Dangerous side effects require approval.
- Secrets must be redacted from logs and traces.

## Observability

- Tool call span.
- Tool latency.
- Tool status.
- Tool risk level.
- Error type.
- Approval linkage when applicable.

## Test Plan

- Valid tool call succeeds.
- Invalid args fail before execution.
- Unknown tool fails safely.
- Duplicate tool registration fails safely.
- Tool errors are converted to typed execution errors.
- Tool timeout is recorded as a typed execution error.
- Tool result size limit is enforced.
- Risky tool pauses for approval.
- Denied tool is not executed.
- Approval-required tool is not executed.
- Tool timeout is recorded.
- Tool error is persisted.

## Acceptance Criteria

- Agent can call at least one safe built-in tool.
- Tool calls are persisted and visible in the run timeline.
- Policy can require approval before execution.
- Tool failures are observable and test-covered.
