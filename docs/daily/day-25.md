# Day 25: Trace and Correlation Foundation

## Goal

Start Phase 4 by making every persisted run traceable and every runtime event
correlatable.

Day 25 should establish this observability baseline:

```text
run creation -> trace_id -> events/tool calls/approvals -> API visibility -> tests
```

## Scope

Day 25 should cover:

- Trace ID generation.
- Span ID generation helper.
- Shared observability context model.
- Structured log context helper.
- Persisted run `trace_id` at creation time.
- Initial run event `trace_id`.
- Subsequent run event correlation through the existing repository paths.
- Tool call and approval trace propagation through existing repository paths.
- API response visibility through existing schemas.
- Unit and integration tests for trace propagation.
- Observability spec update.

Day 25 should not cover:

- Full OpenTelemetry exporter setup.
- Full structlog application wiring.
- Prometheus metrics endpoint.
- Grafana/Jaeger/Tempo/Loki stack.
- Cost pricing tables.
- Eval dataset runner.
- Persisted eval runs.
- Web UI timeline changes.

## Tasks

- [x] Check current git status.
- [x] Read Phase 4 plan and observability spec.
- [x] Create Day 25 daily plan.
- [x] Add observability trace/context helpers.
- [x] Generate trace IDs for new runs.
- [x] Ensure initial and subsequent events share the run trace ID.
- [x] Ensure tool calls and approvals inherit the run trace ID.
- [x] Add tests for trace ID format and propagation.
- [x] Update observability spec and daily index.
- [x] Run focused tests.
- [x] Run quality checks.

## Acceptance

- [x] New runs always have a non-empty trace ID.
- [x] The initial `run_created` event has the same trace ID as the run.
- [x] Runtime transition events keep the same trace ID.
- [x] Tool calls and approvals keep the same trace ID as the run.
- [x] Existing API run/event responses expose the trace ID.
- [x] The observability helper has deterministic tests for ID shape and context output.
- [x] Day 25 does not add metrics backend, tracing exporter, or eval platform scope.

## Verification

Run:

```bash
uv run pytest tests/unit/test_observability.py tests/unit/test_storage_repositories.py tests/unit/test_runtime_execution.py tests/unit/test_approval_repository.py tests/integration/test_api_run_lifecycle.py
uv run ruff check .
uv run mypy .
git diff --check
```

## Notes

- Use a 32-character lowercase hex trace ID so it can map cleanly to the
  OpenTelemetry trace ID shape later.
- Use a 16-character lowercase hex span ID helper for future step/tool spans.
- Keep payloads out of trace IDs and log context helpers.
- Keep dependency additions deferred unless the code needs them immediately.

## Completion Notes

- Added trace/span ID helpers and `ObservabilityContext`.
- Added safe structured log field helper.
- New runs now receive a generated 32-character lowercase hex `trace_id`.
- Initial and subsequent run events inherit the run trace ID.
- Existing tool call and approval repository paths inherit the run trace ID.
- API run/event responses now expose non-empty trace IDs through existing schemas.
- Updated the observability spec with the Day 25 baseline.
- Kept OpenTelemetry exporters, structlog app wiring, metrics backend, eval platform,
  and UI timeline work deferred.

Verification passed:

- `uv run pytest tests/unit/test_observability.py tests/unit/test_storage_repositories.py tests/unit/test_runtime_execution.py tests/unit/test_approval_repository.py tests/integration/test_api_run_lifecycle.py`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`
- `git diff --check`
