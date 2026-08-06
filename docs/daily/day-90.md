# Day 90: v1.0 Final Verification and Release Readiness

Goal:

Run the final v1.0 release readiness checks, update release evidence, and decide
whether Agent Kernel is ready to tag and publish v1.0.

Scope:

- Execute required Python, Web, release, migration, Docker, and docs gates.
- Run or resolve the clean-machine full-stack Docker Compose rehearsal.
- Update the v1.0 release checklist and release notes with final evidence.
- Update milestones with the final readiness decision.
- Do not create a tag or GitHub Release unless the release checklist is ready
  and the user explicitly asks to publish.

Tasks:

- [x] Check current git status before editing.
- [x] Run Python quality gates.
- [x] Run release eval, smoke, and load/soak gates.
- [x] Run Web quality gates.
- [x] Run migration and storage checks.
- [x] Run clean-machine Docker Compose rehearsal or document a release blocker.
- [x] Review security and dependency status.
- [x] Confirm GitHub CI status where available.
- [x] Update v1.0 release checklist.
- [x] Update v1.0 release notes with final verification evidence.
- [x] Update milestones with final readiness state.

Acceptance:

- [x] Required gates pass or are explicitly classified.
- [x] Clean-machine rehearsal passes or has a release-owner waiver.
- [x] v1.0 release checklist reflects actual evidence.
- [x] v1.0 release notes do not over-claim.
- [x] Release readiness decision is explicit.

Verification:

- [x] `uv sync --dev`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`
- [x] `uv run pytest tests/unit/test_migrations.py`
- [x] `uv run pytest tests/unit/test_docs_consistency.py`
- [x] `make release-eval`
- [x] `make release-smoke`
- [x] `make release-load-soak`
- [x] `npm install`
- [x] `npm run lint`
- [x] `npm run build`
- [x] `npm run test:e2e`
- [x] `docker compose config`
- [x] `AGENT_KERNEL_API_PORT=8011 AGENT_KERNEL_WEB_PORT=3011 AGENT_KERNEL_POSTGRES_PORT=55432 AGENT_KERNEL_REDIS_PORT=56379 docker compose config`
- [x] clean checkout full-stack Docker Compose rehearsal
- [x] GitHub CI status check
- [x] `git diff --check`

Notes:

- Day 90 can prepare the repository for v1.0 publication, but tagging and
  GitHub Release creation remain explicit user decisions.
- Local release verification passed. Publication still needs the Day 90 commit,
  push, final GitHub CI success, tag, and GitHub Release.
