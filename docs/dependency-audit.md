# Dependency Audit Review

Last reviewed: 2026-11-13

This document records current dependency review and the historical v0.1 risk
decision. A previous release's risk acceptance does not cover newer findings.

## Current Hardening Review

The P0-P5 review ran `pip-audit` against the installed locked Python environment
and `npm audit` against the workspace lock. The first pass flagged MCP 1.26.0
and certifi 2026.7.22, plus five affected npm packages including Next.js 16.2.12.
These findings were not accepted for the new batch.

Changes, without major-version migration or `audit fix --force`:

- Require official `mcp>=1.30.0,<2`, locked at 1.30.0. The 1.x maintenance fix
  includes Streamable HTTP session retention controls; client/fixture transport
  tests were rerun. See the [MCP advisory](https://github.com/advisories/GHSA-84m7-p3x7-pcfv).
- Refresh transitive certifi to 2026.10.23; no custom CA or TLS-verification
  bypass was introduced.
- Require Next.js `^16.4.6` and refresh its dependency tree within major 16,
  including its compatible PostCSS/sharp versions. The image optimization
  advisory identifies a fixed 16.x line and updated sharp requirement. See the
  [Next.js advisory](https://github.com/advisories/GHSA-2464-fhr4-w9xw).

Repeatable audit commands:

```bash
uv sync --locked --dev
uvx pip-audit --path .venv/lib/python3.12/site-packages --skip-editable --format json
npm audit --json
```

Post-update local results: Python reports **no known vulnerabilities**; npm
reports **0 vulnerabilities**. Ruff/type checks, actual MCP transport tests,
Next.js type generation/build and browser checks are recorded in
[hardening verification](hardening-verification.md).
Next.js 16.4.6 also generates `apps/web/AGENTS.md` during its development-server
startup and adds a root-params type import to `next-env.d.ts`; these are generated
framework integration files, not an application feature or a release action.

Audit scope/limits: editable first-party packages are covered by code review and
tests, not advisory lookup. This audit covers the installed Python environment
and npm lock, not base OS images, optional dependencies absent from that
environment (such as a separately installed S3 SDK), every supported CPU/OS,
third-party MCP servers, or future advisories. A clean advisory result is not a
security certification. Re-audit the exact deployed image and optional extras
before release; remote CI and clean image deployment remain separate gates.

The new MCP/httpcore/Redis/OTel dependencies are used through explicit runtime
boundaries: operator-approved processes/targets, bounded HTTP/queue/telemetry
data, workspace-derived policy and sanitized diagnostics. SDK installation does
not provide an OS sandbox, safe arbitrary commands, OAuth or exactly-once writes.

## Historical v0.1 Review

The following 2026-08-03 record is retained as history, not the current result.

## Commands

Use:

```bash
npm install
npm audit --json
```

Do not automatically run:

```bash
npm audit fix --force
```

Force fixes may downgrade or otherwise move framework packages across breaking
ranges.

## Historical v0.1 Result

Day 38 fresh-run Web install passed:

```text
added 33 packages, and audited 35 packages in 7s
3 high severity vulnerabilities
```

`npm audit --json` reports:

| Package | Direct | Severity | Source |
| --- | --- | --- | --- |
| `next` | yes | high | Aggregates affected `postcss` and `sharp` advisories |
| `postcss` | no | high | Next.js transitive dependency |
| `sharp` | no | high | Next.js optional transitive dependency |

Installed dependency path:

```text
@agent-kernel/web -> next@16.2.12 -> postcss@8.4.31
@agent-kernel/web -> next@16.2.12 -> sharp@0.34.5
```

Registry check on Day 38:

```text
latest next:    16.2.12
latest postcss: 8.5.25
latest sharp:   0.35.3
```

## Decision

Do not apply `npm audit fix --force` for v0.1.

Reasoning:

- The latest stable Next.js version is already installed.
- `npm audit` suggests a breaking and nonsensical fix path for this project:
  `next@9.3.3`.
- Next.js 16.2.12 pins `postcss` to `8.4.31`.
- Next.js 16.2.12 declares `sharp` as optional `^0.34.5`; the audited fixed
  version is `0.35.x`, outside that declared range.
- Overriding framework internals may hide the audit warning but create runtime
  compatibility risk.

v0.1 accepts this as a documented dependency advisory risk because the Web
Workbench is a local operator console, mostly fixture-backed, and not intended
for public multi-tenant production deployment.

## Release Conditions

v0.1 may proceed with this known risk if:

- The advisories are documented in release notes.
- The Web Workbench is not represented as a hardened public production surface.
- `npm audit fix --force` is not applied without a separate compatibility
  decision.
- Public Alpha tracks the Next.js transitive dependency advisories until a
  compatible stable Next.js release updates them.

## Follow-Up

Public Alpha should revisit this when one of these becomes true:

- A stable Next.js release updates `postcss` and `sharp` to fixed ranges.
- Next.js publishes official mitigation guidance.
- The project decides to test and own explicit npm `overrides`.
- The Web Workbench becomes a public-facing production deployment target.
