# Spec-Driven Development Lite

## Decision

Agent Kernel uses lightweight Spec-Driven Development:

```text
Architectural decisions require ADRs.
Core agent capabilities require lightweight feature specs.
Small changes require tests, not documents.
```

## Why Use SDD Lite

Agent systems fail when semantics are unclear:

- What states can a run enter?
- Can a failed tool call be retried?
- What happens when approval is rejected?
- When is memory written?
- How are RAG citations bound to answers?
- How does a worker recover after a crash?
- Which tool calls are idempotent?
- How is a prompt version bound to a run?
- What behavior does an eval actually test?

Lightweight specs force these decisions to be explicit without creating a heavy documentation process.

## ADRs

Use ADRs for decisions that are hard to reverse:

- Python vs Node.js runtime.
- Modular monolith vs microservices.
- Postgres + pgvector vs alternatives.
- Redis first, Temporal later.
- OpenAI + mock provider first.
- Next.js Web UI.

ADR template:

```text
# ADR NNNN: Title

## Status
Accepted

## Context

## Decision

## Consequences
```

## Feature Specs

Write lightweight specs for core Agent capabilities:

- Run lifecycle.
- Tool calling.
- Approval/resume.
- RAG.
- Memory.
- Evals.
- Security policy.
- Observability.

Feature spec template:

```text
# Feature Spec: Name

## Goal
## Non-Goals
## User Stories
## Domain Model
## State Transitions
## API / CLI
## Failure Modes
## Security
## Observability
## Test Plan
```

## What Does Not Need a Spec

Small changes do not need specs:

- Health check endpoint.
- CLI `--version`.
- README formatting.
- Simple bug fix.
- Test helper.
- Minor UI styling.

These changes still need tests when behavior matters.
