# Auth and RBAC

This document is the Beta source of truth for Agent Kernel API authentication,
workspace-scoped authorization, and current security test coverage.

## Current Status

Auth/RBAC is a Beta production-hardening track.

Implemented:

- Identity domain primitives.
- Workspace domain primitives.
- Workspace membership roles.
- Fine-grained permissions.
- Workspace-scoped RBAC authorizer.
- Persisted principals, workspaces, memberships, and hashed API keys.
- Opt-in API key authentication middleware.
- Route-level permission checks.
- Workspace-scoped agents and runs.
- Workspace-scoped approval access and approval decisions.

Still deferred:

- Browser sessions.
- Password login.
- OIDC or SSO.
- User management Web UI.
- Multi-workspace selector in Web.
- Fine-grained custom roles.
- Enterprise tenant isolation guarantees.
- Workspace scoping for knowledge bases, documents, memory, tool calls, chunks,
  embeddings, ingestion jobs, evals, and observability records.

## Enable API Key Auth

API key authentication is disabled by default for local quickstart
compatibility.

Enable it with:

```bash
AGENT_KERNEL_API_KEY_AUTH_ENABLED=true
```

Accepted truthy values:

```text
1
true
yes
on
```

Everything else is treated as disabled.

## API Key Transport

Preferred header:

```http
Authorization: Bearer <agent-kernel-api-key>
```

Supported alternative:

```http
X-Agent-Kernel-Api-Key: <agent-kernel-api-key>
```

When auth is enabled:

- `/healthz` stays public.
- Missing API keys return `401`.
- Invalid, revoked, expired, or disabled-principal keys return `401`.
- Valid keys load the principal, API key, workspace id, and memberships into the
  request auth context.

## Identity Model

Principal:

- Represents an authenticated actor.
- Can be `user` or `service`.
- Disabled principals cannot authorize any permission.

Workspace:

- Primary Beta resource boundary.
- API keys are issued inside one workspace.
- The API key workspace is the current request workspace.

Membership:

- Assigns one principal to one workspace.
- Grants one built-in role.
- Workspace membership is required before any workspace permission is granted.

API key:

- Stores `key_prefix`, `key_hash`, status, workspace id, principal id, and
  timestamps.
- Never stores plaintext keys.
- Plaintext key material is returned only at issuance time.
- Authentication updates `last_used_at`.

## Roles

Built-in roles:

| Role | Intent |
| --- | --- |
| `owner` | Full workspace control. |
| `admin` | Full workspace control for the Beta baseline. |
| `operator` | Operate agents, runs, approvals, tools, knowledge, memory, and evals without workspace admin rights. |
| `viewer` | Read-only access to inspect workspace state. |

## Permissions

Current permissions:

| Permission | Used For |
| --- | --- |
| `workspace:read` | Workspace inspection. |
| `workspace:admin` | Workspace administration. |
| `agent:read` | Agent read routes. |
| `agent:write` | Agent create/write routes. |
| `run:read` | Run and run-event read routes. |
| `run:write` | Run create, queue, cancel, and resume routes. |
| `approval:review` | Approval list, detail, approve, and reject routes. |
| `tool:execute` | Future direct tool execution boundaries. |
| `knowledge:read` | Knowledge, document, chunk, embedding, and retrieval read routes. |
| `knowledge:write` | Knowledge, document, ingestion, chunk, and indexing write routes. |
| `memory:read` | Memory read routes. |
| `memory:write` | Memory create/delete routes. |
| `eval:read` | Future eval read routes. |
| `eval:write` | Future eval write routes. |

## Route Authorization

FastAPI routes use permission dependencies. When auth is disabled, these
dependencies are no-ops so local quickstart paths stay simple.

When auth is enabled:

- Agent write routes require `agent:write`.
- Agent read routes require `agent:read`.
- Run write routes require `run:write`.
- Run read routes require `run:read`.
- Approval routes require `approval:review`.
- Memory read/write routes require `memory:read` or `memory:write`.
- Knowledge, document, chunk, ingestion, embedding, and retrieval routes require
  `knowledge:read` or `knowledge:write`.

Denied permissions return `403`.

## Object Scope

Current scoped resources:

| Resource | Scope Model |
| --- | --- |
| Agent | `agents.workspace_id` is populated on authenticated create and filtered on read. |
| Run | `runs.workspace_id` is populated on authenticated create and filtered on read/write prechecks. |
| Approval | Derived through `approvals.run_id -> runs.workspace_id`. |

Current unscoped resources:

- Knowledge bases.
- Documents.
- Document chunks.
- Embeddings.
- Ingestion jobs.
- Memory items.
- Tool calls.
- Run events beyond run prechecks.
- Eval records.
- Observability records.

These remain Beta follow-ups and should not be treated as production
multi-tenant isolation yet.

## Approval Authorization

Approvals do not carry a separate `workspace_id`.

The API derives approval scope through the approval's run:

```text
approval -> run -> workspace
```

When auth is enabled:

- Approval lists return only approvals in the current workspace.
- Approval detail returns `404` outside the current workspace.
- Approval approve/reject returns `404` outside the current workspace.
- Approval decisions store the current principal as `reviewed_by`.
- Run resume rejects approval ids outside the current workspace before runtime
  resume execution.

## Security Test Matrix

Auth and RBAC test anchors:

| Behavior | Test File |
| --- | --- |
| Role permission decisions | `tests/unit/test_identity_authorizer.py` |
| Identity persistence and API key hashing | `tests/unit/test_identity_repositories.py` |
| API auth middleware and env flag | `tests/unit/test_api_auth.py` |
| Route-level permission denial | `tests/unit/test_api_auth.py` |
| Agent/run workspace isolation | `tests/unit/test_api_auth.py`, `tests/unit/test_storage_repositories.py` |
| Approval workspace isolation | `tests/unit/test_api_auth.py`, `tests/unit/test_approval_repository.py` |
| Approval API compatibility | `tests/integration/test_api_approvals.py` |
| Resume API compatibility | `tests/integration/test_api_run_lifecycle.py` |

Recommended Day 58 security closure command:

```bash
uv run pytest \
  tests/unit/test_identity_authorizer.py \
  tests/unit/test_identity_repositories.py \
  tests/unit/test_api_auth.py \
  tests/unit/test_storage_repositories.py \
  tests/unit/test_approval_repository.py \
  tests/integration/test_api_approvals.py \
  tests/integration/test_api_run_lifecycle.py
```

## Production Guidance

Do:

- Enable API key auth for shared or deployed environments.
- Issue API keys to service principals for automation.
- Rotate API keys periodically.
- Treat plaintext API keys as secrets.
- Run route and workspace scope tests before release.

Do not:

- Deploy as a public multi-tenant SaaS on the current Beta baseline.
- Store plaintext API keys.
- Add broad write routes without permission checks.
- Add new workspace-scoped resources without repository and API cross-workspace
  tests.

## Next Hardening Steps

Upcoming Beta slices should:

- Scope knowledge bases and documents.
- Scope memory records.
- Decide whether tool calls need direct `workspace_id` or should stay derived
  through runs.
- Add Web authentication or API key configuration for live Workbench calls.
- Add audit export or persisted authorization-decision records if production
  operators need compliance-style review.
