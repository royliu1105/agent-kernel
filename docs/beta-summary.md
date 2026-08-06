# Beta Summary: Day 52-75

## Status

Beta production hardening is complete under the Day 52-75 scope:

```text
Make Agent Kernel credible for internal production pilots and serious extension
by other developers.
```

Beta does not mean v1.0 stability. It means the project now has the core
production-shaped runtime, storage, security, observability, eval, and operator
surfaces required for serious self-hosted pilot feedback.

## Completion Statement

The Beta milestone is complete with explicit boundaries:

- The runtime keeps durable state in the database.
- Workers can process queued runs, persist timeline events, recover stuck
  leases, and expose retry/fallback history.
- Redis exists as a queue adapter foundation and coordination port, while the
  default worker loop remains database-first.
- Provider-native OpenAI-style tool calls can be parsed, persisted, executed,
  and covered by deterministic evals.
- Auth, RBAC, workspace scope, approval authorization, and API-key
  authentication are implemented and tested.
- RAG can use OpenAI embeddings and pgvector-backed similarity search while
  preserving SQLite-compatible local development.
- Documents can use local object storage or S3-compatible object storage such
  as MinIO.
- OpenTelemetry trace exporters and a Prometheus-compatible metrics endpoint
  are available through configuration.
- Eval reports can be persisted, queried through API, published from the CLI,
  and inspected in the Web Workbench.
- CI now includes migration smoke checks for SQLite and Postgres/pgvector.

## What Users Can Do Now

Self-hosted pilot users and contributors can:

- Run Agent Kernel locally through SQLite or the Docker Compose stack.
- Use API-key authentication and route-level permissions.
- Scope agents, runs, and approvals to workspaces.
- Create agent runs and process them with the worker.
- Inspect persisted run events, retry/fallback events, tool calls, approvals,
  knowledge base state, memory state, metrics, and eval runs.
- Use provider-native tool-call execution with OpenAI-compatible responses.
- Ingest documents into configurable object storage.
- Index and retrieve knowledge with OpenAI embeddings and pgvector.
- Export traces through OpenTelemetry when SDK dependencies and environment
  variables are configured.
- Scrape `/metrics` with Prometheus or a compatible collector.
- Publish deterministic eval reports through the CLI and inspect them in the
  Web Workbench.

## Completed Beta Work

Identity and security:

- Identity, workspace, role, permission, and API-key domain models.
- Identity persistence and API-key hash storage.
- API-key authentication middleware.
- Route-level authorization enforcement.
- Approval authorization and workspace ownership checks.
- Auth/RBAC documentation and security test matrix.

Durable execution:

- Worker leases and persisted lease records.
- Stuck-run detection and conservative recovery.
- Worker restart regression tests.
- Retry and fallback visibility in persisted run timelines.
- Redis queue adapter foundation using run ids only.

Provider-native tool calling:

- Provider-neutral native tool-call contract.
- OpenAI native tool-call parsing.
- Persisted provider-native tool-call metadata.
- Durable model/tool/model runtime loop.
- Deterministic provider-native behavior evals.

RAG and storage:

- OpenAI embedding provider.
- pgvector-native vector store path.
- S3/MinIO-compatible object storage backend.
- Production RAG/storage integration coverage.
- SQLite-compatible JSON-vector fallback remains available.

Observability:

- OpenTelemetry exporter configuration.
- Idempotent OpenTelemetry setup helper.
- Prometheus-compatible `/metrics` endpoint.
- Runtime counters and latency observations.

Evals and Web:

- Persisted eval run domain, storage model, repository, and migration.
- Eval run create/list/get API.
- CLI `eval report --publish`.
- Live Web Workbench eval run list/detail path.
- Web smoke coverage for live eval report rendering.

Migration hardening:

- SQLite migration regression coverage upgrades a fresh database to Alembic head.
- GitHub CI runs SQLite migration smoke.
- GitHub CI runs Postgres/pgvector migration smoke.
- PostgreSQL-only pgvector migration remains guarded on SQLite.

## Verification

Day 75 local verification should cover:

```bash
uv run pytest tests/unit/test_migrations.py
uv run ruff check .
uv run mypy .
uv run pytest
npm --prefix apps/web run lint
npm --prefix apps/web run test:e2e
docker compose config
git diff --check
```

GitHub CI should be checked after the closure commit is pushed because the
Postgres/pgvector migration smoke runs in the remote Python job.

## Known Remaining Limitations

These limitations are acceptable for Beta and should be handled during the
Day 76-90 v1.0 release candidate track:

- Redis is not yet the default worker scheduling path.
- Worker lease claiming is not yet the default polling mechanism.
- Stuck-run recovery fails expired in-flight runs conservatively instead of
  automatically replaying them.
- Eval runs persist submitted reports; the server does not yet schedule remote
  eval jobs, upload eval datasets, or run LLM-as-judge suites.
- Web Workbench covers core operator workflows, but it is not a complete admin
  console.
- Auth/RBAC is suitable for self-hosted pilots, not public hosted SaaS.
- OpenTelemetry configuration exists, but production deployments still need
  collector, retention, dashboard, and alerting choices.
- Backup, restore, upgrade, compatibility, and hardening docs are still v1.0 RC
  work.

## v1.0 RC Handoff

Day 76-90 should focus on freezing and proving the production contract:

- Public API and CLI compatibility policy.
- Upgrade and migration policy.
- Backup and restore guidance.
- Security hardening checklist.
- Load and soak test scenarios.
- Release-blocking eval gates.
- Clean-machine release rehearsal.
- v1.0 release notes and final release checklist.
