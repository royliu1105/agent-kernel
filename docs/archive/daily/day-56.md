# Day 56: Workspace Scope Retrofit Plan and First Scoped Resources

## Goal

Start object-level workspace scoping by adding `workspace_id` to the first
execution-entry resources: agents and runs.

## Scope

- Add Day 56 daily plan.
- Add optional `workspace_id` to agent and run domain models.
- Add nullable `workspace_id` columns to `agents` and `runs`.
- Add Alembic migration for agent/run workspace scope.
- Update repositories to create and read agents/runs within a workspace.
- Update API create/read paths to use the authenticated API key workspace.
- Add tests for scoped repository and API behavior.
- Update docs and milestones.

## Tasks

- [x] Create Day 56 daily plan.
- [x] Add `workspace_id` to Agent and Run models.
- [x] Add storage columns and migration.
- [x] Add scoped repository reads.
- [x] Add API workspace-aware agent create/read.
- [x] Add API workspace-aware run create/read.
- [x] Add repository scoped tests.
- [x] Add API cross-workspace tests.
- [x] Update security/storage docs and milestones.

## Acceptance

- [x] Authenticated agent creation stores the API key workspace id.
- [x] Authenticated run creation stores the API key workspace id.
- [x] Agents cannot be read from another authenticated workspace.
- [x] Runs cannot be read from another authenticated workspace.
- [x] Runs cannot be created for an agent outside the current workspace.
- [x] Local default unauthenticated quickstart remains compatible.

## Verification

- [x] `uv lock --check`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_api_auth.py tests/unit/test_storage_repositories.py tests/unit/test_migrations.py`
- [x] `uv run pytest tests/integration/test_api_run_lifecycle.py`
- [x] `git diff --check`

## Notes

- Day 56 only scopes agents and runs.
- Existing rows keep nullable `workspace_id` for compatibility.
- Knowledge bases, documents, memory, approvals, tool calls, run events, chunks,
  embeddings, and ingestion jobs are scoped in later Beta slices.
