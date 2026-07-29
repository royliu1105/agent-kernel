# Feature Spec: Observability

## Goal

Agent Kernel must make every agent run inspectable, debuggable, measurable, and cost-aware from v0.1.

The MVP observability stack is:

```text
OpenTelemetry + structlog + Postgres run/step/cost summary
```

Later enhancements may add:

```text
Prometheus + Grafana + Tempo/Jaeger + Loki/ClickHouse
```

## Non-Goals

MVP does not include:

- A full Grafana dashboard.
- A production log aggregation stack.
- Alerting rules.
- Distributed tracing across many services.
- Long-term analytics warehouse.
- Per-user or per-project budget enforcement.

The MVP must still emit data in a shape that can support those later.

## User Stories

- As a developer, I can inspect a run timeline and understand what happened at each step.
- As an operator, I can see where time was spent: model call, tool call, retrieval, approval wait, or memory write.
- As a maintainer, I can correlate logs with a specific run, step, tool call, and trace.
- As a user, I can see token usage and estimated cost for a run.
- As an evaluator, I can compare latency, cost, and failures across regression eval runs.

## Domain Model

Observability is attached to existing runtime entities:

- `Run`
- `RunStep`
- `Message`
- `ToolCall`
- `Approval`
- `Document`
- `EvalRun`

Required persisted fields:

```text
Run:
  trace_id
  status
  started_at
  ended_at
  latency_ms
  input_tokens_total
  output_tokens_total
  estimated_cost_total
  error_type
  error_message

RunStep:
  trace_id
  span_id
  type
  status
  started_at
  ended_at
  latency_ms
  input_tokens
  output_tokens
  estimated_cost
  error_type
  error_message

ToolCall:
  trace_id
  span_id
  tool_name
  status
  risk_level
  requires_approval
  started_at
  ended_at
  latency_ms
  error_type
  error_message

Approval:
  trace_id
  requested_at
  resolved_at
  wait_ms
  decision
```

## Trace Design

Every run has one root trace.

## Day 25 Trace and Correlation Foundation

Day 25 implements the first observability foundation:

- Generate a 32-character lowercase hex `trace_id` for every new run.
- Generate a 16-character lowercase hex `span_id` helper for future spans.
- Add a reusable `ObservabilityContext` for run, agent, step, tool call,
  approval, and eval correlation fields.
- Add a structured log field helper that only accepts safe scalar fields.
- Persist the run `trace_id` at creation time.
- Persist the initial `run_created` event with the same `trace_id`.
- Propagate the run `trace_id` through existing transition events.
- Propagate the run `trace_id` through existing tool call and approval paths.
- Expose trace IDs through the existing run, event, and approval API responses.

Day 25 intentionally does not implement full OpenTelemetry exporter setup,
structlog application wiring, Prometheus metrics, cost pricing tables, eval
datasets, persisted eval runs, or Web UI timeline changes.

Recommended span hierarchy:

```text
agent.run
  agent.step
    llm.model_call
    tool.call
    rag.retrieve
    memory.read
    memory.write
    policy.evaluate
    approval.wait
```

Required span attributes:

```text
run.id
agent.id
step.id
step.type
step.status
provider.name
model.name
tool.name
tool.risk_level
approval.id
document.id
eval_run.id
error.type
cost.estimated
tokens.input
tokens.output
tokens.total
```

Sensitive inputs, secrets, and large payloads must not be emitted as span attributes.

## Structured Logging

Use `structlog` for structured logs.

## Day 26 Structured Runtime Logs

Day 26 implements the first structured logging baseline:

- Add a structured log record builder.
- Add sensitive field redaction for common credential names.
- Preserve token usage fields such as `input_tokens`, `output_tokens`, and
  `total_tokens` as non-sensitive metrics.
- Add a JSON log formatter for one-object-per-line structured logs.
- Emit runtime logs for run start, model call success, provider retry, model
  fallback selection, tool call request, tool retry, tool call success, approval
  request, and run failure.
- Include trace/run/agent correlation fields whenever a run is available.
- Include tool call and approval IDs for tool and approval logs.
- Include provider, model, token, and estimated cost fields for model success
  logs.

