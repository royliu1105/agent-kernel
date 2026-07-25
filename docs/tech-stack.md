# Technology Stack

## Final Recommendation

Use Python for the Agent runtime and TypeScript for the Web UI:

```text
Python Agent Runtime + FastAPI API + Typer CLI + Worker
Next.js + TypeScript Web UI
PostgreSQL + pgvector + Redis
Docker Compose + GitHub Actions
```

## Backend

MVP stack:

- Python 3.12+
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

MVP:

- OpenAI provider.
- Mock provider.
- Replay provider.

Later:

- Anthropic.
- Gemini.
- Ollama.
- vLLM.
- Azure OpenAI.

## Storage

MVP:

- PostgreSQL.
- pgvector.
- Redis.
- Local filesystem object store.

Later:

- S3 or MinIO.
- Qdrant or Weaviate.
- Temporal.
- ClickHouse or analytics warehouse.
- Tempo, Jaeger, Prometheus, and Grafana.

## Frontend

MVP:

- Next.js.
- TypeScript.
- Tailwind CSS.
- shadcn/ui or Radix UI.
- TanStack Query.
- Playwright.

## Documentation

MVP:

- Markdown docs.
- ADRs.
- Lightweight feature specs.
- README.
- CONTRIBUTING.
- SECURITY.
- ROADMAP.

Later:

- MkDocs Material.

## Why Python Instead of Node.js for the Runtime

Node.js is viable, especially for product UI and full-stack SaaS work. Agent Kernel's core load is different: LLM integration, RAG, evals, document parsing, embeddings, tool orchestration, and runtime behavior. Python has lower friction and stronger ecosystem support for these areas.

Final split:

```text
Python = Agent brain, runtime, RAG, evals, worker, API, CLI
TypeScript = Web UI
```

## What Not to Use Too Early

Avoid in v0.1:

- Microservices.
- Kubernetes.
- Temporal as the first workflow engine.
- A large number of LLM providers.
- A plugin marketplace.
- A default shell tool.
- A Web UI-first chat demo.
- Complex multi-agent orchestration before the single-agent runtime is solid.
