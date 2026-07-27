# Development Environment

## Goal

Agent Kernel should use a professional local development environment that is easy to reproduce, friendly to contributors, and close enough to production to catch real integration problems.

The baseline is:

```text
uv-first Python environment
Docker Compose for infrastructure
direnv for local environment variables
pre-commit for local quality gates
VS Code or PyCharm with Ruff, mypy, and pytest integration
```

## Core Principle

Keep local responsibilities clear:

```text
Host machine:
  Python runtime
  Node.js runtime
  IDE
  lint/typecheck/test
  API/worker/CLI development

Docker Compose:
  PostgreSQL + pgvector
  Redis
  Later: MinIO, OpenTelemetry Collector, observability backends
```

Do not install project databases directly on the host unless there is a strong reason.

## Required Tools

Recommended macOS tools:

```text
Homebrew
Git
uv
Docker Desktop
Node.js LTS
pnpm or npm
direnv
pre-commit
```

Optional:

```text
pyenv
```

`pyenv` is useful if you manage many unrelated global Python versions. For Agent Kernel, the preferred default is `uv` for Python version, virtual environment, dependency management, and command execution.

## Installation on macOS

Install Xcode command line tools:

```bash
xcode-select --install
```

Install core tools:

```bash
brew install git uv direnv pre-commit node
brew install --cask docker
```

Optional:

```bash
brew install pyenv
```

Start Docker Desktop before running infrastructure services.

## Python Environment

Use:

```text
Python 3.12+
uv
```

The project should include:

```text
.python-version
pyproject.toml
uv.lock
```

Expected daily commands:

```bash
uv sync
uv run python --version
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy .
```

Avoid:

```bash
pip install ...
python script.py
```

Prefer:

```bash
uv add <package>
uv run <command>
```

This keeps dependency state reproducible.

## Node.js Environment

The Web UI uses Next.js and TypeScript.

Recommended:

```text
Node.js LTS
pnpm or npm
```

Expected commands:

```bash
npm install
npm run lint
npm run build
```

If the project later standardizes on pnpm, use:

```bash
pnpm install
pnpm lint
pnpm build
```

The package manager choice should be locked in the root `package.json`.

## Docker Compose

MVP infrastructure services:

```text
PostgreSQL + pgvector
Redis
```

Expected commands:

```bash
docker compose up -d postgres redis
docker compose ps
docker compose logs -f
docker compose down
```

## Local Worker

The worker can be started without processing any runs:

```bash
uv run agent-kernel-worker
```

Process queued runs once:

```bash
uv run agent-kernel-worker --once --limit 10
```

Run a local polling loop:

```bash
uv run agent-kernel-worker --loop --limit 10 --poll-interval 5
```

The worker uses the same `DATABASE_URL` resolution as the API. If `DATABASE_URL` is not set, it uses
the local SQLite database path from `kernel-storage`.

Before processing runs against a fresh database, apply migrations:

```bash
uv run alembic upgrade head
```

For normal local testing, create runs with `mock:*` model references so no API key or network access
is required. Real OpenAI execution is explicit and requires:

```bash
OPENAI_API_KEY=...
```

Later services may include:

```text
MinIO
OpenTelemetry Collector
Prometheus
Grafana
Tempo or Jaeger
```

Do not make developers install those services directly on the host.

## Environment Variables

The project should include:

```text
.env.example
.env
.envrc
```

Rules:

- `.env.example` is committed.
- `.env` is local and must not be committed.
- `.envrc` may load `.env` and project paths.
- Secrets never go into git.

Recommended `.envrc` pattern:

```bash
dotenv_if_exists .env
```

After creating or editing `.envrc`:

```bash
direnv allow
```

## Pre-Commit Hooks

Use pre-commit to catch issues before commits.

Expected project file:

```text
.pre-commit-config.yaml
```

Expected commands:

```bash
pre-commit install
pre-commit run --all-files
```

Initial hooks should include:

- Ruff lint.
- Ruff format check.
- Basic whitespace/end-of-file checks.
- YAML/TOML checks.

Mypy and tests may run in CI and local `make verify` rather than every commit if they become too slow.

## IDE Setup

### VS Code

Recommended extensions:

- Python.
- Pylance.
- Ruff.
- Mypy Type Checker.
- Docker.
- GitHub Actions.
- Even Better TOML.
- YAML.

Recommended behavior:

- Use the project `.venv`.
- Format on save.
- Organize imports on save.
- Use pytest as the test runner.
- Use Ruff as linter/formatter.
- Surface mypy diagnostics.

### PyCharm

PyCharm Professional is also a strong choice for this project, especially for:

- FastAPI debugging.
- Database inspection.
- Larger Python refactors.
- Test navigation.

Configure PyCharm to use the project `.venv` created by `uv`.

## Standard Local Commands

The project should later expose one-command workflows through `Makefile` or `justfile`.

Recommended commands:

```bash
make setup
make dev
make test
make lint
make format
make typecheck
make verify
```

Equivalent direct commands:

```bash
uv sync
uv run ruff check .
uv run ruff format .
uv run mypy .
uv run pytest
npm run lint
npm run build
```

## Professional Habits

Follow these rules:

- Do not use system Python for project work.
- Do not globally install project dependencies with `pip`.
- Run Python commands through `uv run`.
- Keep dependency changes in the lockfile.
- Use Docker Compose for Postgres, Redis, and related infrastructure.
- Keep `.env` out of git.
- Run focused tests while developing.
- Run full verification before larger commits.
- Update docs when behavior or architecture changes.

## Anti-Patterns

Avoid:

- Installing Postgres and Redis manually on the host for this project.
- Mixing `pip`, `poetry`, `conda`, and `uv` in the same project.
- Running commands against the wrong Python interpreter.
- Depending on globally installed Python packages.
- Committing `.env`, local database files, or generated caches.
- Letting IDE settings override project formatting and lint rules.

## Initial Project Files to Create on Day 1

Day 1 should create or plan these files:

```text
.python-version
pyproject.toml
uv.lock
.env.example
.envrc
.gitignore
.pre-commit-config.yaml
docker-compose.yml
Makefile or justfile
```

The initial quality gate should include:

```bash
uv run ruff check .
uv run mypy .
uv run pytest
npm run lint
npm run build
```

## Final Baseline

Agent Kernel's local development environment is:

```text
uv + Python 3.12
Docker Desktop + Docker Compose
PostgreSQL/pgvector + Redis in Docker
Node.js LTS for Next.js
direnv for env loading
pre-commit for local checks
ruff + mypy + pytest for Python quality
```
