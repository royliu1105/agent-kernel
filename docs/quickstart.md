# Quickstart

This quickstart exercises the current Phase 1 runtime path:

```text
create agent -> create run -> queue run -> worker executes -> inspect output and timeline
```

## Setup

Install dependencies:

```bash
uv sync
npm install
```

Apply database migrations. Without `DATABASE_URL`, Agent Kernel uses the local SQLite database under
`.agent-kernel/`.

```bash
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

## Create An Agent

```bash
uv run agent-kernel agent create --name "Local Test Agent"
```

Copy the returned agent `id`.

## Create A Run

Use a mock model so no network or API key is required:

```bash
uv run agent-kernel run create <agent-id> --input '{"task":"hello runtime","model":"mock:echo"}'
```

Copy the returned run `id`.

## Queue The Run

```bash
uv run agent-kernel run queue <run-id>
```

## Execute With Worker

In another terminal:

```bash
uv run agent-kernel-worker --once --limit 10
```

Expected shape:

```text
processed=1 succeeded=1 failed=0
```

If there are no queued runs, the worker prints:

```text
processed=0 succeeded=0 failed=0
```

## Inspect The Result

```bash
uv run agent-kernel run inspect <run-id>
uv run agent-kernel run events <run-id>
```

Expected run status:

```text
succeeded
```

Expected event timeline:

```text
run_created
run_queued
run_started
run_completed
```

## Cancel A Run

Created or queued runs can be canceled through CLI:

```bash
uv run agent-kernel run cancel <run-id>
```

Canceling a terminal run returns an API conflict.

## Optional Docker Services

Start Postgres and Redis when testing infrastructure configuration:

```bash
docker compose up -d postgres redis
docker compose ps
```

Use `DATABASE_URL` to point the API, worker, and migrations at Postgres.

## Notes

- Use `mock:*` models for normal local development.
- `openai:*` models require `OPENAI_API_KEY`.
- `replay:*` models are for deterministic replay fixtures and fail clearly when no fixture is
  registered.
- The worker currently uses persisted queued runs as the MVP queue. Redis-backed scheduling and
  distributed worker leases are deferred.
