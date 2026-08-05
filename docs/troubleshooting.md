# Troubleshooting

This guide covers common local development and release-verification failures for
Agent Kernel.

Use this together with:

- [Quickstart](quickstart.md)
- [Development Environment](development-environment.md)
- [Production Configuration](production-config.md)
- [Release Checklist](release-checklist.md)

## First Checks

Check tool versions:

```bash
uv --version
uv python list --only-installed
node --version
npm --version
docker --version
docker compose version
```

Check repository state:

```bash
git status --short
uv sync
npm install
docker compose config
```

If these fail, fix them before debugging runtime behavior.

## Docker Compose

### `docker compose up --build` Hangs While Pulling Images

Most often this is a registry/network issue, not an Agent Kernel code issue.

Useful checks:

```bash
docker pull ghcr.io/astral-sh/uv:python3.12-bookworm-slim
docker pull node:24-bookworm-slim
docker pull pgvector/pgvector:pg16
docker pull redis:7-alpine
```

If Docker Hub token requests time out while fetching `node:24-bookworm-slim`,
wait and retry. The Web image cannot build until that base image metadata is
available.

Agent Kernel uses these Dockerfiles:

```text
deploy/Dockerfile.python
apps/web/Dockerfile
```

There is intentionally no root-level `Dockerfile`.

### Containers Exist but the Browser Cannot Open `127.0.0.1:8000`

Docker containers being visible does not mean the API is listening on the host
port. Check service status:

```bash
docker compose ps
docker compose logs api
```

The API should expose:

```text
http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status":"ok","service":"agent-kernel-api"}
```

Common causes:

- The API container has not started yet.
- Migrations failed before the server started.
- Port `8000` is already used by another process.
- Only `postgres` and `redis` were started, not the full stack.

Check port usage on macOS:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3000 -sTCP:LISTEN
```

### `docker compose up -d postgres redis` Works but API Is Unavailable

This command only starts infrastructure dependencies. It does not start the API,
worker, or Web Workbench.

For local development, start the API manually:

```bash
uv run agent-kernel-api
```

For the full Compose stack:

```bash
docker compose up --build
```

### Worker Prints `ready` and Exits

This is expected for one-shot worker commands:

```bash
uv run agent-kernel-worker
uv run agent-kernel-worker --once --limit 10
```

The worker checks queued runs, processes what it can, prints a summary, and
exits.

Use loop mode when you want it to stay running:

```bash
uv run agent-kernel-worker --loop --limit 25 --poll-interval 2
```

Stop a foreground worker with `Ctrl-C`.

## Python and uv

### `uv run` Cannot Access the Cache

If `uv` reports permission problems under `~/.cache/uv`, the environment may be
running with restricted filesystem access. In a normal terminal, rerun:

```bash
uv sync
uv run pytest
```

If it still fails, check ownership:

```bash
ls -ld ~/.cache ~/.cache/uv
```

### Wrong Python Version

Agent Kernel targets Python 3.12 for the runtime.

Check installed interpreters:

```bash
uv python list --only-installed
```

Install Python 3.12 with uv:

```bash
uv python install 3.12
uv sync
```

When running project commands, prefer:

```bash
uv run <command>
```

This ensures the project virtual environment is used instead of a random system
or Homebrew Python.

### Migrations Fail

For SQLite local development:

```bash
unset DATABASE_URL
uv run alembic upgrade head
```

For local Postgres:

```bash
docker compose up -d postgres redis
DATABASE_URL=postgresql+psycopg://agent_kernel:agent_kernel@localhost:5432/agent_kernel \
  uv run alembic upgrade head
