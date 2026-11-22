# Day 73: Prometheus-Compatible Metrics Endpoint

Goal:

Expose process-local runtime metrics through a Prometheus-compatible API
endpoint so production operators can scrape model, tool, retrieval, token, cost,
and latency signals.

Scope:

- Add Prometheus text exposition rendering for the existing metrics recorder.
- Add an API `/metrics` endpoint.
- Share one API-process metrics recorder between runtime execution, retrieval,
  and the metrics endpoint.
- Keep metric labels low-cardinality and secret-free.
- Update production, architecture, observability, and milestone docs.

Tasks:

- [x] Add Prometheus text formatter for counter and observation points.
- [x] Add `/metrics` API endpoint.
- [x] Wire API-created runtime and retrieval services to the process metrics
  recorder.
- [x] Keep `/metrics` scrapeable when API key auth is enabled.
- [x] Add endpoint and formatter tests.
- [x] Update Day 73 docs and Beta milestone progress.

Acceptance:

- [x] `/metrics` returns `text/plain` Prometheus exposition format.
- [x] Counters render as Prometheus counters.
- [x] Observations render as Prometheus summaries with `_count` and `_sum`.
- [x] Runtime and retrieval metrics can be scraped from the API process.
- [x] `/metrics` emits no raw prompts, document chunks, credentials, or tool
  arguments.
- [x] Production docs describe scrape and network exposure expectations.

Verification:

- [x] `uv run pytest tests/unit/test_observability.py tests/unit/test_api_health.py tests/unit/test_api_auth.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`
- [x] `git diff --check`

Notes:

- Day 73 exposes per-process in-memory metrics. Production Prometheus should
  scrape every API instance and aggregate across instances.
- Worker metrics are still process-local and not exposed over HTTP by the worker
  binary. A worker metrics listener remains later hardening work.
