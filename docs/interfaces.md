# Product Interfaces

This document summarizes the current API, CLI, worker, and Web surfaces.

Compatibility rules and stability levels live in
[API and CLI Compatibility Policy](api-cli-compatibility.md). Treat this file
as the interface catalog and the compatibility policy as the change-control
contract.

## API Surface

### Health and Metrics

```http
GET /healthz
GET /metrics
```

`/metrics` returns Prometheus text exposition format and is intended for
private-network scraping.

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

Approval routes enforce route-level permissions and workspace scope.

### Knowledge Base and Documents

```http
POST /v1/knowledge-bases
GET  /v1/knowledge-bases
GET  /v1/knowledge-bases/{knowledge_base_id}
POST /v1/knowledge-bases/{knowledge_base_id}/retrieve
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
```

Retrieval can use SQLite-compatible JSON vectors or pgvector depending on
configuration.

### Memory

```http
POST   /v1/memory
GET    /v1/memory
GET    /v1/memory/{memory_id}
DELETE /v1/memory/{memory_id}
```

### Evals

```http
POST /v1/evals/runs
GET  /v1/evals/runs
GET  /v1/evals/runs/{eval_run_id}
```

The API persists submitted eval reports. It does not yet schedule remote eval
jobs, upload eval datasets, or run LLM-as-judge suites.

Deferred:

```http
POST /v1/evals/datasets
GET  /v1/evals/datasets
POST /v1/evals/jobs
GET  /v1/evals/jobs/{job_id}
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
agent-kernel run resume <run-id>
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

agent-kernel document register <knowledge-base-id> --title "Deploy Guide" --source-uri file://docs/deploy.md --mime-type text/markdown
agent-kernel document upload <knowledge-base-id> ./docs/deploy.md
agent-kernel document list <knowledge-base-id>
agent-kernel document inspect <document-id>
agent-kernel document ingest <document-id>
agent-kernel document chunk <document-id>
agent-kernel document index <document-id>

agent-kernel ingestion inspect <job-id>
agent-kernel ingestion list <document-id>

agent-kernel chunk list <document-id>
agent-kernel chunk inspect <chunk-id>

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
agent-kernel eval report evals/rag-smoke.json --publish
```

`--publish` sends the generated deterministic report to `POST /v1/evals/runs`.

## Worker Surface

```bash
agent-kernel-worker
agent-kernel-worker --once --limit 10
agent-kernel-worker --loop --limit 25 --poll-interval 2
agent-kernel-worker --recover-stuck --limit 100
```

The worker uses persisted queued runs as the durable source of truth. Stuck-run
recovery can explicitly fail expired leased runs with
`worker_lease_expired` so operators can unblock stuck work without blindly
repeating side effects.

The runtime package also exposes `RunQueue`, `InMemoryRunQueue`, and
`RedisRunQueue` for queue coordination. Redis queue entries carry run ids only;
the default worker path still validates queued work from the database.

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

Live same-origin Web proxy routes:

```text
/api/agent-kernel/health
/api/agent-kernel/runs/{run_id}
/api/agent-kernel/runs/{run_id}/events
/api/agent-kernel/approvals
/api/agent-kernel/approvals/{approval_id}/approve
/api/agent-kernel/approvals/{approval_id}/reject
/api/agent-kernel/knowledge-bases
/api/agent-kernel/knowledge-bases/{knowledge_base_id}/retrieve
/api/agent-kernel/evals/runs
```

Current Web jobs:

- Show dashboard metrics from live and local summary data.
- Inspect agent operational status.
- Select runs and inspect live timelines.
- Inspect tool-call details.
- Approve or reject approval items through live backend routes.
- Inspect knowledge bases and run retrieval search against live backend routes.
- Inspect persisted eval runs when the backend is available.
- Inspect read-only runtime, safety, and observability settings.

Preview-backed areas that intentionally remain:

- Some dashboard aggregate cards.
- Agent catalog-style summaries.
- Document ingestion detail surfaces.
- Memory detail surfaces.
- Full admin settings and operational policy editing.

These are not part of the stable Web contract yet. The stable contract for v1.0
is the backend API and CLI; the Web Workbench remains an operator console with
some preview-backed areas.
