# Agent Kernel Documentation

Canonical docs for the maintained runtime. Start with the **Current
documentation** map below. Historical day/phase/release planning files are not
current acceptance checklists.

Default local startup is **Docker only**: `make docker-up`. See
[Docker-Only Local Runtime](docker-local.md).

Published release baseline: [v1.0.0](releases/v1.0.0.md). `master` may contain
**unreleased** work beyond that tag; treat [project overview](project-overview.md)
and the pilot ledger as status sources, not the release number alone.

Open-source cleanup sequencing (navigation only): [OSS cleanup PR plan](oss-cleanup-pr-plan.md).

## Current documentation

Use these first. Status detail lives in the linked ledgers—do not treat deferred
CF items as in-progress delivery.

| Need | Document |
| --- | --- |
| Product, architecture, capability evidence and limits | [Project Overview](project-overview.md) |
| Run locally | [Quickstart](quickstart.md), [Docker operations](docker-local.md) |
| Mock approval/resume showcase | [Showcase happy-path](showcase/mock-happy-path.md) |
| Security and access limits | [SECURITY](../SECURITY.md), [Auth and RBAC](auth-rbac.md), [Memory context safety](specs/memory-context-safety.md) |
| Pilot task/status ledger (not a feature backlog) | [Real-scenario pilot plan](real-scenario-pilot-plan.md) |
| Follow-ups (CF1–CF8; CF3–CF8 deferred/conditional) | [Reference follow-up plan](reference-follow-up-plan.md) |
| Learning alongside pilot work | [Pilot learning guide](pilot-learning-guide.md) |

### Current operator and evidence guides

- [Supervised local paid experience](local-paid-experience.md) — separate authorized walkthrough; not full pilot acceptance
- [Observability completion plan](observability-completion-plan.md) (O1–O5) and [backends/SMTP](observability-backends.md)
- [PV1 runbook contract](pilots/pv1-2026-11-15-runbook-assistant.md), [PV1 materials](pilots/pv1-materials/README.md)
- [Provider compatibility](provider-compatibility.md), [pilot provider contract](specs/pilot-provider-compatibility.md)
- [Reference project comparison](reference-project-comparison.md) — optional historical maintainer research note; no reference tree ships with this repo
- [Execution ownership](execution-ownership.md), [bounded native execution](specs/bounded-native-execution.md)
- [External tools](external-tools.md), [observability operations](observability-operations.md)
- [Backend operations](backend-operations.md), [behavior regression](behavior-regression.md)
- [Hardening verification](hardening-verification.md), [capability hardening plan](capability-hardening-plan.md) (completed R1–R10 / N1–N5 evidence)
- [PostgreSQL-only storage and tests](postgresql-only.md), [configuration](configuration.md), [troubleshooting](troubleshooting.md)

### Architecture and module references

1. [Project Brief](project-brief.md)
2. [Engineering Architecture](architecture.md)
3. [Technology Stack](tech-stack.md)
4. [Storage Architecture](storage-architecture.md)
5. [Module Boundaries](modules.md)
6. [Product Shape](product-shape.md)
7. [User Experience](user-experience.md)
8. [Development Environment](development-environment.md)
9. [Production Configuration](production-config.md)
10. [Product Interfaces](interfaces.md)
11. [Quality Strategy](quality-strategy.md)
12. [Agent Architectures](agent-architectures.md) — pattern notes; not a claim that every pattern is implemented
13. [ADR 0001](adr/0001-modular-monolith.md), [ADR 0002](adr/0002-storage.md), [ADR 0003](adr/0003-python-runtime.md), [ADR 0004](adr/0004-language-strategy.md)

Repository-level entry docs:

- [CONTRIBUTING](../CONTRIBUTING.md)
- [SECURITY](../SECURITY.md)
- [ROADMAP](../ROADMAP.md) — historical release targets; current status points here to overview + pilot
- [Examples](../examples/README.md)

## Archive / historical (not current acceptance)

**Historical; not acceptance criteria.** See also [docs/archive/README.md](archive/README.md).

These record how v0.1 → Public Alpha → Beta → v1.0 were delivered. Completion
of a historical checklist does not imply current isolation, leasing, or
external-tool guarantees. For current status use [project overview](project-overview.md)
and [real-scenario pilot plan](real-scenario-pilot-plan.md).

- [Development plan](development-plan.md) — Day 1–90 historical method and stages
- [Milestones](milestones.md) — day-by-day historical map
- [Daily plans stub](daily/README.md) → [archive/daily](archive/daily/README.md)
- [Post-v0.1 completion plan](post-v0.1-plan.md)
- [Public Alpha guide](archive/public-alpha.md), [Public Alpha summary](archive/public-alpha-summary.md), [Public Alpha release notes](releases/public-alpha.md)
- [Beta summary](archive/beta-summary.md), [Durable execution summary](archive/durable-execution-summary.md)
- [v0.1 snapshot](v0.1.md), [v0.1 release checklist](release-checklist.md), [v0.1.0 notes](releases/v0.1.0.md)
- [v1.0 scope freeze](v1-scope-freeze.md), [v1.0 release checklist](v1-release-checklist.md), [v1.0.0 notes](releases/v1.0.0.md)
- Phase summaries: [1](archive/phase-1-summary.md), [2](archive/phase-2-summary.md),
  [3](archive/phase-3-summary.md), [4](archive/phase-4-summary.md), [5](archive/phase-5-summary.md),
  [6](archive/phase-6-summary.md)
- [API/CLI compatibility](api-cli-compatibility.md), [upgrade/migration](upgrade-migration-policy.md), [backup/restore](backup-restore.md)
- [Security hardening checklist](security-hardening.md), [release eval gates](release-eval-gates.md), [release smoke](release-smoke-tests.md)
- [Load/soak](load-soak-scenarios.md), [clean-machine rehearsal](clean-machine-rehearsal.md), [rehearsal results](archive/clean-machine-rehearsal-results.md)
- [Docs consistency audit](archive/docs-consistency-audit.md), [SDD Lite](archive/sdd-lite.md), [Phase 3 realignment](archive/phase-3-realignment.md)

## Current baseline shape

```text
Monorepo + Modular Monolith + Worker + Pluggable Interfaces
```

Historical delivery sequence (complete; not the active schedule):

```text
Day 1-38: v0.1.0 published release
Day 39-51: Public Alpha
Day 52-75: Beta production hardening
Day 76-90: v1.0 release candidate and release work
```
