# Phase 4 Summary: Observability and Evals

## Status

Phase 4 is complete as a production-grade foundation:

```text
Day 25-29: Observability and Evals
```

Phase 4 delivered traceability, structured logs, runtime metrics, retrieval
metrics, deterministic eval datasets, JSON eval reports, and a cheap CI eval.

## What Users Can Do Now

Developers can create and execute runs with stable trace IDs, inspect correlated
run events, capture structured runtime logs, collect in-process metrics for
model/tool/retrieval behavior, and run deterministic RAG evals locally or in CI.

Current user-facing shape:

```text
Run observability:
run -> trace_id -> events/tool calls/approvals -> structured logs

Runtime metrics:
model/tool/retrieval operation -> latency/tokens/cost/count metrics

Eval workflow:
JSON dataset -> agent-kernel eval report -> JSON report -> CI cheap eval
```

## Completed Capabilities

- Trace ID generation for every run.
- Span ID helper for future spans.
- Observability context model.
- Structured log field builder.
- Sensitive log field redaction.
- JSON log formatter.
- Runtime logs for run start, model success, retries, fallback, tool request,
  tool success, approval request, and run failure.
- Monotonic latency timer.
- Metrics recorder protocol.
- No-op metrics recorder.
- In-memory metrics recorder.
- Model call count and latency metrics.
- Model input/output/total token metrics.
- Model estimated cost metric.
- Tool call count and latency metrics.
- Tool call failure metrics.
- Persisted tool call latency for success and failure paths.
- Retrieval count, latency, result count, and failure metrics.
- JSON RAG eval dataset loader.
- Deterministic RAG eval runner from file-backed datasets.
- Eval report serialization to JSON-compatible dictionaries.
- CLI eval report command.
- Cheap deterministic eval fixture.
- Makefile cheap eval target.
- GitHub Actions cheap eval step.

## CLI Surface

```bash
agent-kernel eval report evals/rag-smoke.json
agent-kernel eval report evals/rag-smoke.json --no-fail-on-failure
```

Default behavior:

- Prints a JSON report.
- Exits with code `0` when the report passes.
- Exits with code `1` when the report fails.

## Test Coverage

Phase 4 added coverage for:

- Trace ID format and propagation.
- Observability context log fields.
- Structured log redaction.
- JSON log formatting.
- Runtime log correlation.
- Latency timer behavior.
- In-memory metrics recorder behavior.
- Model metrics.
- Tool metrics and persisted tool latency.
- Retrieval metrics.
- RAG eval dataset loading.
- RAG eval dataset validation failures.
- Eval report serialization.
- CLI eval report success and failure behavior.

## Known Limitations

These limitations are intentional for Phase 4:

- OpenTelemetry exporters are not implemented yet.
- Global application logging configuration is not implemented yet.
- Prometheus endpoint is not implemented yet.
- Metrics are not persisted to metric tables.
- Full `RunStep` persistence is not implemented yet.
- Not every logical step has persisted latency data yet.
- Cost tracking covers model usage totals and metrics, but not pricing tables,
  budgets, or per-user/project cost policy.
- Eval runs are not persisted yet.
- Eval API endpoints are not implemented yet.
- Eval CLI currently supports deterministic local RAG eval reports, not full
  agent behavior evals.
- YAML eval datasets are not implemented yet.
- LLM-as-judge is intentionally excluded from default CI.
- Web UI eval reports are deferred to Phase 5.

## Closure Verification

Day 29 verification:

```bash
uv run pytest tests/unit/test_rag_evals.py tests/unit/test_cli_commands.py
uv run agent-kernel eval report evals/rag-smoke.json
uv run ruff check .
uv run mypy .
uv run pytest
git diff --check
```

## Next Phase

Phase 5 starts on Day 30:

```text
Web UI
```

The next focus is making completed backend capabilities visible and usable:

- Dashboard.
- Agents page.
- Run timeline.
- Tool call detail.
- Approval inbox.
- Knowledge base page.
- Eval report page.
- Settings.
- Web smoke tests.
