# Day 54: API Key Authentication Middleware

## Goal

Add an opt-in API key authentication middleware so Beta deployments can require
hashed API keys before serving Agent Kernel API routes.

## Scope

- Add Day 54 daily plan.
- Add API auth middleware and auth context.
- Support `Authorization: Bearer <key>`.
- Support `X-Agent-Kernel-Api-Key`.
- Keep `/healthz` public.
- Keep local development auth disabled by default.
- Add tests for missing, invalid, valid, disabled-principal, and default-off
  behavior.
- Update docs and milestones.

## Tasks

- [x] Create Day 54 daily plan.
- [x] Add API key authentication middleware.
- [x] Add request auth context model.
- [x] Add environment flag for opt-in auth enforcement.
- [x] Support Bearer token and Agent Kernel API key headers.
- [x] Keep `/healthz` exempt from auth.
- [x] Add API auth unit tests.
- [x] Update environment example.
- [x] Update production configuration docs.
- [x] Update security docs and milestones.

## Acceptance

- [x] API auth is disabled by default for local quickstart compatibility.
- [x] Missing API keys are rejected when auth is enabled.
- [x] Invalid, revoked, expired, or disabled-principal API keys are rejected.
- [x] Valid API keys can call existing API routes when auth is enabled.
- [x] Successful authentication updates API key usage through the repository.

## Verification

- [x] `uv lock --check`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_api_auth.py tests/unit/test_identity_repositories.py`
- [x] `git diff --check`

## Notes

- Day 54 does not add route-level permission checks.
- Day 54 does not retrofit resource tables with `workspace_id`.
- Day 54 does not add browser sessions, OIDC, SSO, password login, or Web auth
  UI.
