# Day 85: Clean-Machine Release Rehearsal Fixes

Goal:

Execute the v1.0 release candidate clean-machine rehearsal, fix release-blocking
setup gaps discovered by the run, and record evidence without overstating
coverage.

Scope:

- Run a fresh local clone rehearsal from the latest committed baseline.
- Validate dependency install, SQLite migration, Python gates, release evals,
  release smoke, load/soak, Web build, and Web e2e from the clean checkout.
- Fix clean-machine issues discovered during rehearsal.
- Record rehearsal evidence and limitations.
- Update API configuration docs for host/port binding.
- Update daily index and milestone tracking.
- Do not stop or destroy existing Docker containers owned by the user's local
  environment.

Tasks:

- [x] Check current git status before editing.
- [x] Create a temporary clean checkout.
- [x] Record tool versions and commit SHA.
- [x] Run dependency installs from the clean checkout.
- [x] Run SQLite migration and local command checks.
- [x] Run Python release gates from the clean checkout.
- [x] Run Web gates from the clean checkout.
- [x] Identify API startup rehearsal issue.
- [x] Add configurable API host/port environment variables.
- [x] Add tests for API host/port configuration parsing.
- [x] Update configuration, quickstart, and rehearsal docs.
- [x] Record Day 85 rehearsal evidence and remaining limitation.
- [x] Update daily index and milestones.

Acceptance:

- [x] Clean checkout dependency install succeeds.
- [x] Clean checkout SQLite migration succeeds.
- [x] Clean checkout Python tests, release evals, release smoke, and load/soak
  gates pass.
- [x] Clean checkout Web lint/build/e2e gates pass.
- [x] API can bind to a non-default port for rehearsal.
- [x] The discovered API rehearsal issue is fixed and documented.
- [x] Full Docker stack health is checked without disrupting existing user
  containers.
- [x] Full clean-machine restart remains explicitly unclaimed when not executed.

Verification:

- [x] clean checkout `uv sync --dev`
- [x] clean checkout `npm install`
- [x] clean checkout `uv run alembic upgrade head`
- [x] clean checkout `uv run ruff check .`
- [x] clean checkout `uv run mypy .`
- [x] clean checkout `uv run pytest`
- [x] clean checkout `make release-eval`
- [x] clean checkout `make release-smoke`
- [x] clean checkout `make release-load-soak`
- [x] clean checkout `npm run test:e2e`
- [x] `AGENT_KERNEL_API_HOST=127.0.0.1 AGENT_KERNEL_API_PORT=8011 uv run agent-kernel-api`
- [x] `curl http://127.0.0.1:8011/healthz`
- [x] `uv run pytest tests/unit/test_api_health.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `make release-smoke`
- [x] `make release-load-soak`
- [x] `docker compose config`
- [x] `AGENT_KERNEL_API_PORT=8011 docker compose config`
- [x] `git diff --check`

Notes:

- The existing Docker Compose stack was already running and healthy on ports
  `8000`, `3000`, `5432`, and `6379`. Day 85 did not stop it or perform a fresh
  full-stack restart from the temporary checkout.
