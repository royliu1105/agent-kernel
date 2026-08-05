# Product Interfaces

This document summarizes the v0.1 API, CLI, and Web surfaces.

Some endpoints and commands are implemented as production-grade foundations;
some planned surfaces remain deferred and are called out explicitly.

## API Surface

### Health

```http
GET /healthz
```

### Agents and Runs

```http
POST /v1/agents
GET  /v1/agents/{agent_id}
POST /v1/agents/{agent_id}/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/queue
POST /v1/runs/{run_id}/cancel
POST /v1/runs/{run_id}/resume
```

Deferred:

```http
GET   /v1/runs
PATCH /v1/agents/{agent_id}
DELETE /v1/agents/{agent_id}
POST  /v1/runs/{run_id}/retry
```

Retry and fallback exist in runtime policy, but a public retry API remains
deferred.

### Approvals

```http
GET  /v1/approvals
GET  /v1/approvals/{approval_id}
POST /v1/approvals/{approval_id}/approve
POST /v1/approvals/{approval_id}/reject
```

### Knowledge Base and Documents

```http
POST /v1/knowledge-bases
GET  /v1/knowledge-bases
GET  /v1/knowledge-bases/{knowledge_base_id}
POST /v1/knowledge-bases/{knowledge_base_id}/documents
POST /v1/knowledge-bases/{knowledge_base_id}/documents/upload
GET  /v1/knowledge-bases/{knowledge_base_id}/documents
GET  /v1/documents/{document_id}
POST /v1/documents/{document_id}/ingest
GET  /v1/documents/{document_id}/ingestion-jobs
GET  /v1/ingestion-jobs/{job_id}
POST /v1/documents/{document_id}/chunk
GET  /v1/documents/{document_id}/chunks
GET  /v1/document-chunks/{chunk_id}
POST /v1/documents/{document_id}/index
GET  /v1/documents/{document_id}/embeddings
POST /v1/knowledge-bases/{knowledge_base_id}/retrieve
```

### Memory

```http
POST   /v1/memory
GET    /v1/memory
GET    /v1/memory/{memory_id}
DELETE /v1/memory/{memory_id}
```

### Evals

v0.1 evals are CLI-first.

Deferred:

```http
POST /v1/evals/datasets
GET  /v1/evals/datasets
POST /v1/evals/runs
GET  /v1/evals/runs/{eval_run_id}
```

## CLI Surface

JSON object options accept either inline JSON or `@path` to a JSON file.

### Agents and Runs

```bash
agent-kernel agent create --name "Local Test Agent"
agent-kernel run create <agent-id> --input '{"task":"hello runtime","model":"mock:echo"}'
agent-kernel run inspect <run-id>
agent-kernel run events <run-id>
agent-kernel run queue <run-id>
agent-kernel run cancel <run-id>
```

### Approvals

```bash
agent-kernel approval list
agent-kernel approval inspect <approval-id>
agent-kernel approval approve <approval-id>
agent-kernel approval reject <approval-id>
```

### Knowledge Base, Documents, Chunks, and Embeddings

```bash
agent-kernel kb create --name "Engineering Handbook"
agent-kernel kb list
agent-kernel kb inspect <knowledge-base-id>
agent-kernel kb search <knowledge-base-id> --query "What is our deployment policy?"
agent-kernel document upload <knowledge-base-id> ./docs/deploy.md
agent-kernel document ingest <document-id>
agent-kernel document chunk <document-id>
agent-kernel document index <document-id>
agent-kernel chunk list <document-id>
agent-kernel embedding list <document-id>
```

### Memory

```bash
agent-kernel memory create --type user_preference --scope user:<id> --content '{"language":"en"}'
agent-kernel memory list --scope user:<id>
agent-kernel memory inspect <memory-id>
agent-kernel memory delete <memory-id>
```

### Evals

```bash
agent-kernel eval report evals/rag-smoke.json
agent-kernel eval report evals/rag-smoke.json --no-fail-on-failure
```

## Worker Surface

```bash
agent-kernel-worker
agent-kernel-worker --once --limit 10
agent-kernel-worker --loop --limit 25 --poll-interval 2
agent-kernel-worker --recover-stuck --limit 100
```

The worker uses persisted queued runs as the v0.1 durable queue. Beta recovery
can explicitly fail expired leased runs with `worker_lease_expired` so operators
can unblock stuck work without blindly repeating side effects.

## Web Surface

The Agent Workbench includes:

```text
Dashboard
Agents
Runs
Approvals
Knowledge
Evals
Settings
```

Current Web jobs:

- Show dashboard metrics.
- Inspect agent operational status.
- Select runs and inspect timelines.
- Inspect tool-call details.
- Approve or reject approval items locally.
- Inspect local decision history.
- Inspect knowledge bases and document ingestion status.
- Inspect eval reports and behavior cases.
- Inspect read-only runtime, safety, and observability settings.

Important v0.1 limitation:

```text
The Workbench is mostly fixture-backed and does not yet fetch every live backend API.
```

The typed Web API client exists as the boundary for future live integration.
