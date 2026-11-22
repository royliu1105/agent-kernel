# Engineering Architecture

Current capability/evidence overview: [Project Overview](project-overview.md).
For a mechanism walkthrough across ten Agent evaluation angles (with diagrams),
see [Architecture through ten perspectives](architecture-ten-perspectives.md).
This page preserves an explicitly labeled v0.1 snapshot below; that snapshot
does not describe current Web, provider or observability acceptance.

## Architecture Decision

Agent Kernel uses:

```text
Monorepo + Modular Monolith + Worker + Pluggable Interfaces
```

This means the project is developed in one repository, with separate applications and clearly bounded internal packages. The backend is not split into microservices for v0.1, but the runtime is organized so modules can later be extracted if needed.

## Runtime Shape

Agent Kernel has four primary process entrypoints:

```text
API process
Worker process
CLI process
Web process
```

The API creates and inspects state. The worker executes queued agent runs. The
current approval-resume path can execute within the API request; it is not yet
uniformly a queued Worker continuation. The CLI is the developer entrypoint.
The Web UI supports live API-backed agent/knowledge-base/run/approval operations.
Its bounded authenticated first-use path has offline CI evidence; the later
anonymous local paid walkthrough is separate evidence, not multi-tenant acceptance.

## v0.1 Release Snapshot

This section records v0.1 history, not current database support. Current mainline
requires PostgreSQL in runtime and tests; see [PostgreSQL-only storage](postgresql-only.md)
and [the current Docker runtime](docker-local.md).

The v0.1 release shape is:

```text
FastAPI API + Typer CLI + polling worker + Next.js Workbench
Postgres/SQLite storage + local object store + deterministic evals
```

Process responsibilities:

- API owns HTTP request handling, validation, and state inspection.
- Worker owns queued run execution, tool execution, approval resume, retry, and fallback paths.
- CLI owns local developer workflows and API-backed commands.
- Web owns the Agent Workbench operator surface.
- At v0.1, Postgres was the production database and SQLite was supported locally.
  Current mainline has removed SQLite support.
- Redis has a queue adapter foundation; default API/worker paths still keep
  scheduling conservative.
- Object storage can use local filesystem storage or S3/MinIO-compatible
  storage through configuration.

Historical v0.1 boundaries (not current limitations):

- Web Workbench data is mostly fixture-backed.
- Web approval decisions are local UI state.
- Automatic model planning for tool choice is deferred.
- OpenTelemetry trace exporter configuration and API Prometheus metrics
  exposition are available. Fine-grained runtime span instrumentation and
  worker HTTP metrics exposure remain later hardening work.

## High-Level Flow

```text
Web / CLI
   |
   v
FastAPI API
   |
   +--> PostgreSQL + pgvector
   +--> Redis
   +--> Object Store
   |
   v
Worker
   |
   v
Agent Runtime
   |
   +--> LLM Providers
   +--> Tools
   +--> Memory
   +--> RAG
   +--> Policy
   +--> Observability
```

## Dependency Direction

The dependency direction is strict:

```text
apps/*
  -> kernel-runtime / kernel-storage / providers / tools
    -> kernel-core
```

Rules:

- `kernel-core` must not import FastAPI, SQLAlchemy, Redis, OpenAI SDK, or app code.
- `kernel-runtime` must not import FastAPI.
- The Web UI must not access the database directly.
- Prefer Worker execution for long-running loops. Current approval resume is
  an API-side exception; do not claim all continuation is durably queued.
- Worker processes execute queued agent runs.
- Storage and provider implementations depend on core interfaces, not the other way around.

## Why Not Microservices in v0.1

Microservices would add service discovery, distributed transactions, cross-service tracing, deployment overhead, version compatibility, and harder local testing. The v0.1 priority is mastering and shipping the agent runtime, not distributed service topology.

## Why Not a Single Unstructured App

The project is still modular. API, worker, CLI, Web, storage, providers, tools, RAG, evals, and observability each have clear boundaries. This gives a simple deployment model without creating a large unstructured application.

## Canonical Repository Shape

```text
agent-kernel/
  apps/
    api/
    worker/
    cli/
    web/

  packages/
    kernel-core/
    kernel-identity/
    kernel-runtime/
    kernel-providers/
    kernel-tools/
    kernel-memory/
    kernel-rag/
    kernel-policy/
    kernel-evals/
    kernel-observability/
    kernel-storage/

  docs/
  examples/
  evals/
  tests/
  deploy/
```

## Deployment Shape

Current default local deployment uses the single `agent-kernel-local` Docker
Compose project, PostgreSQL-only, with persistent data volumes:

```text
postgres
redis
api
worker
web
prometheus / blackbox / grafana
alloy / loki / tempo / alertmanager / mailpit
```

Container build files:

```text
deploy/Dockerfile.python
apps/web/Dockerfile
```

See [Production Configuration](production-config.md) for runtime variables,
secrets, storage, and release-hardening expectations.
See [Docker local operations](docker-local.md) for default Mock startup and
[local paid experience](local-paid-experience.md) for the separately authorized
profile and observed results. Neither profile is a high-availability deployment.
