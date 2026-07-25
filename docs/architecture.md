# Engineering Architecture

## Architecture Decision

Agent Kernel uses:

```text
Monorepo + Modular Monolith + Worker + Pluggable Interfaces
```

This means the project is developed in one repository, with separate applications and clearly bounded internal packages. The backend is not split into microservices for v0.1, but the runtime is organized so modules can later be extracted if needed.

## Runtime Shape

Agent Kernel has four primary process entrypoints:

```text
API process
Worker process
CLI process
Web process
```

The API creates and inspects state. The worker executes long-running agent runs. The CLI is the developer entrypoint. The Web UI exposes operational views such as run timelines, approval queues, knowledge base state, and eval reports.

## High-Level Flow

```text
Web / CLI
   |
   v
FastAPI API
   |
   +--> PostgreSQL + pgvector
   +--> Redis
   +--> Object Store
   |
   v
Worker
   |
   v
Agent Runtime
   |
   +--> LLM Providers
   +--> Tools
   +--> Memory
   +--> RAG
   +--> Policy
   +--> Observability
```

## Dependency Direction

The dependency direction is strict:

```text
apps/*
  -> kernel-runtime / kernel-storage / providers / tools
    -> kernel-core
```

Rules:

- `kernel-core` must not import FastAPI, SQLAlchemy, Redis, OpenAI SDK, or app code.
- `kernel-runtime` must not import FastAPI.
- The Web UI must not access the database directly.
- API endpoints must not execute long-running agent loops directly.
- Worker processes execute agent runs.
- Storage and provider implementations depend on core interfaces, not the other way around.

## Why Not Microservices in v0.1

Microservices would add service discovery, distributed transactions, cross-service tracing, deployment overhead, version compatibility, and harder local testing. The v0.1 priority is mastering and shipping the agent runtime, not distributed service topology.

## Why Not a Single Unstructured App

The project is still modular. API, worker, CLI, Web, storage, providers, tools, RAG, evals, and observability each have clear boundaries. This gives a simple deployment model without creating a large unstructured application.

## Canonical Repository Shape

```text
agent-kernel/
  apps/
    api/
    worker/
    cli/
    web/

  packages/
    kernel-core/
    kernel-runtime/
    kernel-providers/
    kernel-tools/
    kernel-memory/
    kernel-rag/
    kernel-policy/
    kernel-evals/
    kernel-observability/
    kernel-storage/

  docs/
  examples/
  evals/
  tests/
  deploy/
```
