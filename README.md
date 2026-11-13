# Agent Kernel

Agent Kernel is a self-hosted, observable, evaluable, resumable production-grade AI Agent Runtime for building real agent applications with tools, memory, knowledge bases, human approval, and workflows.

The canonical project baseline is captured in [docs/README.md](docs/README.md).

Run the current local runtime path with [docs/quickstart.md](docs/quickstart.md).

If local setup gets stuck, use [docs/troubleshooting.md](docs/troubleshooting.md).

Current release:

- [Agent Kernel v1.0.0](https://github.com/royliu1105/agent-kernel/releases/tag/v1.0.0), published 2026-08-07.

Current development:

- [Post-v1.0 capability hardening](docs/capability-hardening-plan.md) is the
  canonical plan and acceptance record for current work.
- `master` contains unreleased changes beyond the `v1.0.0` tag. Historical
  release CI does not verify those changes; current evidence lives in the plan.
- Review the [upgrade and migration policy](docs/upgrade-migration-policy.md)
  before upgrading an existing deployment.

Historical delivery:

- [Public Alpha, Beta, and v1.0 plan](docs/post-v0.1-plan.md)
- [v1.0.0 release notes](docs/releases/v1.0.0.md)
- [Public Alpha summary](docs/public-alpha-summary.md)
- [Feedback templates](.github/ISSUE_TEMPLATE)

Project shape:

```text
Python API + CLI + worker + Postgres/SQLite storage + RAG/memory/tools/evals + Next.js Workbench
```

## Local Development

For a first run, follow [Quickstart](docs/quickstart.md). The default path uses
SQLite and mock models, so it does not require Docker or external LLM
credentials.

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

## Feedback

Agent Kernel is in post-v1.0 capability hardening. Please
use GitHub Issues for reproducible bugs, focused feature requests, or first-run
feedback. Redact secrets, API keys, tokens, private documents, and private logs
before sharing output.
