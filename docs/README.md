# Agent Kernel Documentation

This directory contains the canonical planning baseline for Agent Kernel. Treat these documents as the source of truth for the initial implementation plan unless a later ADR changes a decision.

## Recommended Document Split

The plan is split into these documents:

1. [Project Brief](project-brief.md): project positioning, goals, non-goals, and target users.
2. [Engineering Architecture](architecture.md): monorepo, modular monolith, runtime boundaries, and deployment shape.
3. [Technology Stack](tech-stack.md): selected backend, frontend, storage, observability, testing, and deployment stack.
4. [Storage Architecture](storage-architecture.md): Postgres, pgvector, Redis, object storage, SQLite positioning, and storage abstractions.
5. [Module Boundaries](modules.md): package responsibilities and dependency rules.
6. [Product Shape and Capabilities](product-shape.md): what the project becomes and which product capabilities it exposes.
7. [User Experience](user-experience.md): Agent Workbench UX, where chat is an input mode rather than the whole product.
8. [Development Environment](development-environment.md): professional local Python, Docker, Node.js, IDE, and quality-tool setup.
9. [Product Interfaces](interfaces.md): API, CLI, and Web UI drafts.
10. [Quality Strategy](quality-strategy.md): testing, evals, observability, security, and CI gates.
11. [Development Plan](development-plan.md): 30-day v0.1 plan and daily working method.
12. [SDD Lite](sdd-lite.md): lightweight spec-driven development rules.
13. [ADR 0001](adr/0001-modular-monolith.md): modular monolith decision.
14. [ADR 0002](adr/0002-storage.md): storage decision.
15. [ADR 0003](adr/0003-python-runtime.md): Python runtime decision.

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
