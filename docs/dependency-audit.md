# Dependency Audit Review

Last reviewed: 2026-08-03

This document records release-time dependency audit findings and the decision
logic for Agent Kernel v0.1.

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

## Current v0.1 Result

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
