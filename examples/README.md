# Agent Kernel Examples

Examples are small, copyable workflows that exercise real Agent Kernel paths.

They are not toy applications. Each example should map to a product capability
that exists in the runtime and should be runnable from a local checkout.

## Prerequisites

Install dependencies and prepare storage:

```bash
uv sync
npm install
uv run alembic upgrade head
```

Use SQLite for the fastest local path by leaving `DATABASE_URL` unset.

## Example 1: Mock Agent Run

This workflow creates an agent, creates a mock-model run, queues it, executes it,
and inspects the timeline.

```bash
uv run agent-kernel agent create --name "Example Agent"
uv run agent-kernel run create <agent-id> --input @examples/mock-run.json
uv run agent-kernel run queue <run-id>
uv run agent-kernel-worker --once --limit 10
uv run agent-kernel run inspect <run-id>
uv run agent-kernel run events <run-id>
```

Expected timeline includes:

```text
run_created
run_queued
run_started
run_completed
```

## Example 2: Knowledge Base Search

This workflow uploads the included Markdown document and searches it through the
RAG retrieval path.

```bash
uv run agent-kernel kb create --name "Example Handbook"
uv run agent-kernel document upload <knowledge-base-id> examples/docs/deployment-playbook.md
uv run agent-kernel document ingest <document-id>
uv run agent-kernel document chunk <document-id>
uv run agent-kernel document index <document-id>
uv run agent-kernel kb search <knowledge-base-id> --query "How should rollback work?"
```

Expected shape:

```text
retrieval results with chunk IDs and citations
```

## Example 3: Scoped Memory

This workflow creates a user preference memory item and lists it.

```bash
uv run agent-kernel memory create \
  --type user_preference \
  --scope user:example \
  --content @examples/memory-user-preference.json

uv run agent-kernel memory list --scope user:example
```

## Example 4: Cheap RAG Eval

This workflow runs the deterministic RAG smoke eval used by CI.

```bash
uv run agent-kernel eval report evals/rag-smoke.json
```

Expected shape:

```text
"passed": true
```

## Web Workbench

Start the Web Workbench:

```bash
npm run web:dev
```

Open:

```text
http://127.0.0.1:3000
```

The Workbench is fixture-backed in v0.1. It demonstrates the operator console
shape for agents, runs, approvals, knowledge, evals, and settings.
