# Day 53: Identity Persistence and API Key Foundation

## Goal

Add the storage foundation for Beta authentication and workspace-scoped
authorization so future API middleware can authenticate API keys and load
principal/workspace context from durable state.

## Scope

- Add API key value objects and hashing helpers to `kernel-identity`.
- Add principal, workspace, membership, and API key SQLAlchemy records.
- Add Alembic migration for identity tables.
- Add repositories for principals, workspaces, memberships, and API keys.
- Add unit tests for identity persistence and API key authentication behavior.
- Update security, storage, and milestone documentation.

## Tasks

- [x] Create Day 53 daily plan.
- [x] Add API key domain model and credential issuance result.
- [x] Add API key generation, prefixing, hashing, and verification helpers.
- [x] Add identity storage records.
- [x] Add identity Alembic migration.
- [x] Add principal, workspace, membership, and API key repositories.
- [x] Add repository exports.
- [x] Add unit tests for identity persistence and API key behavior.
- [x] Update security spec and storage architecture docs.
- [x] Update Beta milestone status.

## Acceptance

- [x] Principals and workspaces can be persisted and loaded.
- [x] Workspace memberships can be assigned, updated, and listed.
- [x] Persisted memberships can feed the Day 52 authorizer.
- [x] API keys are stored only as hashes plus non-secret prefixes.
- [x] API key authentication updates `last_used_at`.
- [x] Revoked and expired API keys are rejected.

## Verification

- [x] `uv lock --check`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest tests/unit/test_identity_authorizer.py tests/unit/test_identity_repositories.py tests/unit/test_migrations.py`
- [x] `git diff --check`

## Notes

- Day 53 does not add API auth middleware or route-level authorization.
- Day 53 does not add browser sessions, OIDC, SSO, password login, or user
  management UI.
- Day 53 does not add audit event tables.
- Day 53 does not retrofit existing resource tables with `workspace_id`; that
  belongs to later Beta slices.
