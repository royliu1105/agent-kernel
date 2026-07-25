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

- [ ] Check current git status.
- [ ] Read the relevant baseline docs.
- [ ] Create monorepo directory structure.
- [ ] Create Python project configuration.
- [ ] Add `.python-version`.
- [ ] Add `.gitignore`.
- [ ] Add `.env.example`.
- [ ] Add `.envrc` if appropriate.
- [ ] Add FastAPI `/healthz`.
- [ ] Add Typer CLI with `agent-kernel --version`.
- [ ] Add worker startup entrypoint.
- [ ] Add `kernel-core` foundation package.
- [ ] Define initial domain models: `Agent`, `Run`, `RunStep`, `ToolCall`, `Approval`.
- [ ] Add minimal Next.js + TypeScript Web app.
- [ ] Add Docker Compose with Postgres/pgvector and Redis.
- [ ] Add basic backend tests.
- [ ] Add basic Web build/lint scripts.
- [ ] Add GitHub Actions CI.
- [ ] Add `Makefile` or `justfile` for common commands.
- [ ] Update root README with quick local development instructions.

## Acceptance

- [ ] API starts.
- [ ] `GET /healthz` returns healthy response.
- [ ] CLI version command works.
- [ ] Worker starts and prints a ready message.
- [ ] Web app starts or builds.
- [ ] Docker Compose starts Postgres/pgvector and Redis.
- [ ] Basic tests pass.
- [ ] Lint passes.
- [ ] Typecheck passes, or any unavoidable initial limitation is documented.
- [ ] CI workflow exists.

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
