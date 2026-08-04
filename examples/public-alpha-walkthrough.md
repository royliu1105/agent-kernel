# Public Alpha Walkthrough

This walkthrough exercises the core Public Alpha path from a local checkout:

```text
setup -> API health -> agent run -> RAG retrieval -> memory -> eval -> Web Workbench
```

It should take about 30 minutes on a prepared development machine.

## 1. Prepare Local Runtime

```bash
uv sync
npm install
unset DATABASE_URL
uv run alembic upgrade head
```

Start the API:

```bash
uv run agent-kernel-api
```

In another terminal:

```bash
curl http://127.0.0.1:8000/healthz
```

Expected:

```json
{"status":"ok","service":"agent-kernel-api"}
```

## 2. Create and Execute a Run

Create an agent:

```bash
uv run agent-kernel agent create --name "Public Alpha Agent"
```

Copy the returned `id` as:

```text
AGENT_ID=<returned agent id>
```

Create a run:

```bash
uv run agent-kernel run create <AGENT_ID> --input @examples/mock-run.json
```

Copy the returned `id` as:

```text
RUN_ID=<returned run id>
```

Queue and execute:

```bash
uv run agent-kernel run queue <RUN_ID>
uv run agent-kernel-worker --once --limit 10
```

Inspect:

```bash
uv run agent-kernel run inspect <RUN_ID>
uv run agent-kernel run events <RUN_ID>
```

Expected:

```text
status: succeeded
events: run_created, run_queued, run_started, run_completed
```

## 3. Create a Knowledge Base and Retrieve Citations

Create a knowledge base:

```bash
uv run agent-kernel kb create \
  --name "Public Alpha Handbook" \
  --description "Example deployment knowledge base"
```

Copy the returned `id` as:

```text
KNOWLEDGE_BASE_ID=<returned knowledge base id>
```

Upload the example document:

```bash
uv run agent-kernel document upload \
  <KNOWLEDGE_BASE_ID> \
  examples/docs/deployment-playbook.md
```

Copy the returned `id` as:

```text
DOCUMENT_ID=<returned document id>
```

Ingest, chunk, and index:

```bash
uv run agent-kernel document ingest <DOCUMENT_ID>
uv run agent-kernel document chunk <DOCUMENT_ID>
uv run agent-kernel document index <DOCUMENT_ID>
```

Search:

```bash
uv run agent-kernel kb search \
  <KNOWLEDGE_BASE_ID> \
  --query "When should an operator roll back a deployment?"
```

Expected:

```text
results include deployment-playbook.md citation metadata
```

## 4. Create Scoped Memory

```bash
uv run agent-kernel memory create \
  --type user_preference \
  --scope user:public-alpha \
  --content @examples/memory-user-preference.json

uv run agent-kernel memory list --scope user:public-alpha
```

Expected:

```text
user_preference memory with language=en and concise answer style
```

## 5. Run the Cheap Eval

```bash
uv run agent-kernel eval report evals/rag-smoke.json
```

Expected:

```text
"passed": true
```

## 6. Open the Web Workbench

Start the Web app:

```bash
npm run web:dev
```

Open:

```text
http://127.0.0.1:3000
```

Check these live paths:

- Top bar shows API status.
- Runs -> paste `<RUN_ID>` into Run lookup.
- Knowledge -> live knowledge base list includes `Public Alpha Handbook`.
- Knowledge -> paste `<KNOWLEDGE_BASE_ID>` into Retrieval search.
- Knowledge -> search for `rollback`.
- Approvals -> live approval list loads if approval records exist.

The dashboard, agent cards, some lists, and eval cards still include
fixture-backed preview content during Public Alpha. This keeps the intended
operator surface visible while backend list endpoints are completed.

## 7. When Something Fails

Capture:

- Command.
- Expected result.
- Actual output.
- OS, Python, `uv`, Node.js, Docker, and database mode.
- Release version or commit SHA.

Open a GitHub issue using the Public Alpha feedback template.

Do not include secrets, API keys, tokens, private documents, or private logs.
