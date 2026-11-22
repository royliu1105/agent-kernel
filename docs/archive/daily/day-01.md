# Day 01: Project Skeleton and Engineering Baseline

## Goal

Turn the repository into a serious open-source project skeleton with a working engineering baseline.

## Scope

Day 1 should create the minimal runnable structure for:

- Python backend packages.
- FastAPI API entrypoint.
- Typer CLI entrypoint.
- Worker entrypoint.
- Next.js Web app.
- Docker Compose infrastructure.
- Basic tests.
- Quality tooling.
- CI.

Day 1 should not implement the full agent runtime, RAG, memory, approvals, evals, or observability internals.

## Tasks

- [x] Check current git status.
- [x] Read the relevant baseline docs.
- [x] Create monorepo directory structure.
- [x] Create Python project configuration.
- [x] Add `.python-version`.
- [x] Add `.gitignore`.
- [x] Add `.env.example`.
- [x] Add `.envrc` if appropriate.
- [x] Add FastAPI `/healthz`.
- [x] Add Typer CLI with `agent-kernel --version`.
- [x] Add worker startup entrypoint.
- [x] Add `kernel-core` foundation package.
- [x] Define initial domain models: `Agent`, `Run`, `RunStep`, `ToolCall`, `Approval`.
- [x] Add minimal Next.js + TypeScript Web app.
- [x] Add Docker Compose with Postgres/pgvector and Redis.
- [x] Add basic backend tests.
- [x] Add basic Web build/lint scripts.
- [x] Add GitHub Actions CI.
- [x] Add `Makefile` or `justfile` for common commands.
- [x] Update root README with quick local development instructions.

## Acceptance

- [x] API starts.
- [x] `GET /healthz` returns healthy response.
- [x] CLI version command works.
- [x] Worker starts and prints a ready message.
- [x] Web app starts or builds.
- [x] Docker Compose starts Postgres/pgvector and Redis.
- [x] Basic tests pass.
- [x] Lint passes.
- [x] Typecheck passes, or any unavoidable initial limitation is documented.
- [x] CI workflow exists.

## Verification

Run the available commands:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
npm run lint
npm run build
docker compose config
```

If a command cannot run because dependencies are unavailable or the environment is not ready, record the reason in Notes and keep the project files correct.

## Notes

- Use the baseline in `docs/development-environment.md`.
- Keep Day 1 small and structural.
- Do not add complex runtime behavior yet.
- `npm audit` reports 3 high vulnerabilities through Next.js transitive dependencies (`postcss` and `sharp`). The latest stable Next.js is installed (`16.2.12`), while the apparent fixed range is only available in canary/preview builds. Keep this visible and revisit when a stable Next.js release includes the upstream fixes.
