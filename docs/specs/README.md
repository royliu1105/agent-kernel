# Feature Specs

This directory holds lightweight specs for core Agent Kernel capabilities.

Required specs:

- [run-lifecycle.md](run-lifecycle.md)
- [providers.md](providers.md)
- [prompts.md](prompts.md)
- [tool-calling.md](tool-calling.md)
- [approval-resume.md](approval-resume.md)
- [rag.md](rag.md)
- [memory.md](memory.md)
- [evals.md](evals.md)
- [observability.md](observability.md)
- [security-policy.md](security-policy.md)

Each spec should use this template:

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

Specs should be short enough to stay useful. They are design assumptions that evolve with implementation and eval results.

## v0.1 Spec Status

| Spec | v0.1 Status | Notes |
| --- | --- | --- |
| [run-lifecycle.md](run-lifecycle.md) | Implemented foundation | Create, queue, execute, cancel, timeline, worker, approval resume, retry/fallback policy. |
| [providers.md](providers.md) | Implemented foundation | Provider interface, mock, replay, OpenAI baseline, model router. |
| [prompts.md](prompts.md) | Implemented foundation | Prompt version registry foundation. |
| [tool-calling.md](tool-calling.md) | Implemented foundation | Explicit tool requests, registry, schema validation, executor, risk levels. |
| [approval-resume.md](approval-resume.md) | Implemented foundation | Approval records, API/CLI, interrupt/resume, rejection failure path. |
| [rag.md](rag.md) | Implemented foundation | KB/document metadata, upload, ingest, chunk, mock embed, retrieve, citations, `kb_search`. |
| [memory.md](memory.md) | Implemented foundation | Scoped memory CRUD, retrieval, explicit model context injection. |
| [evals.md](evals.md) | Implemented foundation | Deterministic RAG eval dataset runner and CLI reports. |
| [observability.md](observability.md) | Implemented foundation | Trace IDs, structured logs, metrics recorders, model/tool/retrieval metrics. |
| [security-policy.md](security-policy.md) | Beta identity foundation started | Policy decisions, risk levels, approvals, auditability; Day 52 adds identity, workspace, and RBAC primitives. |

## v0.1 Deferred Capability Summary

Deferred beyond v0.1:

- Provider-native function calling.
- Automatic planning/tool choice.
- Durable model/tool/model loop for provider-returned tool calls.
- Async Redis-backed queue with distributed worker leases.
- pgvector-native vector index implementation.
- Hybrid search, RRF, reranking, and query rewriting.
- Semantic memory retrieval and automatic memory writes.
- Persisted eval runs and eval API.
- OpenTelemetry exporters and Prometheus endpoint.
- Auth, RBAC, tenant isolation, and browser sessions.
- Live Web API integration for all Workbench views.
