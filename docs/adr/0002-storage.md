# ADR 0002: Use PostgreSQL + pgvector with Redis for v0.1 Storage

## Status

Accepted

## Context

Agent Kernel needs durable state for runs, steps, messages, tool calls, approvals, memory, documents, evals, prompts, and audit logs. It also needs vector search for RAG and memory. Queue and lock data should be temporary and recoverable.

## Decision

Use this MVP storage stack:

```text
PostgreSQL + pgvector
Redis
Local filesystem object store
```

Postgres is the source of truth. pgvector handles MVP vector retrieval. Redis handles queue, cache, locks, rate limits, and short-lived coordination. Local filesystem storage handles large files and artifacts in local mode.

Later enhancements may add:

- Temporal for durable execution.
- S3 or MinIO for object storage.
- Qdrant or Weaviate for larger-scale vector search.
- ClickHouse or a warehouse for analytics.

## Consequences

Benefits:

- Strong transactional storage for core state.
- Simpler deployment than a separate vector database.
- Easier backups and local testing than many-service storage.
- Clear path to later adapters.

Costs:

- pgvector may not be enough for very large retrieval workloads.
- Postgres schema design must avoid overloading the business database with huge artifacts.
- Redis must never be treated as the durable source of truth.
