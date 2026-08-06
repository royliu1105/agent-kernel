# Security Hardening Checklist

This checklist defines the v1.0 release candidate security hardening baseline
for self-hosted Agent Kernel deployments.

It is not a public hosted SaaS security certification. Agent Kernel can be used
for self-hosted pilots and internal production trials when operators apply the
deployment controls below.

## Release Gate Summary

Block v1.0 release if any of these are false:

- API authentication can be enabled for `/v1/*` routes.
- Route-level permissions are enforced when authentication is enabled.
- Workspace-scoped agent, run, and approval access is tested.
- Plaintext API keys are never persisted.
- Sensitive structured-log fields are redacted.
- Risky tools require approval or are denied by policy before execution.
- Rejected approvals fail safely instead of executing the tool.
- Safe-tool retries do not retry side-effecting tools automatically.
- Stable public API and CLI security behavior is documented.
- Known unscoped secondary resources are documented as v1.0 limitations or
  fixed before final release.

## Implemented Security Controls

Authentication and authorization:

- Optional API-key authentication with `AGENT_KERNEL_API_KEY_AUTH_ENABLED=true`.
- API keys accepted through `Authorization: Bearer <key>` and
  `X-Agent-Kernel-Api-Key`.
- Hashed API key storage with plaintext key material returned only at issuance.
- Disabled principals, revoked keys, and expired keys are rejected.
- Built-in workspace roles: `owner`, `admin`, `operator`, and `viewer`.
- Fine-grained route permissions for agents, runs, approvals, knowledge,
  memory, and evals.
- Route-level authorization returns `403` for missing permissions.

Workspace scope:

- Authenticated agent creation stores the API key workspace id.
- Authenticated run creation stores the API key workspace id.
- Agent and run reads are filtered by authenticated workspace.
- Approval list, detail, approve, reject, and run-resume prechecks derive scope
  through `approval -> run -> workspace`.

Tool and approval safety:

- Tool metadata carries a risk level.
- Default policy allows `read_only`, requires approval for external writes,
  filesystem writes, and network tools, and denies `dangerous`.
- Denied tools are not executed.
- Approval-required tools pause before execution.
- Resume executes the original persisted tool arguments.
- Resume callers cannot replace tool arguments.
- Rejected approvals fail the waiting run safely.
- Automatic tool retry is limited to safe/read-only tools.

Auditability and observability:

- Run events preserve policy decisions, tool-call requests, tool completion,
  tool failures, approval requests, approval decisions, retries, and fallback
  attempts.
- Tool calls are persisted.
- Approval records are persisted.
- Trace IDs link runs, events, tool calls, approvals, logs, and eval runs.
- Structured logging redacts sensitive field names.

Deployment controls:

- `/healthz` and `/metrics` are public from the application perspective but
  should be network-protected in production.
- Postgres, Redis, and object storage should stay on private networks.
- Secrets should be injected through deployment secret stores.
- Backup guidance treats database and object storage as sensitive.

## Known v1.0 RC Limitations

These are not hidden. Release reviewers must decide whether they are acceptable
for v1.0 final:

- API-key auth is disabled by default for local quickstart compatibility.
- There is no browser login, OIDC, SSO, or password auth.
- The Web Workbench does not provide a full user-management UI.
- Public hosted SaaS tenant isolation is out of scope.
- Knowledge bases, documents, document chunks, embeddings, ingestion jobs,
  memory items, tool calls, eval records, and observability records still need
  a final object-scope audit.
- `/metrics` has no built-in authentication and must be protected by network or
  gateway controls.
- Secrets manager integration is deployment-specific.
- Remote sandbox execution is not implemented.
- Browser session automation is not implemented.
- Dependency advisories must continue to be reviewed before release.

## Operator Checklist

Before exposing a deployment to shared users:

- [ ] Set `AGENT_KERNEL_ENV=production`.
- [ ] Set `AGENT_KERNEL_API_KEY_AUTH_ENABLED=true`.
- [ ] Use PostgreSQL, not SQLite.
- [ ] Keep Postgres private.
- [ ] Keep Redis private.
- [ ] Keep object storage private.
- [ ] Put API and Web behind HTTPS.
- [ ] Protect `/metrics` with network or gateway controls.
- [ ] Store `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, AWS credentials, and
  plaintext Agent Kernel API keys as secrets.
- [ ] Do not put secrets in `NEXT_PUBLIC_*` variables.
- [ ] Configure backup and restore before migrations.
- [ ] Rotate API keys on a schedule.
- [ ] Review pending approvals regularly.
- [ ] Review failed runs and stuck-run recovery output.
- [ ] Review dependency audit findings before release.

## Maintainer Checklist

Before v1.0 final:

- [ ] Run the Auth/RBAC test matrix in [Auth and RBAC](auth-rbac.md).
- [ ] Run the full Python test suite.
- [ ] Run the Web smoke tests.
- [ ] Run migration smoke tests for SQLite and Postgres.
- [ ] Confirm no stable `/v1/*` route lacks a permission dependency.
- [ ] Confirm security docs match current behavior.
- [ ] Confirm known unscoped resources are listed in release limitations or
  fixed.
- [ ] Confirm dependency audit status is documented.
- [ ] Confirm `SECURITY.md` reporting instructions are current.
- [ ] Confirm release notes include security limitations.

## Route Authorization Review

Stable `/v1/*` routes should require one of these permissions:

- `agent:read`
- `agent:write`
- `run:read`
- `run:write`
- `approval:review`
- `knowledge:read`
- `knowledge:write`
- `memory:read`
- `memory:write`
- `eval:read`
- `eval:write`

Exempt routes:

- `GET /healthz`
- `GET /metrics`

New public routes must not be merged without:

- A route permission dependency.
- Auth-enabled tests for allowed and denied roles.
- Object-scope tests when the resource belongs to a workspace.
- Documentation in [API and CLI Compatibility Policy](api-cli-compatibility.md)
  if the route is stable or preview.

## Tool Safety Review

New tools must define:

- Input schema.
- Risk level.
- Permission expectations.
- Side-effect profile.
- Timeout behavior.
- Result-size behavior.
- Audit visibility.
- Tests for success, validation failure, policy denial, and approval-required
  paths.

Do not add arbitrary shell, filesystem write, network, browser-session, or
external mutation tools as stable tools without a dedicated security review.

## Logging and Trace Review

Logs and traces must not include:

- API keys.
- Authorization headers.
- Database credentials.
- Redis credentials.
- OpenAI API keys.
- AWS credentials.
- Full private document contents.
- Unredacted secrets embedded in tool arguments.

Structured log redaction is based on sensitive field names. Maintainers must be
careful when adding new log fields because arbitrary nested payloads are not a
substitute for explicit redaction review.

## Dependency Review

Before release:

```bash
npm audit
uv run python -m pip list
```

Do not apply force upgrades blindly. Framework upgrades can create larger
compatibility risk than the advisory they attempt to fix. Record accepted risk
in release notes and dependency-audit docs.

## Incident Response Baseline

If a vulnerability is reported:

1. Acknowledge privately.
2. Reproduce on a private branch or local environment.
3. Assess affected versions and configurations.
4. Patch with tests.
5. Rotate exposed credentials if needed.
6. Publish a security advisory or release note when appropriate.
7. Credit the reporter if they want disclosure.

Do not request real user secrets, private documents, or production logs in
public issues.

## v1.0 Decision Point

Before v1.0 final, reviewers must choose one of these paths for every known
security limitation:

- Fix it before release.
- Document it as an explicit v1.0 limitation.
- Remove or demote the affected surface from stable scope.

Silent security limitations are release blockers.
