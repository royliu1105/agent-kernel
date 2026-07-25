# Product Interfaces

## API Draft

### Agents

```http
POST   /v1/agents
GET    /v1/agents
GET    /v1/agents/{agent_id}
PATCH  /v1/agents/{agent_id}
DELETE /v1/agents/{agent_id}
```

### Runs

```http
POST   /v1/agents/{agent_id}/runs
GET    /v1/runs
GET    /v1/runs/{run_id}
GET    /v1/runs/{run_id}/events
POST   /v1/runs/{run_id}/cancel
POST   /v1/runs/{run_id}/resume
POST   /v1/runs/{run_id}/retry
```

### Approvals

```http
GET    /v1/approvals
GET    /v1/approvals/{approval_id}
POST   /v1/approvals/{approval_id}/approve
POST   /v1/approvals/{approval_id}/reject
```

### Tools

```http
GET    /v1/tools
POST   /v1/tools
GET    /v1/tools/{tool_name}
PATCH  /v1/tools/{tool_name}
```

### Knowledge Base

```http
POST   /v1/documents
GET    /v1/documents
GET    /v1/documents/{document_id}
POST   /v1/documents/{document_id}/ingest
POST   /v1/retrieval/query
```

### Memory

```http
GET    /v1/memory
POST   /v1/memory
DELETE /v1/memory/{memory_id}
```

### Evals

```http
POST   /v1/evals/datasets
GET    /v1/evals/datasets
POST   /v1/evals/runs
GET    /v1/evals/runs/{eval_run_id}
```

## CLI Draft

```bash
agent-kernel init
agent-kernel dev
agent-kernel server start
agent-kernel worker start

agent-kernel agent create --name research-agent --prompt prompts/research.md
agent-kernel agent list
agent-kernel agent inspect <agent-id>

agent-kernel run create <agent-id> --input "Summarize these docs"
agent-kernel run watch <run-id>
agent-kernel run retry <run-id>
agent-kernel run cancel <run-id>

agent-kernel approval list
agent-kernel approval approve <approval-id>
agent-kernel approval reject <approval-id> --reason "Not allowed"

agent-kernel doc upload ./docs/*.md
agent-kernel doc ingest <document-id>
agent-kernel kb query "What is our deployment policy?"

agent-kernel eval run ./evals/research.yaml --agent <agent-id>
agent-kernel eval report <eval-run-id>
```

## Web UI Draft

MVP pages:

- Dashboard.
- Agents.
- Run detail and timeline.
- Tool call detail.
- Approval inbox.
- Knowledge base.
- Eval reports.
- Settings.

Primary UI jobs:

- Show recent runs, success rate, cost, latency, and pending approvals.
- Configure agents, model policies, prompts, tools, and memory policy.
- Inspect run timelines step by step.
- Review model calls, tool calls, retrieved chunks, approvals, errors, retries, and costs.
- Approve or reject risky tool calls.
- Upload and inspect documents.
- View ingestion status.
- Run and inspect eval reports.
