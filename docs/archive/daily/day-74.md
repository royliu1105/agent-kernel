# Day 74: Persisted Eval Runs, Eval API, and Live Web Views

Goal:

Turn deterministic eval reports into durable operator-visible records that can
be published through the API and inspected in the Web Workbench.

Scope:

- Add persisted eval run domain and storage model.
- Add database migration for eval run reports.
- Add EvalRun repository operations.
- Add eval run API create/list/get endpoints.
- Add CLI `eval report --publish` flow.
- Add live Web eval run list/detail integration.
- Update specs, production docs, Web scope copy, and Beta milestone tracking.

Tasks:

- [x] Add `EvalRun` and `EvalRunStatus` domain models.
- [x] Add `eval_runs` storage model and migration.
- [x] Add `EvalRunRepository`.
- [x] Add eval run API schemas and endpoints.
- [x] Add CLI publish option for local eval reports.
- [x] Add Web API proxy for eval run list.
- [x] Replace eval Workbench fixture path with live eval runs when available.
- [x] Add storage, API, CLI, and Web smoke tests.
- [x] Update eval and production docs.
- [x] Update Beta milestone progress.

Acceptance:

- [x] Eval reports can be persisted with pass/fail counts and full report JSON.
- [x] API clients can create, list, and inspect eval runs.
- [x] CLI can run a deterministic RAG eval and publish the report.
- [x] Workbench eval view can render persisted eval runs from the backend.
- [x] Failed eval reports are visible as failed persisted runs.
- [x] Day 74 does not execute arbitrary eval datasets on the server.

Verification:

- [x] `uv run pytest tests/unit/test_storage_repositories.py tests/integration/test_api_evals.py tests/unit/test_cli_commands.py`
- [x] `npm --prefix apps/web run lint`
- [x] `npm --prefix apps/web run test:e2e`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`
- [x] `git diff --check`

Notes:

- The API persists submitted eval reports. It does not yet schedule remote eval
  execution, upload datasets, run LLM-as-judge, or sandbox eval code.
- Worker-side HTTP metrics and eval job queues remain later hardening work.
