# Quickstart

This quickstart exercises the current v0.1 local runtime path:

```text
install deps -> migrate storage -> create agent/run -> execute worker -> inspect runtime -> open Web Workbench
```

Use mock models for the default path. No external LLM credentials are required.

## Prerequisites

- Python 3.12 through `uv`.
- Node.js 24+.
- Docker Desktop when using Postgres/Redis or full Docker Compose.
- `make` for convenience commands.

## Setup

Install dependencies:

```bash
uv sync
npm install
```

Create a local environment file:

```bash
cp .env.example .env
```

For the fastest local path, either leave `DATABASE_URL` unset to use SQLite or
set it to the Postgres URL from `.env.example` after starting Docker services.

## Option A: SQLite Quick Path

SQLite is useful for fast local development without Docker:

```bash
unset DATABASE_URL
uv run alembic upgrade head
```

This creates the local database under:

```text
.agent-kernel/agent_kernel.db
```

## Option B: Postgres and Redis Services

Start infrastructure services:

```bash
docker compose up -d postgres redis
docker compose ps
```

Apply migrations against Postgres:

```bash
DATABASE_URL=postgresql+psycopg://agent_kernel:agent_kernel@localhost:5432/agent_kernel \
  uv run alembic upgrade head
```

## Start API

In one terminal:

```bash
uv run agent-kernel-api
```

Verify:

```bash
curl http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status":"ok","service":"agent-kernel-api"}
```

## Create and Run an Agent

Create an agent:

```bash
uv run agent-kernel agent create --name "Local Test Agent"
```

Copy the returned agent `id`.

Create a run using a mock model:

```bash
uv run agent-kernel run create <agent-id> --input '{"task":"hello runtime","model":"mock:echo"}'
```

Copy the returned run `id`.

Queue the run:

```bash
uv run agent-kernel run queue <run-id>
```

Execute queued work:

```bash
uv run agent-kernel-worker --once --limit 10
```

Expected shape:

```text
processed=1 succeeded=1 failed=0
```

Inspect the result and timeline:

```bash
uv run agent-kernel run inspect <run-id>
uv run agent-kernel run events <run-id>
```

Expected run status:

```text
succeeded
```

Expected event timeline includes:

```text
run_created
run_queued
run_started
run_completed
```

## Try RAG and Memory Commands

Create a knowledge base:

```bash
uv run agent-kernel kb create --name "Engineering Handbook"
```

Upload, ingest, chunk, index, and search a document:

```bash
uv run agent-kernel document upload <knowledge-base-id> ./README.md
uv run agent-kernel document ingest <document-id>
uv run agent-kernel document chunk <document-id>
uv run agent-kernel document index <document-id>
uv run agent-kernel kb search <knowledge-base-id> --query "What is Agent Kernel?"
```

Create and inspect a scoped memory item:

```bash
uv run agent-kernel memory create \
  --type user_preference \
  --scope user:local \
  --content '{"language":"en"}'

uv run agent-kernel memory list --scope user:local
```

## Run Evals

Run the deterministic RAG smoke eval:

```bash
uv run agent-kernel eval report evals/rag-smoke.json
```

## Start Web Workbench

In another terminal:

```bash
npm run web:dev
```

Open:

```text
http://127.0.0.1:3000
```

The current Workbench is fixture-backed. It exposes the v0.1 product surface,
including dashboard, agents, runs, approvals, knowledge, evals, and settings,
but it does not yet fetch all live backend data.

## Full Docker Compose Stack

When Docker Desktop is running, start the full local stack:

```bash
docker compose up --build
```

Services:

```text
postgres  -> localhost:5432
redis     -> localhost:6379
api       -> http://127.0.0.1:8000
web       -> http://127.0.0.1:3000
worker    -> background queued-run worker
```

The API container runs migrations before startup.

For config-only validation:

```bash
docker compose config
```

## Verification

Run backend checks:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
uv run agent-kernel eval report evals/rag-smoke.json
```

Run Web checks:

```bash
npm run lint
npm run build
npm run test:e2e
```

Convenience targets:

```bash
make verify
make verify-web
```

## Notes

- Use `mock:*` models for normal local development.
- `openai:*` models require `OPENAI_API_KEY`.
- `replay:*` models are for deterministic replay fixtures and fail clearly when
  no fixture is registered.
- The worker currently uses persisted queued runs as the MVP queue.
- Redis-backed scheduling and distributed worker leases are deferred.
- Web approval decisions are local UI state until live Web mutation is added.
