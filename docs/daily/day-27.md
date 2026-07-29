# Day 27: Latency and Metrics Foundation

## Goal

Add a small metrics and latency foundation so runtime model/tool execution can be
measured without committing to a production metrics backend yet.

Day 27 should establish this observability baseline:

```text
runtime operation -> latency measurement -> metrics recorder -> logs/events/tests
```

## Scope

Day 27 should cover:

- Monotonic latency measurement helper.
- Metrics recorder protocol.
- No-op metrics recorder for default runtime behavior.
- In-memory metrics recorder for tests and local inspection.
- Model call latency measurement.
- Model call token and estimated cost metrics.
- Tool call latency measurement.
- Persisted tool call `latency_ms` for successful and failed tool calls.
- Runtime structured logs with `latency_ms`.
- Runtime tests for model/tool metrics and tool latency persistence.
- Observability spec update.

Day 27 should not cover:

- Prometheus endpoint.
- OpenTelemetry metrics exporter.
- Grafana dashboard.
- Persisted metric tables.
- Full `RunStep` repository and step persistence.
- Retrieval metrics.
- Eval platform implementation.
- Web UI metric views.

## Tasks

- [x] Check current git status.
- [x] Read Phase 4 plan and observability spec.
- [x] Create Day 27 daily plan.
- [x] Add monotonic latency helper.
- [x] Add metrics recorder protocol and in-memory implementation.
- [x] Record model call metrics.
- [x] Record tool call metrics.
- [x] Persist tool call latency.
- [x] Include latency fields in structured runtime logs.
- [x] Add observability helper tests.
- [x] Add runtime metrics and latency tests.
- [x] Update observability spec, daily index, and milestones.
- [x] Run focused tests.
- [x] Run quality checks.

## Acceptance

- [x] Model success records call count, latency, input tokens, output tokens,
  total tokens, and estimated cost metrics.
- [x] Tool success records call count and latency metrics.
- [x] Tool failure records failure count and latency metrics.
- [x] Successful tool calls persist `latency_ms`.
- [x] Failed tool calls persist `latency_ms`.
- [x] Structured model/tool logs include `latency_ms`.
- [x] Default runtime still works without configuring a metrics backend.
- [x] Day 27 does not add Prometheus, OTel exporters, persisted metric tables, or
  full RunStep persistence.

## Verification

Run:

```bash
uv run pytest tests/unit/test_observability.py tests/unit/test_runtime_execution.py tests/unit/test_tool_call_repository.py
uv run ruff check .
uv run mypy .
git diff --check
```

## Notes

- Use monotonic clocks for elapsed time.
- Keep metrics labels low-cardinality: provider, model, tool name, status, and
  error type only.
- Keep the in-memory recorder deterministic and test-friendly.

## Completion Notes

- Added `LatencyTimer`.
- Added `MetricsRecorder`, `NoOpMetricsRecorder`, and `InMemoryMetricsRecorder`.
- Recorded model call count, latency, input token, output token, total token, and
  estimated cost metrics.
- Recorded tool call count, tool call failure count, and tool latency metrics.
- Persisted `ToolCall.latency_ms` for successful and failed tool calls.
- Added `latency_ms` to model/tool structured logs.
- Added tests for metrics normalization, recorder behavior, model metrics, tool
  metrics, and persisted tool latency.
- Updated observability spec and Phase 4 milestone progress.
- Kept Prometheus endpoints, OTel metrics exporters, persisted metric tables,
  retrieval metrics, eval platform, Web UI views, and full RunStep persistence
  deferred.

Verification passed:

- `uv run pytest tests/unit/test_observability.py tests/unit/test_runtime_execution.py tests/unit/test_tool_call_repository.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `git diff --check`
