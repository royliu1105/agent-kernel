# Phase 3 Summary: RAG and Memory Foundation

## Status

Phase 3 is complete as a production-grade foundation:

```text
Day 14-24: RAG Retrieval, Agent Integration, and Memory
```

Phase 3 was split into:

- Phase 3A: Day 14-18 - RAG Ingestion + Indexing Foundation.
- Phase 3B: Day 19-21 - RAG Retrieval + Agent Integration.
- Phase 3C: Day 22-23 - Memory Foundation.
- Phase 3 Closure: Day 24.

## What Users Can Do Now

Users can create a knowledge base, upload a text or Markdown document, ingest it, chunk it, index it with deterministic mock embeddings, search it, and call that search path from an agent run through a safe read-only tool.

Users can also create scoped memory items, list them, inspect them, delete them, and explicitly opt a model run into scoped memory context injection.

Current user-facing shape:

```text
Knowledge base workflow:
create KB -> upload document -> ingest -> chunk -> index -> retrieve

Agent RAG workflow:
run input tool request -> kb_search -> cited retrieval results -> tool audit timeline

Memory workflow:
create memory -> list/inspect/delete -> explicit scoped retrieval -> model context injection
```

## Completed RAG Capabilities

- Knowledge base domain model.
- Document domain model.
- Knowledge base and document storage.
- Knowledge base and document API.
- Knowledge base and document CLI.
- Local document upload.
- Local object store abstraction.
- Ingestion job model and storage.
- Manual ingestion API and CLI.
- Text and Markdown parser.
- Parsed text artifacts.
- Document chunk domain model.
- Deterministic chunker.
- Document chunk storage.
- Embedding provider interface.
- Deterministic mock embedding provider.
- Chunk embedding storage.
- JSON vector-store foundation.
- Document indexing service.
- Retrieval service.
- Citation builder.
- Retrieval API.
- Retrieval CLI.
- `kb_search` read-only tool.
- Agent runtime integration for explicit `kb_search` tool requests.
- Worker integration for queued `kb_search` tool runs.
- Deterministic RAG behavior eval foundation.
- Regression cases for relevance, citations, empty knowledge bases, and missing knowledge bases.

## Completed Memory Capabilities

- `MemoryType` enum:
  - `short_term`
  - `task_context`
  - `user_preference`
  - `long_term`
- `MemoryItem` domain model.
- Required memory scope.
- Structured JSON memory content.
- Optional `source_run_id`.
- Confidence score.
- Memory metadata.
- `memory_items` storage table.
- Memory repository create/list/get/delete operations.
- Memory API create/list/inspect/delete operations.
- Memory CLI create/list/inspect/delete operations.
- Scoped memory retrieval service.
- Optional memory type filtering.
- Deterministic memory prompt rendering.
- Explicit runtime memory config parsing.
- Agent model context injection through a system message.
- `memory_retrieved` run event visibility.
- Model run output metadata showing memory item IDs used.

## API Surface

RAG and knowledge base APIs:

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

Memory APIs:

```http
POST   /v1/memory
GET    /v1/memory
GET    /v1/memory/{memory_id}
DELETE /v1/memory/{memory_id}
```

## CLI Surface

RAG and knowledge base CLI:

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

Memory CLI:

```bash
agent-kernel memory create --type user_preference --scope user:<id> --content '{"language":"zh"}'
agent-kernel memory list --scope user:<id>
agent-kernel memory inspect <memory-id>
agent-kernel memory delete <memory-id>
```

## Runtime Input Shapes

Explicit `kb_search` tool request:

```json
{
  "tool": {
    "name": "kb_search",
    "arguments": {
      "knowledge_base_id": "00000000-0000-0000-0000-000000000000",
      "query": "What is our deployment policy?",
      "top_k": 5
    }
  }
}
```

Explicit memory context injection:

```json
{
  "task": "Summarize this for me.",
  "memory": {
    "scopes": ["user:roy", "task:deploy"],
    "types": ["user_preference", "task_context"],
    "limit": 10
  }
}
```

## Test And Eval Coverage

Phase 3 added coverage for:

- Local object store behavior.
- Document upload API.
- Ingestion jobs.
- Text/Markdown parsing.
- Chunking.
- Chunk repository behavior.
- Mock embeddings.
- Chunk embedding repository behavior.
- Document indexing.
- Retrieval ranking.
- Citation construction.
- Retrieval API.
- Retrieval CLI.
- `kb_search` tool execution.
- Runtime `kb_search` execution.
- Worker `kb_search` execution.
- Deterministic RAG behavior evals.
- Memory repository behavior.
- Memory API CRUD.
- Memory CLI commands.
- Memory retrieval.
- Runtime memory context injection.
- Invalid memory config failures.

## Known Limitations

These limitations are intentional for Phase 3:

- Embeddings use deterministic mock vectors by default.
- OpenAI embeddings are not implemented yet.
- Vector storage uses JSON vectors for SQLite-compatible tests.
- pgvector-native vector columns and indexes are not implemented yet.
- Retrieval is vector-only.
- BM25, hybrid search, RRF, query rewriting, and reranking are not implemented yet.
- Ingestion and indexing are manual synchronous operations.
- Async ingestion/indexing worker is not implemented yet.
- Document permissions are not advanced beyond current project boundaries.
- `kb_search` is available through explicit tool requests, not provider-native function calling.
- Agent planning does not automatically decide when to call `kb_search`.
- Retrieval citations are present in retrieval/tool results, but final answer synthesis with citations is not implemented yet.
- Memory retrieval is exact scope/type filtering, not semantic memory retrieval.
- Memory writes are explicit only.
- Automatic memory writes and memory consolidation are not implemented yet.
- Memory conflict resolution with current user instructions is not implemented yet.
- Memory observability spans and metrics are deferred to Phase 4.

## Deferred Agentic RAG Scope

Phase 3 intentionally stops at explicit tool requests and cited retrieval results.

Provider-native function calling is deferred because it requires provider-specific
tool schemas and response parsing, a durable model/tool/model execution loop,
intermediate tool-call persistence, approval/retry/resume handling across
provider-returned tool calls, prompt/tool schema versioning, and behavior evals
for automatic tool choice. Phase 3 validates the underlying tool execution path
through explicit `kb_search` requests without mixing it with automatic planning.

Final answer synthesis with citations is deferred because production-grade cited
answers must verify that final claims are grounded in retrieved chunks, avoid
hallucinated citations, handle multiple chunks per answer, refuse when evidence
is insufficient, and defend against prompt injection in retrieved documents.
Phase 3 makes citation data available in retrieval and `kb_search` outputs;
final answer synthesis should be implemented after provider-native tool calling,
guardrails, and stronger RAG evals are in place.

## Closure Verification

Day 24 verification:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
git diff --check
```

## Next Phase

Phase 4 starts on Day 25:

```text
Observability and Evals
```

The next focus is making runtime behavior inspectable and measurable:

- Structured logs.
- OpenTelemetry spans.
- Trace IDs.
- Model/tool/retrieval/memory metrics.
- Cost tracking.
- Eval reporting improvements.