Day 26 intentionally does not implement global application logging
configuration, full structlog application wiring, OpenTelemetry exporters,
Prometheus metrics, log aggregation, latency persistence, eval platform work, or
Web UI timeline changes.

Every runtime log line should include available correlation fields:

```text
trace_id
span_id
run_id
agent_id
step_id
tool_call_id
approval_id
document_id
eval_run_id
provider
model
tool_name
status
error_type
```

Log levels:

```text
debug:
  internal planning details, only when enabled

info:
  run created, step started, model call finished, tool call finished, approval requested

warning:
  retry, fallback, policy warning, redaction, degraded retrieval

error:
  failed step, provider error, tool failure, ingestion failure
```

Secrets and credentials must be redacted before logging.

## Metrics

MVP metrics:

```text
agent_runs_total
agent_run_success_total
agent_run_failure_total
agent_run_latency_ms
agent_steps_total
agent_step_latency_ms
llm_model_calls_total
llm_model_call_latency_ms
llm_tokens_input_total
llm_tokens_output_total
llm_estimated_cost_total
tool_calls_total
tool_call_failure_total
tool_call_latency_ms
rag_retrievals_total
rag_retrieval_latency_ms
approval_requests_total
approval_wait_ms
memory_reads_total
memory_writes_total
eval_runs_total
eval_case_failures_total
```

Recommended labels:

```text
agent_id
project_id
provider
model
tool_name
step_type
status
error_type
```

Avoid high-cardinality labels such as raw prompt text, user input, document chunk content, or tool arguments.

## Cost Tracking

Cost tracking is a first-class observability concern.

Record per model call:

```text
provider
model
input_tokens
output_tokens
total_tokens
estimated_cost
pricing_version
run_id
step_id
```

Persist aggregate cost on:

- `Run`
- `RunStep`
- `EvalRun`

Cost data is used by:

- Run detail UI.
- Eval reports.
- Regression checks.
- Future budget policy.

## API / CLI

MVP API surfaces:

```http
GET /v1/runs/{run_id}
GET /v1/runs/{run_id}/events
GET /v1/evals/runs/{eval_run_id}
```

MVP CLI surfaces:

```bash
agent-kernel run watch <run-id>
agent-kernel run inspect <run-id>
agent-kernel eval report <eval-run-id>
```

## Web UI

MVP UI should show:

- Run status.
- Run timeline.
- Step latency.
- Model calls.
- Tool calls.
- Retrieval calls.
- Approval wait time.
- Errors and retries.
- Input/output token totals.
- Estimated cost.

Later UI enhancements:

- Trace waterfall.
- Metrics dashboard.
- Cost dashboard.
- Eval trend charts.
- Provider reliability dashboard.

## Failure Modes

Observability failures must not break agent execution.

Rules:

- If trace export fails, continue the run and log a warning.
- If metrics export fails, continue the run and log a warning.
- If cost calculation fails, persist token counts and mark estimated cost as unavailable.
- If logs contain secrets, redaction must happen before emission.
- If an observed payload is too large, store a truncated summary and optionally link to an artifact.

## Security

Do not log or trace:

- API keys.
- OAuth tokens.
- Secrets.
- Raw credentials.
- Full private documents.
- Full retrieved chunks by default.
- Full tool output when it may contain sensitive data.

Allowed:

- Stable IDs.
- Sizes.
- Counts.
- Hashes.
- Redacted summaries.
- Error categories.

## Test Plan

Unit tests:

- Trace context creation.
- Structured log field injection.
- Cost calculation.
- Secret redaction.
- Metric label validation.

Integration tests:

- Create run and verify persisted `trace_id`.
- Execute model call and verify token/cost summary.
- Execute tool call and verify latency/status summary.
- Approval pause/resume records approval wait time.
- Failed step records error type and message.

Behavior eval tests:

- Eval report includes cost and latency summary.
- Regression eval can fail on maximum cost or maximum step count.

## Acceptance Criteria

v0.1 is acceptable when:

- Every run has a `trace_id`.
- Every persisted step has timing data.
- Model calls record token and estimated cost data.
- Tool calls record status, risk level, and latency.
- Approval waits record wait duration.
- Logs can be correlated by `run_id` and `trace_id`.
- Runtime emits OpenTelemetry spans.
- Observability failures do not fail the run.
