# Feature Spec: Security Policy

## Goal

Define the baseline security model for tool permissions, approvals, secret redaction, auth, auditability, and safe runtime behavior.

## Non-Goals

- Full OIDC/SSO in v0.1.
- OPA/Rego policy engine in v0.1.
- Full container sandbox in v0.1.
- Enterprise multi-tenant isolation in v0.1.

## User Stories

- As an admin, I can restrict which tools an agent may use.
- As an operator, I can require approval for risky actions.
- As a maintainer, I can audit who approved a tool call.
- As a user, I can trust that secrets are not logged by default.

## Domain Model

Initial entities:

- `Policy`
- `PolicyDecision`
- `Tool`
- `ToolCall`
- `Approval`
- `AuditEvent`
- `ApiKey`
- `User`
- `Project`

Day 52 identity baseline:

- `kernel-identity` owns infrastructure-free identity, workspace, and RBAC
  primitives.
- `Principal` represents an authenticated actor and is either `user` or
  `service`.
- `Workspace` is the primary Beta resource boundary.
- `WorkspaceMembership` assigns one built-in role to one principal in one
  workspace.
- Built-in roles are `owner`, `admin`, `operator`, and `viewer`.
- Permissions are fine-grained strings such as `run:read`, `run:write`,
  `approval:review`, `knowledge:write`, and `workspace:admin`.
- `WorkspaceAuthorizer` makes deterministic authorization decisions from a
  principal, workspace id, permission, and membership set.
- Workspace membership is required before any workspace permission is granted.
- Disabled principals are denied even if a membership exists.
- Day 52 does not persist users, workspaces, memberships, API keys, or audit
  events.
- Day 52 does not add API auth middleware, browser sessions, OIDC, SSO, or
  route-level enforcement.

Day 53 identity persistence baseline:

- `ApiKey` stores only `key_prefix`, `key_hash`, lifecycle status, timestamps,
  workspace id, and principal id.
- `ApiKeyCredential` returns the plaintext key only at issue time.
- API key hashes use SHA-256 over high-entropy generated secrets.
- API key comparison uses constant-time digest comparison.
- API key issuance requires the principal and workspace to exist and the
  principal to be a member of that workspace.
- API key authentication rejects revoked and expired keys.
- Successful API key authentication updates `last_used_at`.
- Principals, workspaces, memberships, and API keys are persisted in Postgres
  through SQLAlchemy models and Alembic migration `0009_identity_tables`.
- Day 53 does not add route-level API authentication middleware, browser
  sessions, OIDC, SSO, password login, or user management UI.
- Day 53 does not retrofit existing resource tables with `workspace_id`.

Day 54 API authentication baseline:

- API key authentication is enforced by middleware when
  `AGENT_KERNEL_API_KEY_AUTH_ENABLED` is true.
- Local development keeps API key authentication disabled by default.
- `/healthz` remains public so container and load-balancer health checks do not
  require secrets.
- API keys can be supplied through `Authorization: Bearer <key>` or
  `X-Agent-Kernel-Api-Key`.
- Valid API keys load a request auth context with principal, API key, and
  workspace memberships.
- Missing, invalid, revoked, expired, or disabled-principal API keys return
  `401 Unauthorized`.
- Day 54 does not add route-level permission checks.
- Day 54 does not add browser sessions, OIDC, SSO, password login, or Web auth
  UI.

Day 55 route authorization baseline:

- API routes use FastAPI dependencies to require the permission needed for the
  operation.
- The authenticated API key workspace is treated as the current request
  workspace.
- `WorkspaceAuthorizer` evaluates the authenticated principal, memberships,
  current workspace, and required permission.
- Missing permissions return `403 Forbidden`.
- Agent routes require `agent:read` or `agent:write`.
- Run routes require `run:read` or `run:write`.
- Approval routes require `approval:review`.
- Memory routes require `memory:read` or `memory:write`.
- Knowledge, document, ingestion, chunk, embedding, and retrieval routes require
  `knowledge:read` or `knowledge:write`.
- Day 55 does not retrofit existing resource tables with `workspace_id`.
- Day 55 does not add object-level ownership checks.

Day 56 workspace scope baseline:

- `Agent` and `Run` now carry optional `workspace_id`.
- `agents.workspace_id` and `runs.workspace_id` are nullable for compatibility
  with existing local development rows.
- Authenticated agent creation stores the authenticated API key workspace id.
- Authenticated run creation stores the authenticated API key workspace id.
- Agent and run reads are filtered by the authenticated API key workspace when
  auth is enabled.
- Runs cannot be created for an agent outside the current authenticated
  workspace.
- Existing unauthenticated local quickstart behavior remains compatible.
- Day 56 does not scope knowledge bases, documents, memory, approvals, tool
  calls, run events, chunks, embeddings, or ingestion jobs.

Risk levels:

```text
read_only
external_write
filesystem_write
network
dangerous
```

Day 8 risk-level baseline:

- Tools expose a `risk_level` in `ToolMetadata`.
- The first built-in tool is `read_only`.
- Day 8 does not make allow/deny/approval decisions.
- Policy evaluation begins after the tool contract and executor are stable.
- Default Day 8 tools must not perform network access, filesystem writes, shell execution, or other
  side effects.

Policy decisions:

```text
allow
deny
require_approval
```

Day 9 policy baseline:

