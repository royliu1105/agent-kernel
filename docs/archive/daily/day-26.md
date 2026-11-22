# Day 26: Structured Runtime Logs

## Goal

Add structured runtime logs that can be correlated with run traces, tool calls,
approvals, providers, models, statuses, and errors.

Day 26 should establish this observability baseline:

```text
runtime action -> structured log event -> trace/run correlation -> redacted fields -> tests
```

## Scope

Day 26 should cover:

- Structured log record builder.
- Safe scalar log fields only.
- Sensitive field redaction for common credential names.
- JSON log formatter for later app/server wiring.
- Runtime logs for run start, model success, provider retry, fallback, tool
  request, approval request, tool success, and run failure.
- Tests for log field construction, redaction, formatter output, and runtime
  correlation.
- Observability spec update.

Day 26 should not cover:

- Full OpenTelemetry exporter setup.
- Global application logging configuration.
- Log aggregation stack.
- Prometheus metrics.
- Latency persistence.
- Cost pricing tables.
- Eval platform implementation.
- Web UI timeline changes.

## Tasks

- [x] Check current git status.
- [x] Read Phase 4 plan and observability spec.
- [x] Create Day 26 daily plan.
- [x] Add structured log record helpers.
- [x] Add sensitive field redaction.
- [x] Add JSON log formatter.
- [x] Emit runtime structured logs on key execution paths.
- [x] Add observability helper tests.
- [x] Add runtime log correlation tests.
- [x] Update observability spec and daily index.
- [x] Run focused tests.
- [x] Run quality checks.

## Acceptance

- [x] Runtime logs include `trace_id` and `run_id` when a run is available.
- [x] Model success logs include provider, model, token, and estimated cost fields.
- [x] Tool logs include tool call ID and tool name.
- [x] Approval logs include approval ID and tool call ID.
- [x] Failure logs include error type but do not include raw prompts or secrets.
- [x] JSON formatter outputs a parseable structured JSON log line.
- [x] Day 26 does not add metrics backend, tracing exporter, or eval platform scope.

## Verification

Run:

```bash
uv run pytest tests/unit/test_observability.py tests/unit/test_runtime_execution.py
uv run ruff check .
uv run mypy .
git diff --check
```

## Notes

- Keep logs useful without logging raw prompt text, tool arguments, document
  chunks, credentials, or secrets.
- Treat current structured logs as the stable app-facing contract. Future
  structlog/OpenTelemetry wiring should adapt these fields rather than invent
  a new shape.

## Completion Notes

- Added structured log record building in `kernel_observability`.
- Added sensitive field redaction for common credential names.
- Kept token usage fields unredacted for observability metrics.
- Added a JSON log formatter for structured log lines.
- Added runtime logs for run start, model success, provider retry, fallback,
  tool request, tool retry, tool success, approval request, and run failure.
- Added tests for log records, redaction, JSON formatting, emitted log payloads,
  and runtime correlation.
- Updated the observability spec and Phase 4 milestone progress.
- Kept OpenTelemetry exporters, global logging configuration, metrics backend,
  eval platform, latency persistence, and UI timeline work deferred.

Verification passed:

- `uv run pytest tests/unit/test_observability.py tests/unit/test_runtime_execution.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `git diff --check`
