# Security Policy

## Supported Versions

Agent Kernel is in the v1.0 release candidate hardening track.

Security fixes target the current main branch and the latest published release
line. Before v1.0 final, release candidates may still revise security
boundaries when the change is documented in release notes.

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability.

For now, report privately to the maintainer through the repository owner's
preferred private contact channel. If the project later enables GitHub private
vulnerability reporting, use that channel.

Include:

- Affected commit or version.
- Impact summary.
- Reproduction steps.
- Relevant configuration.
- Whether secrets, data, or external systems may be exposed.

Do not include real secrets or customer data in the report.

## Isolation model and non-goals

Agent Kernel scopes agents, runs, approvals, and related objects with
**Workspace** membership and RBAC. That is the isolation model for self-hosted
deployments.

It is **not**:

- A finished public multi-tenant SaaS product.
- Certified hard tenant isolation at the database or network layer.
- End-user browser login, OIDC, or SSO.
- A substitute for your own perimeter, secret store, and threat model.

Do not deploy Agent Kernel as a public multi-tenant SaaS without additional
tenant isolation, network controls, and managed secret storage. See
[Auth and RBAC](docs/auth-rbac.md) for what is implemented vs deferred.

## Localhost default (auth disabled)

`make docker-up` is a **trusted localhost** profile:

- Application API authentication is off by default.
- Ports bind to loopback only; still treat the machine as trusted.
- Mock models and Mailpit avoid paid calls and real email by default.

Do not publish this profile to the internet. Enable API-key auth and tighten
network exposure before any shared or production-like deployment. Operator
detail: [Docker local](docs/docker-local.md), [configuration](docs/configuration.md).

## Current Security Posture

Agent Kernel currently includes:

- Tool risk levels.
- Policy decisions.
- Human approval records.
- Approval interrupt/resume.
- Tool-call and approval audit timeline.
- Structured log redaction for sensitive fields.
- Mock and replay providers for deterministic local testing.
- API-key authentication for `/v1/*` routes when enabled.
- Hashed API key storage.
- Route-level RBAC permission checks.
- Workspace-scoped agents, runs, and approval decisions.
- OpenTelemetry trace configuration and Prometheus-compatible API metrics.

Agent Kernel does not yet include:

- End-user browser login, OIDC, or SSO.
- Public hosted SaaS tenant isolation.
- Browser session management.
- Remote sandbox execution.
- Secrets manager integration.
- Complete object-level scoping for every secondary resource.

The v1.0 release candidate security checklist is documented in
[docs/security-hardening.md](docs/security-hardening.md). Memory injection
limits: [docs/specs/memory-context-safety.md](docs/specs/memory-context-safety.md).

## Secret Handling

Never commit:

- API keys.
- Database credentials.
- Redis credentials.
- Auth signing keys.
- Encryption keys.
- Production logs containing sensitive payloads.
- Grafana or other generated local passwords under `.agent-kernel/`.

Use environment variables or deployment secret stores. Prefer
`.env.example` as the public shape; keep real values in ignored private runtime
files.

## Tool Safety

New tools must define:

- Input schema.
- Risk level.
- Permission requirements.
- Failure behavior.
- Audit visibility.
- Tests for allowed and denied execution paths.

Network, filesystem write, and external write tools should require explicit
policy review and human approval unless they are intentionally constrained.
Production Runs go through `RunExecutionService` and the shared
`ToolPolicyEvaluator`; see [tool calling](docs/specs/tool-calling.md).

## Dependency Security

Run dependency review before releases.

Current known issue:

```text
npm install reports 3 high severity vulnerabilities.
```

Do not run force upgrades blindly. Review whether the fix is compatible with
Next.js, React, and Playwright before applying.

The current dependency-audit review is documented in
[docs/dependency-audit.md](docs/dependency-audit.md).
