# Agent Kernel Documentation

This directory contains the canonical planning baseline for Agent Kernel. Treat these documents as the source of truth for the initial implementation plan unless a later ADR changes a decision.

## Recommended Document Split

The plan is split into these documents:

1. [Project Brief](project-brief.md): project positioning, goals, non-goals, and target users.
2. [Engineering Architecture](architecture.md): monorepo, modular monolith, runtime boundaries, and deployment shape.
3. [Agent Architectures](agent-architectures.md): mainstream Agent architecture patterns and how Agent Kernel combines them.
4. [Technology Stack](tech-stack.md): selected backend, frontend, storage, observability, testing, and deployment stack.
5. [Storage Architecture](storage-architecture.md): Postgres, pgvector, Redis, object storage, SQLite positioning, and storage abstractions.
6. [Module Boundaries](modules.md): package responsibilities and dependency rules.
7. [Product Shape and Capabilities](product-shape.md): what the project becomes and which product capabilities it exposes.
8. [User Experience](user-experience.md): Agent Workbench UX, where chat is an input mode rather than the whole product.
9. [Development Environment](development-environment.md): professional local Python, Docker, Node.js, IDE, and quality-tool setup.
10. [Quickstart](quickstart.md): real local runtime path for agent/run/worker execution.
11. [Production Configuration](production-config.md): runtime environment, deployment topology, secrets, storage, and release hardening.
12. [Auth and RBAC](auth-rbac.md): Beta API key auth, workspace roles, permissions, object scope, and security test matrix.
13. [Dependency Audit Review](dependency-audit.md): npm audit findings, risk acceptance, and follow-up policy.
14. [Troubleshooting](troubleshooting.md): local setup, Docker, uv, npm, port, worker, and release-verification failure modes.
15. [Agent Kernel v0.1](v0.1.md): v0.1 product snapshot, capability matrix, readiness, and next steps.
16. [Public Alpha Guide](public-alpha.md): early-user trial path, feedback workflow, and live Web API priorities.
17. [Post-v0.1 Completion Plan](post-v0.1-plan.md): Public Alpha, Beta, and v1.0 completion plan.
18. [Public Alpha Summary](public-alpha-summary.md): completed Day 39-51 hardening work, verification scope, limitations, and Beta entry point.
19. [Durable Execution Summary](durable-execution-summary.md): completed Day 59-63 worker leasing, recovery, queue adapter foundation, retry visibility, and operator CLI scope.
20. [Beta Summary](beta-summary.md): completed Day 52-75 production hardening work, verification scope, limitations, and v1.0 RC handoff.
21. [API and CLI Compatibility Policy](api-cli-compatibility.md): v1.0 RC stability levels, public contract, preview surfaces, and deprecation rules.
22. [Versioned Configuration Reference](configuration.md): v1.0 RC environment-variable contract, defaults, secret status, and change-control rules.
23. [Upgrade and Migration Policy](upgrade-migration-policy.md): v1.0 RC upgrade sequence, Alembic rules, migration test expectations, and rollback boundaries.
24. [Backup and Restore Guide](backup-restore.md): v1.0 RC backup scope, Postgres/object-store restore steps, validation, retention, and security expectations.
25. [Security Hardening Checklist](security-hardening.md): v1.0 RC release gates, operator checklist, known limitations, and incident-response baseline.
26. [Release Eval Gates](release-eval-gates.md): v1.0 RC deterministic release-blocking eval command, datasets, CI gate, and non-blocking eval boundaries.
27. [Release Smoke Tests](release-smoke-tests.md): v1.0 RC critical-path smoke matrix and `make release-smoke` command contract.
28. [Load and Soak Scenarios](load-soak-scenarios.md): v1.0 RC load/soak profiles, thresholds, manual infrastructure scenarios, and failure handling.
29. [Phase 1 Summary](phase-1-summary.md): completed core runtime capabilities and tradeoffs.
30. [Phase 2 Summary](phase-2-summary.md): completed tool, policy, approval, retry, and fallback capabilities.
31. [Phase 3 Summary](phase-3-summary.md): completed RAG and memory foundation capabilities and limitations.
32. [Phase 4 Summary](phase-4-summary.md): completed observability and deterministic eval capabilities and limitations.
33. [Phase 5 Summary](phase-5-summary.md): completed Agent Workbench Web UI capabilities and limitations.
34. [Phase 6 Summary](phase-6-summary.md): completed v0.1 release-hardening work, verification, and remaining release blockers.
35. [Product Interfaces](interfaces.md): current API, CLI, worker, and Web UI surface catalog.
36. [Quality Strategy](quality-strategy.md): testing, evals, observability, security, and CI gates.
37. [Development Plan](development-plan.md): v0.1 plan and daily working method.
38. [Milestones](milestones.md): day-by-day milestone map for v0.1, Public Alpha, Beta, and v1.0.
39. [Daily Plans](daily/README.md): per-day execution checklist and progress tracking.
40. [Release Checklist](release-checklist.md): v0.1 release verification checklist.
41. [v0.1.0 Release Notes](releases/v0.1.0.md): published release notes, limitations, and next steps.
42. [Public Alpha Release Notes](releases/public-alpha.md): Public Alpha announcement draft, trial scope, limitations, and feedback request.
43. [SDD Lite](sdd-lite.md): lightweight spec-driven development rules.
44. [Phase 3 Realignment](phase-3-realignment.md): RAG and memory delivery correction for Days 19-24.
45. [ADR 0001](adr/0001-modular-monolith.md): modular monolith decision.
46. [ADR 0002](adr/0002-storage.md): storage decision.
47. [ADR 0003](adr/0003-python-runtime.md): Python runtime decision.
48. [ADR 0004](adr/0004-language-strategy.md): Python runtime plus TypeScript product surface decision.

Repository-level release docs:

- [CONTRIBUTING](../CONTRIBUTING.md): contribution workflow and quality gates.
- [SECURITY](../SECURITY.md): vulnerability reporting and security posture.
- [ROADMAP](../ROADMAP.md): v0.1, Public Alpha, and later production hardening.
- [Examples](../examples/README.md): runnable local example workflows.

## Current Baseline

Agent Kernel is planned as:

```text
Monorepo + Modular Monolith + Worker + Pluggable Interfaces
```

The first implementation target is:

```text
Day 1-38: v0.1.0 published release
Day 39-51: Public Alpha
Day 52-75: Beta production hardening
Day 76-90: v1.0 release candidate and release work
```
