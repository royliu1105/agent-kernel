# Technology Stack

## Current Stack

Updated 2026-11-15. This is the implemented stack, not the original MVP wishlist.
See [Project Overview](project-overview.md) for evidence and acceptance limits.

Use Python for the Agent runtime and TypeScript for the Web UI:

```text
Python Agent Runtime + FastAPI API + Typer CLI + Worker
Next.js + TypeScript Web UI
PostgreSQL + pgvector + Redis
Docker Compose + GitHub Actions
```

## Backend

Implemented backend/toolchain:

- Python 3.12 (`>=3.12,<3.13` in the current workspace).
- uv workspace and lockfile.
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- Typer
- pytest
- ruff
- mypy
- OpenTelemetry
- structlog

## LLM Providers

Implemented adapters:

- OpenAI provider.
- DeepSeek provider (the local walkthrough uses `deepseek-flash`).
- Mock provider.
- Replay provider.

OpenAI and Alibaba DashScope embedding adapters support the selected RAG
profiles. The local walkthrough uses DashScope `text-embedding-v3`, Beijing,
1024 dimensions. A configured adapter is not evidence that every model was tested.

Possible extensions, not scheduled pilot work:

- Anthropic.
- Gemini.
- Ollama.
- vLLM.
- Azure OpenAI.

## Storage

Implemented storage and coordination:

- PostgreSQL.
- pgvector.
- Redis.
- Local filesystem object store.
- S3/MinIO-compatible object-store adapter (not a running default local MinIO).

PostgreSQL is the only supported runtime/test database. Redis queue hints do
not replace the authoritative PostgreSQL Run ledger. No SQLite fallback exists.

Not part of the current stack or committed pilot scope:

- Qdrant or Weaviate.
- Temporal.
- ClickHouse or analytics warehouse.

## Observability

OpenTelemetry instrumentation, structured logs, Prometheus/Blackbox, Grafana,
Alloy/Loki, Tempo, Alertmanager and Mailpit are implemented. The default local
Compose stack includes these services. See the [acceptance ledger](observability-completion-plan.md)
for local end-to-end evidence and the remaining external-mailbox gate.
Jaeger is not the selected local trace backend; local SMTP capture is not real inbox delivery.

## Frontend

Implemented frontend:

- Next.js.
- React.
- TypeScript.
- Playwright.

Tailwind, shadcn/Radix and TanStack Query were early options, not installed
dependencies in the current Web package. Node.js 24 is the Docker/CI runtime
baseline. The supported first-use path has authenticated offline CI evidence;
the anonymous local paid experience is a different profile.

## Documentation

Current documentation:

- Markdown docs.
- ADRs.
- Lightweight feature specs.
- README.
- CONTRIBUTING.
- SECURITY.
- ROADMAP.

Optional documentation hosting, not a pilot prerequisite:

- MkDocs Material.

## Why Python Instead of Node.js for the Runtime

Node.js is viable, especially for product UI and full-stack SaaS work. Agent Kernel's core load is different: LLM integration, RAG, evals, document parsing, embeddings, tool orchestration, and runtime behavior. Python has lower friction and stronger ecosystem support for these areas.

Final split:

```text
Python = Agent brain, runtime, RAG, evals, worker, API, CLI
TypeScript = Web UI
```

## What Not to Use Too Early

Continue to avoid introducing without demonstrated need and separate scope:

- Microservices.
- Kubernetes.
- Temporal as the first workflow engine.
- A large number of LLM providers.
- A plugin marketplace.
- A default shell tool.
- A Web UI-first chat demo.
- Complex multi-agent orchestration before the single-agent runtime is solid.
