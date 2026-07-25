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

Risk levels:

```text
read_only
external_write
filesystem_write
network
dangerous
```

Policy decisions:

```text
allow
deny
require_approval
```

## State Transitions

Policy flow:

```text
tool_call_requested -> policy_evaluated -> allowed
tool_call_requested -> policy_evaluated -> denied
tool_call_requested -> policy_evaluated -> approval_required
```

Detailed policy precedence will be completed during Phase 2 implementation.

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
- Allow/deny/require-approval decisions.
- Tool input/output validation.
- Tool timeout.
- Tool result size limit.
- Secret redaction in logs and traces.
- Prompt injection warning baseline for retrieved content.
- Human approval for dangerous tools.
- Audit log for approvals and tool calls.
- No arbitrary shell tool in the default install.

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
- User without permission cannot approve.
- Duplicate approval is rejected.
- Secrets are redacted from logs and traces.
- Tool result size limit is enforced.

## Acceptance Criteria

- Tool execution passes through policy evaluation.
- Risky side effects can require approval.
- Decisions are persisted and auditable.
- Default install does not expose unsafe arbitrary execution.
