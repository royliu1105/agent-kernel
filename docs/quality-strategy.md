# Quality Strategy

## Quality Principle

Agent Kernel must be deployable, testable, observable, maintainable, and recoverable from the first version. Production-grade thinking is not deferred to the end.

## Required Test Layers

### Unit Tests

Cover:

- Provider abstraction.
- Tool schema validation.
- Tool permission policy.
- Agent state transitions.
- Retry/fallback behavior.
- Prompt rendering.
- Memory retrieval.
- Chunking.
- Cost calculation.

### Integration Tests

Cover:

- Create agent -> create run -> worker executes -> inspect result.
- RAG ingestion -> retrieval -> cited answer.
- Risky tool call -> approval request -> approve -> resume.
- Tool failure -> retry -> fallback.
- Deterministic mock LLM transcript replay.

### Behavior Evals

Eval cases should check:

- Expected tool calls.
- Forbidden tool calls.
- Required citations.
- Final answer properties.
- Maximum cost.
- Maximum step count.
- Regression behavior.

## Eval System

MVP:

- YAML or JSONL dataset format.
- Eval runner.
- Deterministic assertions.
- Mock provider replay.
- Regression report.
- Cheap evals in CI.

Later:

- LLM-as-judge.
- Pairwise regression comparison.
- Golden trace replay.
- Prompt version A/B.
- Security red-team evals.

## Observability

MVP:

- Every run has a trace ID.
- Every step has a span.
- Model call, tool call, retrieval, approval, and memory write emit spans.
- Structured logs include run ID, agent ID, step ID, and trace ID.
- Metrics include run count, success/failure, latency, model latency, tool latency, token usage, cost, and approval wait time.
- Run-level cost and latency summaries are persisted.

Later:

- Grafana dashboard.
- Jaeger or Tempo trace UI.
- Prometheus metrics.
- Alerting rules.
- Per-user and per-project budgets.

## Security

MVP:

- API key auth.
- User/admin/service roles.
- Tool risk levels.
- Allow/deny/require-approval policy.
- Tool input/output validation.
- Tool timeout.
- Tool result size limit.
- Secret redaction in logs and traces.
- Prompt injection warning baseline for retrieved content.
- Human approval for dangerous tools.
- Audit log for approvals and tool calls.
- No arbitrary shell tool in the default install.

Later:

- OPA/Rego policy.
- OAuth/OIDC.
- SSO.
- Fine-grained resource permissions.
- Container isolation.
- Signed tool manifests.
- Secret manager integration.
- Tenant isolation.

## CI Quality Gate

Every PR should pass:

```bash
ruff check .
mypy .
pytest
npm run lint
npm run build
```

Behavior evals should start cheap and deterministic, then later add scheduled real-model smoke evals.

## Release Candidate Gates

Before claiming v1.0 release-candidate readiness, maintainers should run:

```bash
make release-eval
make release-smoke
```

`make release-eval` is the release-blocking behavior eval gate. It covers the
deterministic RAG smoke dataset, the release RAG gate dataset, and
provider-native tool-call regression cases.

`make release-smoke` is the critical-path product smoke gate. It includes
release evals, Docker Compose config validation, selected API/CLI/worker/RAG/
memory/approval/tool/eval tests, and Web lint/build checks.

Load tests, soak tests, browser e2e tests, clean-machine rehearsals, live
provider tests, and infrastructure-backed pgvector/S3 checks remain separate
release work because they have different runtime, credential, and flake
profiles.
