# Security Hardening Checklist

This checklist defines the current security hardening baseline for self-hosted
Agent Kernel deployments. Use release-matched documentation for older tags;
versioned release notes and the v1.0 scope freeze remain historical records.

It is not a public hosted SaaS security certification. Agent Kernel can be used
for self-hosted pilots and internal production trials when operators apply the
deployment controls below.

## Release Gate Summary

Block release readiness if any of these are false:

- API authentication can be enabled for `/v1/*` routes.
- Route-level permissions are enforced when authentication is enabled.
- Workspace-scoped agents, runs, approvals, knowledge, memory, evals, tool
  calls, run events, and usage access are tested.
- API metrics enforce conditional monitoring authentication, and non-loopback
  Worker metrics reject startup without a monitoring token.
- Plaintext API keys are never persisted.
- Sensitive structured-log fields are redacted.
- Risky tools require approval or are denied by policy before execution.
- Rejected approvals fail safely instead of executing the tool.
- Safe-tool retries do not retry side-effecting tools automatically.
- Stable public API and CLI security behavior is documented.
- Deterministic release eval gates and the additional provider wire/timeline
  mutation tests pass; see [Release Eval Gates](release-eval-gates.md).
- Known security limitations are explicitly reviewed, documented, or fixed.

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
- Knowledge bases own documents, chunks, embeddings, and ingestion jobs through
  derived workspace scope. `kb_search` uses the persisted Run workspace,
  including Worker and approval-resume paths, not model-supplied selectors.
- Memory and eval records have workspace ownership. Memory business `scope`
  strings do not authorize access; source runs are checked in the same workspace.
- Tool calls and run events derive scope through their Run. `/v1/usage` and
  `/v1/usage/breakdown` require `run:read` and use authenticated workspace scope.
- Foreign object IDs return HTTP 404; missing role permissions return HTTP 403.
- Legacy NULL-owned knowledge, memory, and eval records are hidden from
  authenticated workspaces. `workspace_id=None` is trusted local/operator
  access, not a tenant boundary.
- Metrics are process/deployment-wide, not workspace data APIs. Collector,
  log, and trace access must be restricted separately.

These controls have cross-workspace regressions in
`tests/integration/test_knowledge_workspace_isolation.py`,
`tests/integration/test_memory_eval_isolation.py`, and
`tests/integration/test_operational_scope.py`. See [Auth and RBAC](auth-rbac.md)
for the full scope and test matrix; these are self-hosted application boundaries,
not public hosted SaaS isolation certification.

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
- Structured logging and configured trace exporters allow only reviewed scalar
  fields; content, nested payloads, and exception text are redacted or omitted.

Deployment controls:

- `/healthz` and sanitized `/readyz` are unauthenticated probe endpoints.
- API `/metrics` requires `AGENT_KERNEL_MONITORING_TOKEN` when API-key auth is
  enabled or a token is configured. Send `Authorization: Bearer <monitoring-token>`;
  ordinary workspace API keys do not grant access. Auth enabled without a token
  returns HTTP 401 for every scrape. Only auth disabled with no token permits
  unauthenticated API metrics.
- Worker metrics are opt-in with `AGENT_KERNEL_WORKER_METRICS_ENABLED=true`;
  the default is `false`, `AGENT_KERNEL_WORKER_METRICS_HOST=127.0.0.1`, and
  `AGENT_KERNEL_WORKER_METRICS_PORT=9001`. Non-loopback binding requires a
  monitoring token. A configured token must contain at least 32 ASCII characters
  and cannot be all whitespace; it also protects loopback scraping. Loopback
  without a token permits unauthenticated scraping.
- Keep both metrics surfaces private even with tokens. API scrapes do not include
  Worker process counters; scrape each instance separately. API durable gauges
  include all workspaces. See [Observability Operations](observability-operations.md).
- Postgres, Redis, and object storage should stay on private networks.
- Secrets should be injected through deployment secret stores.
- Backup guidance treats database and object storage as sensitive.
- Embeddings default to `AGENT_KERNEL_EMBEDDING_PROVIDER=mock`. Real embeddings
  require explicit `AGENT_KERNEL_EMBEDDING_PROVIDER=openai`; an `OPENAI_API_KEY`
  alone never enables paid embeddings. Keep API and Worker selection consistent.

## Current Limitations

Release reviewers must evaluate these boundaries for each deployment:

