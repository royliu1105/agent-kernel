# Day 55: Route-Level Authorization Baseline

## Goal

Add route-level permission checks on top of Day 54 API key authentication so
Beta API routes can reject authenticated principals that do not have the
required workspace role permission.

## Scope

- Add Day 55 daily plan.
- Add permission enforcement dependency for API routes.
- Use API key workspace as the current request workspace for the baseline.
- Add permission checks to existing `/v1/*` routes.
- Add tests for viewer read/write and operator write behavior.
- Update security docs and milestones.

## Tasks

- [x] Create Day 55 daily plan.
- [x] Add route permission dependency.
- [x] Enforce agent read/write permissions.
- [x] Enforce run read/write permissions.
- [x] Enforce approval review permission.
- [x] Enforce memory read/write permissions.
- [x] Enforce knowledge/document read/write permissions.
- [x] Add route authorization tests.
- [x] Update security docs and milestones.

## Acceptance

- [x] API auth remains disabled by default for local quickstart compatibility.
- [x] Authenticated viewers can read allowed resources.
- [x] Authenticated viewers cannot write resources.
- [x] Authenticated operators can write resources.
- [x] Forbidden route access returns `403`.

## Verification

- [x] `uv lock --check`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_api_auth.py tests/unit/test_identity_authorizer.py`
- [x] `uv run pytest tests/integration/test_api_run_lifecycle.py tests/integration/test_api_knowledge_base.py tests/integration/test_api_memory.py tests/integration/test_api_approvals.py`
- [x] `git diff --check`

## Notes

- Day 55 does not retrofit existing resource tables with `workspace_id`.
- Day 55 uses the authenticated API key's workspace as the current request
  workspace.
- Day 55 does not add object-level ownership checks.
- Day 55 does not add Web auth UI, OIDC, SSO, browser sessions, or user
  management.
