# ADR 0001: Use Modular Monolith with Separate Entrypoints

## Status

Accepted

## Context

Agent Kernel needs an API server, worker, CLI, Web UI, runtime, storage, tools, RAG, memory, evals, observability, and security policy. A microservice architecture would add significant operational complexity before the runtime semantics are stable.

At the same time, a single unstructured app would make module boundaries unclear and hard to maintain.

## Decision

Use a monorepo with a modular monolith backend and separate process entrypoints:

```text
apps/api
apps/worker
apps/cli
apps/web
packages/kernel-*
```

The API, worker, and CLI share internal Python packages. The Web UI is a separate Next.js app in the same repository.

## Consequences

Benefits:

- Simple local development.
- Simple CI.
- Clear module boundaries.
- Easier end-to-end tests.
- Easier refactoring while the runtime is young.
- Future extraction to services remains possible.

Costs:

- Requires discipline around imports.
- CI may need path-based optimization later.
- Internal packages need clear ownership and documentation.
