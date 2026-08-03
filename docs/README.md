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
12. [Dependency Audit Review](dependency-audit.md): npm audit findings, risk acceptance, and follow-up policy.
13. [Troubleshooting](troubleshooting.md): local setup, Docker, uv, npm, port, worker, and release-verification failure modes.
14. [Agent Kernel v0.1](v0.1.md): v0.1 product snapshot, capability matrix, readiness, and next steps.
15. [Phase 1 Summary](phase-1-summary.md): completed core runtime capabilities and tradeoffs.
16. [Phase 2 Summary](phase-2-summary.md): completed tool, policy, approval, retry, and fallback capabilities.
17. [Phase 3 Summary](phase-3-summary.md): completed RAG and memory foundation capabilities and limitations.
18. [Phase 4 Summary](phase-4-summary.md): completed observability and deterministic eval capabilities and limitations.
19. [Phase 5 Summary](phase-5-summary.md): completed Agent Workbench Web UI capabilities and limitations.
20. [Phase 6 Summary](phase-6-summary.md): completed v0.1 release-hardening work, verification, and remaining release blockers.
21. [Product Interfaces](interfaces.md): v0.1 API, CLI, worker, and Web UI surface.
22. [Quality Strategy](quality-strategy.md): testing, evals, observability, security, and CI gates.
23. [Development Plan](development-plan.md): v0.1 plan and daily working method.
24. [Milestones](milestones.md): day-by-day milestone map for v0.1 and Public Alpha.
25. [Daily Plans](daily/README.md): per-day execution checklist and progress tracking.
26. [Release Checklist](release-checklist.md): v0.1 release verification checklist.
27. [v0.1.0 Release Notes](releases/v0.1.0.md): release candidate notes, limitations, and next steps.
28. [SDD Lite](sdd-lite.md): lightweight spec-driven development rules.
29. [Phase 3 Realignment](phase-3-realignment.md): RAG and memory delivery correction for Days 19-24.
30. [ADR 0001](adr/0001-modular-monolith.md): modular monolith decision.
31. [ADR 0002](adr/0002-storage.md): storage decision.
32. [ADR 0003](adr/0003-python-runtime.md): Python runtime decision.
33. [ADR 0004](adr/0004-language-strategy.md): Python runtime plus TypeScript product surface decision.

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
36 days to v0.1
51 days to Public Alpha
```

The first day of implementation should focus only on the project skeleton and engineering baseline.
