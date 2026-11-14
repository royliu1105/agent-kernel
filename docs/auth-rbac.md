# Auth and RBAC

This document is the current source of truth for Agent Kernel
API authentication, workspace-scoped authorization, and current security test
coverage.

## Current Status

Auth/RBAC is implemented for self-hosted deployments. The current boundary
includes post-v1.0 hardening; historical release notes describe older tags.

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
- Knowledge-base ownership and derived document/chunk/embedding/
  ingestion scope, including trusted Run scope in `kb_search`.
- Workspace-owned memory and eval records, with legacy NULL-owned records hidden
  from authenticated workspaces.
- Run-derived tool calls, run events, and workspace-filtered usage APIs.
- Separate conditional monitoring-token authorization for API metrics and an
  opt-in private Worker metrics listener.

Still deferred:

- Browser sessions.
- Password login.
- OIDC or SSO.
- User management Web UI.
- Multi-workspace selector in Web.
- Fine-grained custom roles.
- Public hosted SaaS tenant isolation guarantees.

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

The CLI reads `AGENT_KERNEL_API_KEY` from its environment and sends the preferred
header for JSON requests and multipart uploads. Load it through a secret manager
or an untracked local environment; do not commit it or expose it in
`NEXT_PUBLIC_*`. Web proxy authentication is separate and is not added by P1.1.
Use HTTPS outside localhost and send credentials only to a trusted API URL.

When auth is enabled:

- `/healthz` and `/readyz` stay public probe endpoints.
- `/metrics` uses a separate monitoring-token check, not workspace-key auth.
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

- Primary self-hosted application resource boundary.
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
| `admin` | Full workspace control for the current self-hosted baseline. |
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
| `eval:read` | Eval run read routes. |
| `eval:write` | Eval run persistence routes. |

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
| Knowledge base | `knowledge_bases.workspace_id`, set from authenticated context on create. |
| Document | Derived through `documents.knowledge_base_id -> knowledge_bases.workspace_id`. |
| Chunk / embedding / ingestion job | Derived through their document and its knowledge base. |
| Memory | `memory_items.workspace_id`; business `scope` strings never grant access. Source runs are validated against the same workspace. |
| Eval | `eval_runs.workspace_id`; report/list/detail use authenticated workspace. |
| Tool call / run event | Derived through Run; scoped repository queries and API run prechecks. |
| Usage summary | `GET /v1/usage` aggregates only the authenticated workspace; requires `run:read`. |

Knowledge access rules:

- Authenticated list queries exclude foreign and NULL-owned knowledge bases.
- All direct child IDs and mutation paths check ownership before object-store
  access, embedding calls or writes. Missing/foreign resources return 404;
  insufficient role permission remains 403.
- `kb_search` gets immutable context from the persisted Run, for direct,
  provider-native, queued worker and approval-resume paths. Tool arguments
  cannot override workspace scope. A missing/inaccessible KB fails the run
  without retry or passing a tool result to a follow-up model request.
- Sources and parsed artifacts must use their KB/document/job namespaces.
  Invalid legacy references are hidden in scoped mode and must be re-uploaded.
- `workspace_id=None` is trusted local/operator access, not a tenant scope.
  Never expose auth-disabled API instances publicly or share one across tenants.
