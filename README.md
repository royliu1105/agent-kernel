# Agent Kernel

Agent Kernel is planned as a self-hosted, observable, evaluable, resumable production-grade AI Agent Runtime for building real agent applications with tools, memory, knowledge bases, human approval, and workflows.

The canonical project baseline is captured in [docs/README.md](docs/README.md).

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
uv run uvicorn agent_kernel_api.main:app --reload
```

Run frontend checks:

```bash
npm run lint
npm run build
```

Validate infrastructure config:

```bash
docker compose config
```

Start dependencies when Docker Desktop is running:

```bash
docker compose up -d postgres redis
```