- API-key auth is disabled by default for local quickstart compatibility.
- There is no browser login, OIDC, SSO, or password auth.
- The Web Workbench does not provide a full user-management UI.
- Public hosted SaaS tenant isolation is out of scope.
- Auth-disabled API access and `workspace_id=None` repository access are trusted
  operator paths, not tenant isolation. Keep them out of shared tenant ingress.
- Metrics, logs, and traces are operator-only surfaces; monitoring-token checks
  do not turn them into workspace-scoped interfaces or provide transport TLS.
- Secrets manager integration is deployment-specific.
- Remote sandbox execution is not implemented.
- Native execution limits and checkpoint fencing do not force-kill uncooperative
  in-process adapters or undo external effects. Keep trusted adapters bounded;
  use process isolation for untrusted code. Private checkpoints contain model
  history/results and must be covered by database/backup access controls.
- Browser session automation is not implemented.
- Dependency advisories must continue to be reviewed before release.

## Operator Checklist

Before exposing a deployment to shared users:

- [ ] Set `AGENT_KERNEL_ENV=production`.
- [ ] Set `AGENT_KERNEL_API_KEY_AUTH_ENABLED=true`.
- [ ] Use PostgreSQL and keep runtime/test credentials separate.
- [ ] Keep Postgres private.
- [ ] Keep Redis private.
- [ ] Keep object storage private.
- [ ] Put API and Web behind HTTPS.
- [ ] Inject a separate `AGENT_KERNEL_MONITORING_TOKEN` with at least 32 random
  ASCII characters; verify missing/wrong tokens return HTTP 401 on protected
  API and Worker `/metrics` endpoints.
- [ ] Keep metrics private and enable the Worker listener only where needed.
- [ ] Set `AGENT_KERNEL_EMBEDDING_PROVIDER` explicitly and match API/Worker
  indexing and retrieval configuration.
- [ ] Store `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, AWS credentials, and
  plaintext Agent Kernel API keys and monitoring tokens as secrets.
- [ ] Do not put secrets in `NEXT_PUBLIC_*` variables.
- [ ] Configure backup and restore before migrations.
- [ ] Rotate API keys on a schedule.
- [ ] Review pending approvals regularly.
- [ ] Apply migration `0019_execution_checkpoint`; keep provider/tool settings
  and trusted execution limits consistent across API and Worker. Review legacy
  native approvals without saved history instead of inventing a continuation.
- [ ] Review failed runs and stuck-run recovery output.
- [ ] Review dependency audit findings before release.

## Maintainer Checklist

Before each release:

- [ ] Run the Auth/RBAC test matrix in [Auth and RBAC](auth-rbac.md).
- [ ] Run the full Python test suite.
- [ ] Run `make release-eval`: RAG smoke/release datasets, native tool-call evals,
  bounded continuation/backoff/wire contracts (isolated PostgreSQL), and `scripts/timeline_regression.py`.
- [ ] Verify the Python CI `Test` step also passes the actual-adapter HTTP mock
  contracts and timeline mutation tests. `make release-eval` alone is not enough.
- [ ] Run the Web smoke tests.
- [ ] Run fresh/legacy PostgreSQL migration and downgrade/re-upgrade checks.
- [ ] Confirm no stable `/v1/*` route lacks a permission dependency.
- [ ] Confirm security docs match current behavior.
- [ ] Run cross-workspace and legacy NULL-ownership regressions; review new
  resource routes for scope checks before data access or side effects.
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

Routes exempt from workspace API-key middleware:

- `GET /healthz`
- `GET /readyz`
- `GET /metrics` (separate conditional monitoring-token check, not an
  unconditional public-route exemption)

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

Structured logs and configured trace exporters use an allowlist of reviewed
scalar identifiers/counts. Nested containers and unknown fields are opaque;
ordinary free-text log messages and exception text are not safe output channels.
This is not a general natural-language PII classifier. Additional raw handlers,
direct stdout/stderr writes, or raw trace exporters can bypass that boundary.
Review all new fields and integrations against
[Observability Operations](observability-operations.md#logs-and-traces).

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

## Release Decisions

Before a release, reviewers must choose one of these paths for every known
security limitation:

- Fix it before release.
- Document it as an explicit release limitation.
- Remove or demote the affected surface from stable scope.

Silent security limitations are release blockers.

The historical [v1.0 Scope Freeze](v1-scope-freeze.md) records the original
release decision. Preserve that record and versioned release notes; use the
current configuration, implementation, and regression evidence for new releases.
