# Agent Kernel

Agent Kernel is planned as a self-hosted, observable, evaluable, resumable production-grade AI Agent Runtime for building real agent applications with tools, memory, knowledge bases, human approval, and workflows.

The canonical project baseline is captured in [docs/README.md](docs/README.md).

Run the current local runtime path with [docs/quickstart.md](docs/quickstart.md).

If local setup gets stuck, use [docs/troubleshooting.md](docs/troubleshooting.md).

Current release:

- [Agent Kernel v0.1.0](https://github.com/royliu1105/agent-kernel/releases/tag/v0.1.0)

Post-v0.1 completion plan:

- [Public Alpha, Beta, and v1.0 plan](docs/post-v0.1-plan.md)

Current v0.1 shape:

```text
Python API + CLI + worker + Postgres/SQLite storage + RAG/memory/tools/evals + Next.js Workbench
```

## Local Development

Required tools:

- Python 3.12 through `uv`
- Node.js 24+
- Docker Desktop
- `direnv`
- `pre-commit`

Set up the workspace:

```bash
uv sync
npm install
```

Run backend checks:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
```

Run local entrypoints:

```bash
uv run agent-kernel --version
uv run agent-kernel-worker
uv run agent-kernel-worker --once --limit 10
uv run agent-kernel-api
```

Run frontend checks:

```bash
npm run lint
npm run build
npm run test:e2e
```

Validate infrastructure config:

```bash
docker compose config
```

Start local infrastructure dependencies when Docker Desktop is running:

```bash
docker compose up -d postgres redis
```

Start the full local stack when Docker Desktop is running:

```bash
docker compose up --build
```

The full stack exposes:

- API: `http://127.0.0.1:8000`
- API health: `http://127.0.0.1:8000/healthz`
- Web Workbench: `http://127.0.0.1:3000`

Run the standard local verification set:

```bash
make verify
make verify-web
```

`make verify` avoids browser e2e tests by default. `make verify-web` includes Playwright.
