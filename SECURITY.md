# Security Policy

## Supported Versions

Agent Kernel is pre-v1.

Security fixes target the current main branch until versioned releases are
published.

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

Agent Kernel v0.1 includes:

- Tool risk levels.
- Policy decisions.
- Human approval records.
- Approval interrupt/resume.
- Tool-call and approval audit timeline.
- Structured log redaction for sensitive fields.
- Mock and replay providers for deterministic local testing.

Agent Kernel v0.1 does not yet include:

- End-user authentication.
- Role-based authorization.
- Tenant isolation.
- Browser session management.
- Remote sandbox execution.
- Secrets manager integration.
- Production-grade network isolation guidance beyond local Compose.

Do not deploy v0.1 as a public multi-tenant service without additional security
controls.

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
