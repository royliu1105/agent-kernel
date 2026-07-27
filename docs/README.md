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
11. [Product Interfaces](interfaces.md): API, CLI, and Web UI drafts.
12. [Quality Strategy](quality-strategy.md): testing, evals, observability, security, and CI gates.
13. [Development Plan](development-plan.md): 30-day v0.1 plan and daily working method.
14. [Milestones](milestones.md): day-by-day milestone map for v0.1 and Public Alpha.
15. [Daily Plans](daily/README.md): per-day execution checklist and progress tracking.
16. [SDD Lite](sdd-lite.md): lightweight spec-driven development rules.
17. [ADR 0001](adr/0001-modular-monolith.md): modular monolith decision.
18. [ADR 0002](adr/0002-storage.md): storage decision.
19. [ADR 0003](adr/0003-python-runtime.md): Python runtime decision.
20. [ADR 0004](adr/0004-language-strategy.md): Python runtime plus TypeScript product surface decision.

## Current Baseline

Agent Kernel is planned as:

```text
Monorepo + Modular Monolith + Worker + Pluggable Interfaces
```

The first implementation target is:

```text
30 days to v0.1
45 days to Public Alpha
```

The first day of implementation should focus only on the project skeleton and engineering baseline.
