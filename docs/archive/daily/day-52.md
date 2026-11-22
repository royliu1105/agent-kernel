# Day 52: Beta Kickoff and Identity RBAC Foundation

## Goal

Start Beta production hardening by defining the identity, workspace, and RBAC
foundation that later API auth, approval authorization, durable execution, and
Web operator workflows can use.

## Scope

- Create the Day 52 daily plan.
- Add a small `kernel-identity` package.
- Define principals, workspaces, memberships, roles, permissions, authorization
  requests, and authorization decisions.
- Add a workspace-scoped RBAC authorizer.
- Add unit tests for role permissions and workspace isolation.
- Update security specs and Beta milestone status.

## Tasks

- [x] Create Day 52 daily plan.
- [x] Add `kernel-identity` workspace package.
- [x] Add identity and workspace domain models.
- [x] Add built-in role and permission model.
- [x] Add workspace-scoped authorizer.
- [x] Add unit tests for owner, operator, viewer, disabled principal, and
  cross-workspace denial behavior.
- [x] Update security spec with Day 52 baseline.
- [x] Update module boundary documentation.
- [x] Update Beta milestone status.

## Acceptance

- [x] Authorization decisions are deterministic and testable without API or
  storage dependencies.
- [x] Workspace membership is required before permissions are granted.
- [x] Viewer cannot perform write actions.
- [x] Operator can review approvals but cannot administer a workspace.
- [x] Disabled principals are denied.

## Verification

- [x] `uv lock --check`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_identity_authorizer.py`
- [x] `git diff --check`

## Notes

- Day 52 does not add API authentication middleware.
- Day 52 does not persist users, workspaces, memberships, API keys, or audit
  events.
- Day 52 does not retrofit existing API routes with authorization checks.
- Day 52 does not implement browser sessions, OIDC, SSO, or multi-tenant
  production isolation.