- No knowledge update/delete/ownership-transfer HTTP endpoints exist in this
  version. Database ownership assignment is an offline operator action; stop
  API/workers while doing it. See [Upgrade policy](upgrade-migration-policy.md#knowledge-ownership-upgrade-p11).

Memory and eval legacy NULL-owned records are quarantined like knowledge bases.
Runtime memory retrieval uses the persisted Run workspace, not user/model input.
API responses expose ownership for inspection, not as a client-selectable scope.

Operational metrics are process-wide, low-cardinality and not tenant data APIs.
API `/metrics` requires `AGENT_KERNEL_MONITORING_TOKEN` whenever API-key auth is
enabled or a token is configured. Auth enabled without a token fails closed
with HTTP 401; only auth disabled with no token allows unauthenticated scraping.
Use `Authorization: Bearer <monitoring-token>`, not an ordinary workspace key.
Worker metrics are independently opt-in and require a token for non-loopback
binds. See [Production Configuration](production-config.md#worker-metrics).
Protect logs/traces at the deployment layer and do not give tenant users
collector access. `/healthz` and sanitized dependency `/readyz` remain probe
endpoints, not record-query interfaces.

Optional `AGENT_KERNEL_RATE_LIMIT_REQUESTS` enables a shared Redis fixed window
for authenticated requests per workspace, across keys and API replicas. Denied
requests return 429 with `Retry-After`; unavailable Redis returns 503. Limits do
not replace role checks, tool approvals, an ingress limit on unauthenticated
traffic, or token/cost budgets. Default zero disables this policy explicitly.
Auth-disabled mode cannot enable any admission limit.

`AGENT_KERNEL_RATE_LIMIT_PRINCIPAL_REQUESTS` and
`AGENT_KERNEL_RATE_LIMIT_API_KEY_REQUESTS` independently enable per-principal and
per-key quotas. Principal quotas are workspace-local, shared across the user's
keys, not global across unrelated tenants. All enabled buckets use the same
window and one atomic Redis operation: a denial or invalid bucket charges none
of them. Changing a quota starts its new policy bucket. This deployment supports
standalone Redis, not Redis Cluster multi-key scripting. Quotas do not protect
against Redis failover losing recently admitted counters.

`GET /v1/usage/breakdown?group_by=workspace|run|principal|model` requires
`run:read` and always applies the authenticated workspace. Optional `run_id`
narrows that scope, never expands it; `limit` bounds groups (1..1000, default100).
Run initiators come from authenticated principals, never model/user input JSON.
Model attribution uses persisted per-response usage, including charged responses
before tool failure/approval. These are estimates, not provider invoices; failed
requests with no usage response have unknown billable cost. Local and legacy
initiators remain null, and migrated historical model usage is `unknown`.

External tools additionally require an operator-owned workspace allowlist and
run through the same policy, approval and persisted audit path. These self-hosted
boundaries are not a claim of hostile public multi-tenant SaaS isolation.

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
| Knowledge child IDs, mutations and legacy quarantine | `tests/unit/test_knowledge_workspace_scope.py` |
| Knowledge API / runtime / worker / approval-resume isolation | `tests/integration/test_knowledge_workspace_isolation.py` |
| Model workspace spoofing | `tests/unit/test_kb_search_tool.py` |
| CLI key transport | `tests/unit/test_cli_commands.py` |
| PostgreSQL legacy upgrade and ownership assignment | `tests/unit/test_migrations.py` |
| Real pgvector scope, fresh/legacy upgrade | `tests/integration/test_pgvector_workspace_scope.py` (opt-in locally; required in CI) |
| Memory/eval isolation, legacy quarantine, and trusted runtime memory scope | `tests/integration/test_memory_eval_isolation.py` |
| Run-derived tool/event isolation and workspace usage | `tests/integration/test_operational_scope.py` |
| API monitoring-token separation | `tests/unit/test_api_auth.py` |
| Worker monitoring-token validation and listener lifecycle | `tests/unit/test_observability_http.py` |

Recommended security regression command:

```bash
uv run pytest \
  tests/unit/test_identity_authorizer.py \
  tests/unit/test_identity_repositories.py \
  tests/unit/test_api_auth.py \
  tests/unit/test_storage_repositories.py \
  tests/unit/test_approval_repository.py \
  tests/unit/test_observability_http.py \
  tests/integration/test_api_approvals.py \
  tests/integration/test_api_run_lifecycle.py \
  tests/integration/test_knowledge_workspace_isolation.py \
  tests/integration/test_memory_eval_isolation.py \
  tests/integration/test_operational_scope.py
```

## Production Guidance

Do:

- Enable API key auth for shared or deployed environments.
- Issue API keys to service principals for automation.
- Rotate API keys periodically.
- Treat plaintext API keys as secrets.
- Run route and workspace scope tests before release.

Do not:

- Treat these self-hosted controls as public multi-tenant SaaS certification.
- Store plaintext API keys.
- Add broad write routes without permission checks.
- Add new workspace-scoped resources without repository and API cross-workspace
  tests.

## Remaining Hardening Steps

Follow the [capability hardening plan](capability-hardening-plan.md):

- Keep knowledge, memory, eval, and Run-derived resource isolation regressions
  passing, including PostgreSQL/pgvector checks in CI.
- Review new resources and mutation paths for authenticated scope before reads,
  writes, object-store access, or provider calls.
- Add Web authentication or API key configuration for live Workbench calls.
- Add audit export or persisted authorization-decision records if production
  operators need compliance-style review.

See [Security Hardening Checklist](security-hardening.md) for the release-level
security gates and operator checklist.
