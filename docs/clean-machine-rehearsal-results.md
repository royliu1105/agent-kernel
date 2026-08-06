# Clean-Machine Rehearsal Results

This document records v1.0 release candidate clean-machine rehearsal evidence.

## Day 85 Result

Date:

```text
2026-08-07 Asia/Shanghai
```

Baseline commit rehearsed from a fresh local clone:

```text
cf2163b813f23a957ecb3eb956df0fde68086b5c
```

Temporary checkout:

```text
/tmp/agent-kernel-rehearsal.45pfr0/agent-kernel
```

Tool versions observed:

```text
uv 0.11.32
Node.js v24.16.0
npm 11.13.0
Docker Compose v5.3.1
```

## Passed Gates

Clean checkout:

- `git status --short`: clean.
- `uv sync --dev`: passed.
- `npm install`: passed with known npm audit warnings.
- `uv run alembic upgrade head`: passed on SQLite.
- `uv run agent-kernel --version`: passed.
- `uv run agent-kernel-worker --help`: passed.
- `uv run ruff check .`: passed.
- `uv run mypy .`: passed.
- `uv run pytest`: 313 passed, 1 Starlette deprecation warning.
- `make release-eval`: passed.
- `make release-load-soak`: passed with 25/25 worker burst successes.
- `make release-smoke`: passed.
- `npm run test:e2e`: 2 Playwright smoke tests passed.

Post-fix current checkout:

- `AGENT_KERNEL_API_HOST=127.0.0.1 AGENT_KERNEL_API_PORT=8011 uv run agent-kernel-api`:
  API started on `127.0.0.1:8011`.
- `curl http://127.0.0.1:8011/healthz`: returned
  `{"status":"ok","service":"agent-kernel-api"}`.
- `uv run pytest tests/unit/test_api_health.py`: 7 passed.
- `uv run ruff check .`: passed.
- `uv run mypy .`: passed.
- `make release-smoke`: passed.
- `make release-load-soak`: passed.
- `docker compose config`: passed.
- `AGENT_KERNEL_API_PORT=8011 docker compose config`: passed and rewired the
  API container port plus Web API URLs to `8011`.

Docker evidence:

- Existing local Docker Compose stack was running and healthy.
- `docker compose ps` showed healthy API, Web, Postgres, and Redis services,
  plus a running worker.
- `curl http://127.0.0.1:8000/healthz`: passed.
- `curl -I http://127.0.0.1:3000`: returned HTTP 200.

## Issues Found

### API rehearsal command was wrong

Original rehearsal plan used:

```bash
uv run agent-kernel-api --help
```

Actual behavior:

- `agent-kernel-api` starts Uvicorn.
- `--help` is passed through in a way that does not provide a help screen.
- The command failed when port `8000` was already in use.

Classification:

```text
documentation + configuration
```

Fix:

- Added `AGENT_KERNEL_API_HOST`.
- Added `AGENT_KERNEL_API_PORT`.
- Wired Docker Compose to pass API host/port into the API container and to
  derive Web API URLs from the configured API port.
- Updated the clean-machine rehearsal runbook.
- Updated quickstart and configuration docs.
- Added tests for API host/port parsing.

## Known Limitations

Day 85 did not stop or destroy the existing local Docker Compose stack. Because
ports `8000`, `3000`, `5432`, and `6379` were already occupied by a healthy
Agent Kernel stack, Day 85 did not perform a fresh full-stack Compose restart
from the temporary checkout.

This means:

- The clean checkout application gates passed.
- The local Docker stack health check passed.
- A fresh Docker restart from the clean checkout remains unclaimed.

Day 85 therefore marks the rehearsal fixes complete, but the v1.0 milestone
acceptance item `Clean-machine release rehearsal passes` should remain open
until a fresh full-stack restart is executed or explicitly waived.

## Day 90 Follow-Up

Day 90 fixed the remaining full-stack rehearsal blocker by making Docker
Compose host ports configurable for Web, Postgres, and Redis in addition to the
API process port.

The following isolated host-port mapping was validated:

```bash
AGENT_KERNEL_API_PORT=8011 \
AGENT_KERNEL_WEB_PORT=3011 \
AGENT_KERNEL_POSTGRES_PORT=55432 \
AGENT_KERNEL_REDIS_PORT=56379 \
docker compose config
```

Day 90 then started an isolated Compose project:

```bash
AGENT_KERNEL_API_PORT=8011 \
AGENT_KERNEL_WEB_PORT=3011 \
AGENT_KERNEL_POSTGRES_PORT=55432 \
AGENT_KERNEL_REDIS_PORT=56379 \
docker compose -p agent-kernel-day90 up --build -d
```

Observed result:

- Postgres became healthy on host port `55432`.
- Redis became healthy on host port `56379`.
- API became healthy on host port `8011`.
- Web became healthy on host port `3011`.
- Worker started successfully.
- `curl http://127.0.0.1:8011/healthz` returned
  `{"status":"ok","service":"agent-kernel-api"}`.
- `curl -i http://127.0.0.1:8011/metrics` returned HTTP 200 with
  Prometheus text content type.
- `curl -I http://127.0.0.1:3011` returned HTTP 200.
- A CLI-driven mock run was created, queued, executed by the container worker,
  and completed with status `succeeded`.

The temporary Day 90 stack was removed with:

```bash
docker compose -p agent-kernel-day90 down -v
```

This closes the Day 85 full-stack Docker restart limitation for the local
release-candidate workspace. The final release commit should still be pushed
and verified by GitHub CI before tagging.
