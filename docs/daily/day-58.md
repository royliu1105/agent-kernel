# Day 58: Auth/RBAC Docs and Security Test Closure

## Goal

Close the first Beta Auth/RBAC track by documenting the implemented security
model, adding missing security regression tests, and recording the current
scope and limitations before moving into durable execution work.

## Scope

- Add a canonical Auth/RBAC documentation page.
- Document API key auth enablement, supported headers, roles, permissions,
  object scope, approval authorization, and deferred security work.
- Add missing tests for auth env flag parsing.
- Add missing tests for viewer denial on approval review routes.
- Update docs index and milestone progress.
- Run the focused Auth/RBAC security closure test suite.

## Tasks

- [x] Add `docs/auth-rbac.md`.
- [x] Link Auth/RBAC docs from `docs/README.md`.
- [x] Add API auth env flag parsing tests.
- [x] Add viewer approval review denial test.
- [x] Update Day 58 daily plan and milestone progress.
- [x] Run focused Auth/RBAC security closure tests.

## Acceptance

- [x] Auth/RBAC behavior has a single reader-facing documentation entry point.
- [x] Current roles, permissions, API key behavior, and object-scope boundaries
  are explicit.
- [x] Deferred auth/RBAC limitations are explicit.
- [x] Production operators can see which tests protect the current security
  baseline.
- [x] Security closure tests pass.

## Verification

- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_identity_authorizer.py tests/unit/test_identity_repositories.py tests/unit/test_api_auth.py tests/unit/test_storage_repositories.py tests/unit/test_approval_repository.py tests/integration/test_api_approvals.py tests/integration/test_api_run_lifecycle.py`

## Notes

- Day 58 does not add new auth mechanisms.
- Day 58 does not add browser sessions, OIDC, SSO, password login, custom roles,
  or Web auth UI.
- Day 58 does not scope knowledge bases, documents, memory, tool calls, chunks,
  embeddings, ingestion jobs, evals, or observability records.
- Day 59 starts durable execution and worker leasing.
