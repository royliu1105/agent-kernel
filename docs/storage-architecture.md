# Storage Architecture

## Storage Principle

Agent storage is not just chat history. It must support state recovery, auditability, memory, retrieval, evals, observability, and operational control.

## MVP Storage Stack

```text
PostgreSQL + pgvector
Redis
Local filesystem object store
```

## Later Storage Stack

```text
Temporal for durable execution
S3 or MinIO for artifacts
Qdrant or Weaviate for larger vector search
ClickHouse or warehouse for analytics
Tempo/Jaeger + Prometheus/Grafana for observability
```

## Source of Truth

Postgres is the source of truth.

Important state must end up in Postgres:

- Agent definitions.
- Run state.
- Run steps.
- Messages.
- Tool calls.
- Approval decisions.
- Prompt versions.
- Memory records.
- Document metadata.
- Eval metadata.
- Audit events.

Redis is not the source of truth. Redis is used for temporary coordination:

- Queue jobs.
- Short-lived locks.
- Cache.
- Rate limits.
- Streaming event buffers.

## Data Categories

### Control Plane Data

Stored in Postgres:

- Users.
- Projects.
- Agents.
- Tools.
- Model policies.
- Prompt versions.
- Permissions.
- API keys.

### Execution State

Stored in Postgres, coordinated by Redis:

- Runs.
- Run steps.
- Messages.
- Model calls.
- Tool calls.
- Approvals.
- Retries.
- Errors.

### Event and Audit Log

MVP: Postgres event table.

Events include:

- Run created.
- Step started.
- Model called.
- Tool requested.
- Approval requested.
- Approval granted or rejected.
- Step failed.
- Run resumed.

### Knowledge Store

MVP: Postgres + pgvector.

Data:

- Documents.
- Chunks.
- Embeddings.
- Citations.
- Ingestion jobs.

### Memory Store

MVP: Postgres + pgvector.

Memory types:

- Short-term memory from current messages and steps.
- Task context from run-specific state.
- User preferences as structured key-value data.
- Long-term memory as memory items with optional embeddings.

### Object Storage

Object storage stores large files and artifacts:

- Uploaded PDFs, Markdown, HTML, and docx files.
- Generated reports.
- Large tool outputs.
- Eval reports.
- Trace exports.

MVP implementation:

```text
LocalObjectStore
```

Later implementation:

```text
S3ObjectStore
```

S3 is AWS's object storage service and a widely adopted API standard. MinIO is an open-source, self-hosted, S3-compatible object storage system.

## SQLite Positioning

SQLite may be supported later for:

- Local development.
- Single-user learning mode.
- Tests.
- Quickstart without Docker.

It is not the default production storage path. The production/default path remains:

```text
PostgreSQL + pgvector
```

## Required Storage Interfaces

The codebase should define storage boundaries before binding business logic to a concrete database:

- `RunStore`
- `AgentStore`
- `MessageStore`
- `ToolCallStore`
- `ApprovalStore`
- `MemoryStore`
- `DocumentStore`
- `VectorStore`
- `ObjectStore`
- `ArtifactStore`
- `EventStore`
- `Queue`
- `LockManager`
