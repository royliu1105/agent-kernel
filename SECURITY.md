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

Do not deploy Agent Kernel as a public multi-tenant SaaS without additional
tenant isolation, network controls, and managed secret storage.

The v1.0 release candidate security checklist is documented in
[docs/security-hardening.md](docs/security-hardening.md).

## Secret Handling

Never commit:

- API keys.
- Database credentials.
- Redis credentials.
- Auth signing keys.
- Encryption keys.
- Production logs containing sensitive payloads.

Use environment variables or deployment secret stores.

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