```

If Postgres is still starting, wait until it is healthy:

```bash
docker compose ps postgres
```

If Postgres reports:

```text
value too long for type character varying(32)
```

while updating `alembic_version.version_num`, a migration revision id is longer
than Alembic's default 32-character version column. Keep revision ids short and
run the migration tests:

```bash
uv run pytest tests/unit/test_migrations.py
```

## Node and Web

### Node Version Is Too Old

The workspace requires Node.js 22 or newer. The current development baseline is
Node.js 24.

Check:

```bash
node --version
npm --version
```

Then install dependencies:

```bash
npm install
```

### Web Workbench Does Not Open

Start the Web Workbench:

```bash
npm run web:dev
```

Open:

```text
http://127.0.0.1:3000
```

If the port is busy:

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
```

### `npm audit` Reports Vulnerabilities

Do not blindly run:

```bash
npm audit fix --force
```

Force fixes may upgrade framework packages across breaking ranges. Review the
advisory, affected transitive dependency, available fixed version, and Next.js
compatibility first.

For release work, record the risk in the release checklist and prefer a normal
dependency upgrade when a compatible stable version is available.

## Runtime Commands

### CLI Cannot Reach the API

Most CLI commands call the local API. If the API is not running, commands can
fail with:

```text
Could not reach Agent Kernel API at http://127.0.0.1:8000/...
```

Start the API:

```bash
uv run agent-kernel-api
```

Verify health:

```bash
curl http://127.0.0.1:8000/healthz
```

Expected:

```json
{"status":"ok","service":"agent-kernel-api"}
```

If the API is running on another host or port, either set:

```bash
export AGENT_KERNEL_API_URL=http://127.0.0.1:8000
```

or pass:

```bash
uv run agent-kernel agent create --name "Example" --api-url http://127.0.0.1:8000
```

Also check port usage:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

### CLI JSON Is Hard to Quote

Most JSON object arguments accept inline JSON or `@file`.

Inline:

```bash
uv run agent-kernel run create <agent-id> --input '{"task":"hello","model":"mock:echo"}'
```

From a file:

```bash
uv run agent-kernel run create <agent-id> --input @examples/mock-run-input.json
```

### Mock Models vs Real Providers

Use mock models for local verification:

```text
mock:echo
mock:reverse
mock:tool-request
```

Real OpenAI models require:

```bash
export OPENAI_API_KEY=...
```

### Knowledge Base Search Returns No Results

RAG retrieval only searches indexed chunks. The required sequence is:

```bash
uv run agent-kernel kb create --name "Example Handbook"
uv run agent-kernel document upload <knowledge-base-id> examples/docs/deployment-playbook.md
uv run agent-kernel document ingest <document-id>
uv run agent-kernel document chunk <document-id>
uv run agent-kernel document index <document-id>
uv run agent-kernel kb search <knowledge-base-id> --query "rollback"
```

If search returns no results, confirm:

- You are using the correct knowledge base ID.
- `document chunk <document-id>` completed before indexing.
- `document index <document-id>` returned a positive `embedding_count`.
- The query uses terms that appear in the document.

### Workbench Says API Unreachable

The Workbench live panels call the API through same-origin Web routes. If the
top bar shows API unreachable or a live panel shows a lookup error:

1. Confirm the API is running at `http://127.0.0.1:8000/healthz`.
2. Confirm the Web app is running at `http://127.0.0.1:3000`.
3. If the API uses another URL, set `NEXT_PUBLIC_AGENT_KERNEL_API_URL` before
   starting the Web app.
4. Refresh the browser after restarting API or Web.

Useful local commands:

```bash
curl http://127.0.0.1:8000/healthz
npm run web:dev
```

During Public Alpha, some Workbench sections are fixture-backed previews while
the live API paths are being connected. Fixture-backed preview data does not
prove the backend API is reachable; use the top-bar health indicator or live
lookup panels for that.

## Release Verification

Before tagging a release, run:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
uv run agent-kernel eval report evals/rag-smoke.json
npm run lint
npm run build
npm run test:e2e
docker compose config
docker compose up --build
```

Release checklist items should only be checked when the command was actually
run and passed in the release-candidate state.
