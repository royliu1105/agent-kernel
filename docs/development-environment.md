# Development Environment

## Goal

Agent Kernel should use a professional local development environment that is easy to reproduce, friendly to contributors, and close enough to production to catch real integration problems.

The baseline is:

```text
uv-first Python environment
Docker Compose for all long-running services
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
  Short-lived CLI/test tooling only; no default host application servers

Docker Compose:
  API + continuous Worker + Web
  PostgreSQL + pgvector
  Redis
  Prometheus + Grafana + Blackbox
  Alloy + Loki + Tempo + Alertmanager + Mailpit
```

Do not install project databases directly on the host unless there is a strong reason.
The default startup command is `make docker-up`. See [Docker-only local runtime](docker-local.md).
Host `uv`/Node remain development tools, not the default runtime. Use host server
processes only for an explicitly requested debugging exception.

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

Start Docker Desktop before running the local stack.

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
make test-db-up
make test
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

All long-running services now use one Compose project, `agent-kernel-local`.
The original infrastructure-only workflow is no longer the startup default.

```text
API / Worker / Web / PostgreSQL / Redis / observability / local SMTP
```

Expected commands:

```bash
make docker-up
make docker-status
make docker-logs SERVICE=worker
make docker-stop
make docker-down
```

## Local Worker

The Docker stack already runs a continuous Worker; do not launch a second host loop.
Inspect it with:

```bash
make docker-logs SERVICE=worker
```

Use the CLI inside the API container:

```bash
sh scripts/local-stack.sh exec -T api agent-kernel run inspect <run-id>
```

API and Worker share Docker PostgreSQL and Redis settings. The API startup applies
migrations before the Worker/Web become ready. PostgreSQL is required for all
database paths, including tests and explicit host debugging. Start a separate
test service with `make test-db-up`; see [PostgreSQL-only testing](postgresql-only.md).

For normal local testing, create runs with `mock:*` model references so no API key or network access
is required. Real OpenAI execution is explicit and requires:

```bash
OPENAI_API_KEY=...
```

Already included in the default stack:

```text
Prometheus
Grafana
Alloy / Loki / Tempo
Alertmanager / Mailpit
```

Do not make developers install those services directly on the host.
S3/MinIO is a separate deployment choice; this profile keeps objects in a named volume.

## Environment Variables

The project should include:

```text
.env.example
.env
.envrc
```

Rules:

- The Docker wrapper uses its own private `.agent-kernel/docker-local/config.env`,
  not root `.env`/`direnv`; see the Docker guide before changing runtime settings.

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

The repository exposes these workflows through `Makefile`. Database tests require
`make test-db-up`; do not use the running application's PostgreSQL for tests.

Recommended commands:

```bash
make setup
make docker-up
make test-db-up
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
export AGENT_KERNEL_TEST_POSTGRES_URL=postgresql+psycopg://agent_kernel:test-only@127.0.0.1:55432/agent_kernel_test
uv run pytest
npm run lint
npm run build
```

Run `make test-db-down` after testing to discard only the disposable test service.

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

The quality gate includes:

```bash
uv run ruff check .
uv run mypy .
make test-db-up
make test
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
