# Agent Kernel Examples

Examples are copyable workflows that exercise real Agent Kernel runtime paths.

They are not toy applications. Each example maps to a product capability that
exists in the current runtime and should be runnable from a local checkout with
mock models and Docker PostgreSQL.

## Start Here

Use the full walkthrough when trying the project as an early external user:

- [Public Alpha Walkthrough](public-alpha-walkthrough.md)

Use the request collection when you prefer an HTTP client:

- [Public Alpha HTTP requests](public-alpha.http)

## Prerequisites

Start the Docker runtime (including migrations and the continuous Worker):

```bash
make docker-up
```

Verify:

```bash
curl http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status":"ok","service":"agent-kernel-api"}
```

## Example 1: Mock Agent Run

This workflow creates an agent, creates a mock-model run, queues it, executes it,
and inspects the timeline.

```bash
sh scripts/local-stack.sh exec -T api agent-kernel agent create --name "Example Agent"
sh scripts/local-stack.sh exec -T api agent-kernel run create <agent-id> --input @examples/mock-run.json
sh scripts/local-stack.sh exec -T api agent-kernel run queue <run-id>
# The Docker Worker processes queued runs automatically.
sh scripts/local-stack.sh exec -T api agent-kernel run inspect <run-id>
sh scripts/local-stack.sh exec -T api agent-kernel run events <run-id>
```

Expected run status:

```text
succeeded
```

Expected timeline includes:

```text
run_created
run_queued
run_started
run_completed
```

You can also paste the run ID into the Web Workbench Run lookup panel.

## Example 2: Knowledge Base Search

This workflow uploads the included Markdown document and searches it through the
RAG retrieval path.

```bash
sh scripts/local-stack.sh exec -T api agent-kernel kb create \
  --name "Example Handbook" \
  --description "Deployment runbook used by Public Alpha examples"

sh scripts/local-stack.sh exec -T api agent-kernel document upload \
  <knowledge-base-id> \
  examples/docs/deployment-playbook.md

sh scripts/local-stack.sh exec -T api agent-kernel document ingest <document-id>
sh scripts/local-stack.sh exec -T api agent-kernel document chunk <document-id>
sh scripts/local-stack.sh exec -T api agent-kernel document index <document-id>

sh scripts/local-stack.sh exec -T api agent-kernel kb search \
  <knowledge-base-id> \
  --query "How should rollback work?"
```

Expected response shape:

```text
results[0].content
results[0].score
results[0].citation.document_title
results[0].citation.document_source_uri
```

Expected cited source:

```text
deployment-playbook.md
```

You can also paste the knowledge base ID into the Web Workbench Retrieval search
panel and submit the same query.

## Example 3: Scoped Memory

This workflow creates a user preference memory item and lists it.

```bash
sh scripts/local-stack.sh exec -T api agent-kernel memory create \
  --type user_preference \
  --scope user:example \
  --content @examples/memory-user-preference.json

sh scripts/local-stack.sh exec -T api agent-kernel memory list --scope user:example
```

Expected fields include:

```text
type: user_preference
scope: user:example
content.language: en
```

## Example 4: Cheap RAG Eval

This workflow runs the deterministic RAG smoke eval used by CI.

```bash
sh scripts/local-stack.sh exec -T api agent-kernel eval report evals/rag-smoke.json
```

Expected shape:

```text
"passed": true
```

## Example 5: Web Workbench

The Web Workbench is already running in Docker after `make docker-up`.

Open:

```text
http://127.0.0.1:3000
```

Current Public Alpha live paths:

- API health status in the top bar.
- Run lookup by run ID.
- Run events lookup by run ID.
- Approval inbox list.
- Approval approve/reject mutations.
- Knowledge base list.
- Retrieval search with raw cited chunks.

Fixture-backed preview areas remain for pages whose backend list/detail APIs are
not complete yet. Those previews are intentionally labeled in the UI.

## Known Example Boundaries

- Use `mock:*` models unless you intentionally configure external providers.
- Retrieval uses the current deterministic mock embedding path by default.
- Final answer synthesis with citations is not part of these examples yet.
- Auth/RBAC, object storage backends, real embeddings, and durable distributed
  queues are planned after Public Alpha.