- `PolicyDecisionType` defines `allow`, `deny`, and `require_approval`.
- `PolicyDecision` records decision, reason, risk level, and tool name.
- `ToolPolicy` contains explicit tool-name decisions and risk-level decisions.
- `ToolPolicyEvaluator` evaluates `ToolMetadata`.
- Explicit tool-name decisions override risk-level defaults.
- Default risk policy:
  - `read_only` -> `allow`
  - `external_write` -> `require_approval`
  - `filesystem_write` -> `require_approval`
  - `network` -> `require_approval`
  - `dangerous` -> `deny`
- `PolicyAwareToolExecutor` evaluates policy before delegating to `ToolExecutor`.
- Denied tools are not executed.
- Approval-required tools are not executed on Day 9.
- Day 9 does not persist approvals, create audit events, or move runs to `waiting_approval`.

Day 10 audit baseline:

- Policy decisions can be recorded against persisted tool calls.
- `policy_evaluated` run events capture decision, reason, status, and approval requirement.
- `tool_call_requested`, `tool_call_completed`, and `tool_call_failed` events provide the first
  tool audit timeline.
- Day 10 audit is scoped to run events and tool call records.
- A separate audit event table and external audit sink are deferred.
- Approval decision audit is deferred until approval persistence exists.

Day 11 approval audit baseline:

- Approval requests append `approval_requested`.
- Approval decisions append `approval_approved` or `approval_rejected`.
- Approval decisions record reviewer and decision note fields for future auth integration.
- Duplicate approval decisions are rejected.
- Day 11 still uses run events as the audit timeline.
- A dedicated audit table remains deferred.

Day 12 approval execution baseline:

- Approval-required tools are not executed before approval.
- Runtime resume executes the original persisted tool call arguments.
- Resume callers cannot provide replacement tool arguments.
- Rejected approvals fail the waiting run safely.
- Approval wait/resume/failure transitions are auditable through run events.
- Auth and role enforcement remain deferred, but reviewer fields stay in approval records.

Day 13 retry/fallback security baseline:

- Automatic tool retry is limited to safe/read-only tools.
- Side-effecting risk levels are not automatically retried.
- Approval-required tools pause instead of retrying.
- Rejected approvals fail instead of retrying.
- Invalid tool arguments are not retried.
- Provider retry/fallback is allowed for explicitly retryable provider errors.
- Fallback models must be explicitly configured in run input.
- Retry and fallback attempts are auditable through run events.

## State Transitions

Policy flow:

```text
tool_call_requested -> policy_evaluated -> allowed
tool_call_requested -> policy_evaluated -> denied
tool_call_requested -> policy_evaluated -> approval_required
approval_required -> approval_requested -> run_waiting_approval
approval_approved -> run_resuming -> running
approval_rejected -> run_failed
retryable_safe_failure -> retry_event -> retry_attempt
retryable_provider_failure -> retry_or_fallback_event -> retry_or_fallback_attempt
```

Detailed policy precedence will be completed during Phase 2 implementation.

Day 9 precedence:

```text
explicit tool-name policy
-> risk-level policy
-> require_approval fallback
```

## API / CLI

Policy is configured through agent and tool configuration in v0.1.

Expected related API:

```http
GET   /v1/tools
PATCH /v1/tools/{tool_name}
PATCH /v1/agents/{agent_id}
GET   /v1/approvals
POST  /v1/approvals/{approval_id}/approve
POST  /v1/approvals/{approval_id}/reject
```

## Failure Modes

- Tool has no risk level.
- Policy decision is ambiguous.
- User lacks permission.
- Secret appears in tool output.
- Prompt injection attempts to override policy.
- Approval is replayed or duplicated.

## Security

MVP requirements:

- API key auth.
- User/admin/service roles.
- Tool risk levels.
- Safe read-only tool baseline.
- Allow/deny/require-approval decisions.
- Tool input/output validation.
- Tool timeout.
- Tool result size limit.
- Secret redaction in logs and traces.
- Prompt injection warning baseline for retrieved content.
- Human approval for dangerous tools.
- Audit log for approvals and tool calls.
- No arbitrary shell tool in the default install.

Beta security baseline:

- Identity and workspace scope must be explicit before route-level
  authorization is added.
- Permission checks should return auditable decisions with principal id,
  workspace id, permission, role, result, and reason.
- Service principals must still be members of a workspace before they can act
  on workspace-scoped resources.
- Route-level authorization should be added after storage persistence exists for
  principals, workspaces, memberships, and API keys.
- Plaintext API keys must never be persisted.

## Observability

- Policy evaluation span.
- Policy decision event.
- Audit event.
- Redaction warning.
- Denied tool call metric.
- Approval-required metric.

## Test Plan

- Safe tool is allowed.
- Dangerous tool requires approval.
- Denied tool is not executed.
- Dangerous tool is denied by default.
- Write and network tools require approval by default.
- Explicit tool-name rules override risk-level defaults.
- Approval-required tools are not executed before approval exists.
- Policy decisions are visible in the run timeline.
- Tool call success and failure are visible in the run timeline.
- User without permission cannot approve.
- Workspace membership is required for all workspace-scoped permissions.
- Viewer role is read-only.
- Operator role can operate runs and approvals without workspace admin rights.
- Disabled principals are denied.
- API keys are persisted as hashes and non-secret prefixes only.
- Revoked and expired API keys cannot authenticate.
- Missing or invalid API keys are rejected when API key auth is enabled.
- Authenticated principals without a required route permission receive `403`.
- Duplicate approval is rejected.
- Secrets are redacted from logs and traces.
- Tool result size limit is enforced.

## Acceptance Criteria

- Tool execution passes through policy evaluation.
- Risky side effects can require approval.
- Decisions are persisted and auditable.
- Default install does not expose unsafe arbitrary execution.
