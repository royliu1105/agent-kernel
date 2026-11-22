# Day 72: OpenTelemetry Exporter Configuration

Goal:

Add production-ready OpenTelemetry exporter configuration without making
OpenTelemetry SDK packages mandatory for local development and default CI.

Scope:

- Add environment-driven OpenTelemetry trace exporter configuration.
- Keep OpenTelemetry disabled by default.
- Support OTLP/HTTP and console trace exporters.
- Wire API and worker startup paths through the shared configuration helper.
- Document deployment environment variables and current observability boundaries.

Tasks:

- [x] Add OpenTelemetry configuration model and environment parsing.
- [x] Add idempotent OpenTelemetry setup helper.
- [x] Support `otlp-http` and `console` exporters.
- [x] Keep missing OpenTelemetry SDK dependencies as a clear runtime error only
  when telemetry is enabled.
- [x] Wire API and worker startup paths.
- [x] Add observability unit tests.
- [x] Update production and observability docs.
- [x] Update Beta milestone progress.

Acceptance:

- [x] OpenTelemetry remains disabled by default.
- [x] `AGENT_KERNEL_OTEL_ENABLED=true` enables exporter setup.
- [x] `AGENT_KERNEL_OTEL_EXPORTER=otlp-http` exports traces through an
  OTLP/HTTP endpoint.
- [x] `AGENT_KERNEL_OTEL_EXPORTER=console` supports local exporter inspection.
- [x] Repeated setup calls are idempotent.
- [x] Missing SDK dependencies produce a clear configuration error.

Verification:

- [x] `uv run pytest tests/unit/test_observability.py`
- [x] `uv run pytest tests/unit/test_api_health.py tests/unit/test_worker_cli.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`
- [x] `git diff --check`

Notes:

- Day 72 configures the OpenTelemetry provider and span exporter. It does not
  yet add fine-grained span instrumentation around every runtime operation.
- Day 73 remains focused on the Prometheus-compatible metrics endpoint.
