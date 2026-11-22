# Day 57: Approval Authorization Enforcement

## Goal

Enforce workspace-scoped authorization for human approval workflows so an
authenticated API key can only list, inspect, approve, reject, or resume with
approvals that belong to its workspace.

## Scope

- Add workspace-aware approval repository reads.
- Filter approval list and get routes by the authenticated API key workspace.
- Filter approval approve and reject mutations by the authenticated API key
  workspace.
- Record the authenticated principal as the approval reviewer.
- Precheck run resume approval ids against the current workspace.
- Add repository and API tests for cross-workspace approval isolation.
- Update Beta milestone and security documentation.

## Tasks

- [x] Add workspace-aware approval repository list/get support.
- [x] Add workspace-aware approval approve/reject support.
- [x] Scope approval list and get API routes.
- [x] Scope approval decision API routes.
- [x] Record authenticated reviewer ids on approval decisions.
- [x] Reject run resume requests that reference approvals outside the current
  workspace.
- [x] Add repository workspace filtering tests.
- [x] Add API cross-workspace approval tests.
- [x] Update docs and milestone progress.

## Acceptance

- [x] Authenticated approval lists only return approvals in the API key
  workspace.
- [x] Approval details from another workspace return `404`.
- [x] Approval approve/reject from another workspace returns `404`.
- [x] Approval decisions made with auth enabled store `reviewed_by`.
- [x] Resume requests cannot use an approval from another workspace.
- [x] Unauthenticated local quickstart behavior remains compatible.

## Verification

- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_api_auth.py tests/unit/test_approval_repository.py`
- [x] `uv run pytest tests/integration/test_api_approvals.py tests/integration/test_api_run_lifecycle.py`

## Notes

- Day 57 does not add `workspace_id` directly to approvals.
- Approval workspace scope is derived from `approval.run_id -> runs.workspace_id`
  to avoid duplicating tenancy state.
- Day 57 does not scope knowledge bases, documents, memory, tool calls, chunks,
  embeddings, or ingestion jobs.
- Day 57 does not add browser login, OIDC, SSO, password auth, approval quorum,
  or multi-reviewer workflows.
