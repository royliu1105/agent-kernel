# Day 83: Load and Soak Test Scenarios

Goal:

Define the v1.0 release candidate load and soak scenarios, and add a small
deterministic local load gate that maintainers can run without credentials or
external infrastructure.

Scope:

- Add a maintainer-facing `make release-load-soak` command.
- Add an in-process queued-worker burst scenario.
- Document local, infrastructure-backed, and manual long-running load/soak
  scenario boundaries.
- Update quality strategy, docs index, daily index, and milestone tracking.
- Do not make long-running soak, live-provider, pgvector, S3/MinIO, or browser
  e2e load tests default CI gates.

Tasks:

- [x] Check current git status before editing.
- [x] Review existing worker/runtime queue behavior.
- [x] Add deterministic worker burst load scenario.
- [x] Add `make release-load-soak`.
- [x] Add unit coverage for the load scenario helper.
- [x] Document load and soak scenarios.
- [x] Update quality strategy, docs index, daily index, and milestones.

Acceptance:

- [x] Maintainers can run a quick load/soak gate with one command.
- [x] The default gate is deterministic and credential-free.
- [x] The default gate exercises durable run creation, queue transitions,
  worker polling, model execution, persisted terminal state, and empty queue
  behavior.
- [x] Longer infrastructure-backed scenarios are documented but not default CI.
- [x] Day 83 does not introduce paid provider calls or external service
  dependencies.

Verification:

- [x] `make release-load-soak`
- [x] `uv run pytest tests/unit/test_release_load_soak.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `git diff --check`

Notes:

- Day 83 defines the load/soak release surface. Day 84-85 still own
  clean-machine rehearsal planning and fixes.
