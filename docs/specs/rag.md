# Feature Spec: RAG

## Goal

Provide a knowledge base pipeline for document upload, ingestion, chunking, embedding, retrieval, and cited agent answers.

## Non-Goals

- Competing with dedicated enterprise knowledge base products.
- Advanced reranking in v0.1.
- Multiple vector database backends in v0.1.
- Complex document permission inheritance in v0.1.

## User Stories

- As a user, I can upload documents.
- As a user, I can ingest documents into searchable chunks.
- As an agent, I can call `kb_search`.
- As a reviewer, I can inspect which chunks were retrieved and cited.

## Domain Model

Initial entities:

- `KnowledgeBase`
- `Document`
- `DocumentChunk`
- `IngestionJob`
- `RetrievalQuery`
- `RetrievalResult`
- `Citation`

MVP storage:

```text
Document metadata -> Postgres
Document body/artifacts -> LocalObjectStore
Embeddings -> pgvector
```

## State Transitions

Document ingestion states:

```text
registered -> uploaded -> parsing -> parsed -> chunking -> chunked -> embedding -> indexed
                           \-> failed
```

Detailed ingestion semantics will be completed during Phase 3 implementation.

## Day 14 Metadata Foundation

Day 14 implements the RAG control-plane foundation:

- Create/list/inspect knowledge bases.
- Register document metadata under a knowledge base.
- List documents for a knowledge base.
- Inspect one document.
- Persist document lifecycle status, source URI, MIME type, checksum, size, and metadata.

Day 14 intentionally does not store document bytes, parse files, chunk text, call embeddings, write vectors, retrieve content, or expose `kb_search`.

## Day 15 Upload Foundation

Day 15 implements the first RAG data-plane path:

- Upload a local file through API multipart upload.
- Write document bytes to `LocalObjectStore`.
- Create `Document` metadata with `uploaded` status.
- Persist `source_uri` as `object://local/<object-key>`.
- Persist checksum, size, MIME type, original filename, and object key.
- Enforce a conservative upload size limit.

Day 15 intentionally does not parse uploaded files, chunk text, call embeddings, write vectors, retrieve content, or expose `kb_search`.

## Day 16 Ingestion and Parser Foundation

Day 16 implements the first manual ingestion path:

- Create durable `IngestionJob` records.
- Parse uploaded text/Markdown documents.
- Move document status from `uploaded` to `parsing` to `parsed`.
- Store parsed text as an object-store artifact.
- Persist parsed text URI, checksum, byte size, and character count on the ingestion job.
- Record unsupported documents as failed ingestion jobs.

Day 16 intentionally does not run an async ingestion worker, chunk parsed text, call embeddings, write vectors, retrieve content, or expose `kb_search`.

## Day 17 Chunking Foundation

Day 17 implements deterministic parsed-text chunking:

- Read parsed text artifacts from `LocalObjectStore`.
- Split text into stable chunks with character overlap.
- Persist `DocumentChunk` records in Postgres.
- Store chunk content, index, source offsets, checksum, token estimate, and metadata.
- Move document status from `parsed` to `chunking` to `chunked`.
- Replace existing chunks when a document is re-chunked.

Day 17 intentionally does not generate embeddings, write vectors, retrieve chunks, build citations, or expose `kb_search`.

## Day 18 Embedding and Vector Store Foundation

Day 18 implements deterministic chunk embedding/indexing:

- Define an embedding provider interface.
- Add deterministic mock embeddings for tests and local development.
- Persist chunk embeddings in `chunk_embeddings`.
- Store chunk ID, document ID, model, dimensions, vector, checksum, and metadata.
- Move document status from `chunked` to `embedding` to `indexed`.
- Replace existing embeddings when a document/model is re-indexed.
- Add repository-level cosine similarity scoring for future retriever work.

Day 18 intentionally does not call OpenAI embeddings, use pgvector-native columns/indexes, expose retrieval, build citations, or expose `kb_search`.

## Day 68 OpenAI Embeddings Backend

Day 68 adds a real OpenAI embeddings provider behind the existing
`EmbeddingProvider` interface:

- `OpenAIEmbeddingProvider` calls the OpenAI `/v1/embeddings` endpoint.
- Default model: `text-embedding-3-small`.
- Default dimensions: `1536`.
- Configuration helpers read:
  - `OPENAI_API_KEY`
  - `OPENAI_EMBEDDING_MODEL`
  - `OPENAI_EMBEDDING_DIMENSIONS`
- Empty input returns an empty vector list without network I/O.
- Missing API keys, HTTP failures, malformed responses, count mismatches,
  index mismatches, and dimension mismatches raise typed `OpenAIEmbeddingError`
  failures.
- Tests use injectable HTTP transport and do not perform live OpenAI calls.
- `DocumentIndexingService` can persist vectors returned by
  `OpenAIEmbeddingProvider`.

Day 68 intentionally does not make OpenAI embeddings the default provider,
does not add pgvector-native storage, and does not add live OpenAI calls to CI.

## Day 69 pgvector-Native Vector Store

Day 69 adds an optional pgvector-native storage and similarity-search path:

- `AGENT_KERNEL_VECTOR_STORE=auto` uses pgvector on PostgreSQL and JSON-vector
  fallback elsewhere.
- `AGENT_KERNEL_VECTOR_STORE=json` always uses the SQLite-compatible JSON-vector
  path.
- `AGENT_KERNEL_VECTOR_STORE=pgvector` requires PostgreSQL and fails clearly on
  other databases.
- Migration `0013_pgvector_embeddings` is a no-op on SQLite and, on PostgreSQL,
  installs the `vector` extension, adds `chunk_embeddings.vector_pg`, backfills
  it from the existing JSON `vector` column, and creates a cosine HNSW index.
- `ChunkEmbeddingRepository.replace_for_document` keeps writing JSON vectors
  for compatibility and also populates `vector_pg` when pgvector is enabled.
- `ChunkEmbeddingRepository.similarity_search` orders by pgvector cosine
  distance on PostgreSQL:

```sql
ORDER BY ce.vector_pg::vector(<dimensions>) <=> CAST(:query_vector AS vector(<dimensions>))
```

- The default migration creates a cosine HNSW expression index for 1536
  dimensions, matching the default `text-embedding-3-small` configuration.

Day 69 intentionally keeps JSON vectors as the compatibility source of truth
for local tests and does not add BM25, hybrid search, RRF, reranking, query
rewriting, or live Postgres CI.

## Phase 3B Retrieval and Agent Integration Plan

Phase 3B completes the RAG usage path:

```text
Day 19: Retriever + Citation Builder + Retrieval API/CLI
Day 20: kb_search Tool + Agent Runtime Integration
Day 21: RAG Behavior Evals + Regression Cases
```

### Day 19 Retrieval Foundation

Day 19 should implement:

- Query embedding with the deterministic mock embedding provider.
- Vector similarity retrieval over persisted chunk embeddings.
- Top-k retrieval results.
- Citation objects linked to knowledge base, document, chunk, and character offsets.
- Retrieval API: `POST /v1/knowledge-bases/{knowledge_base_id}/retrieve`.
- Retrieval CLI: `agent-kernel kb search <knowledge-base-id> --query "..."`.

Day 19 should not implement `kb_search` tool integration, agent runtime integration, memory, RRF, BM25, hybrid search, or reranking.

### Day 20 Agent RAG Integration

Day 20 should implement:

- `kb_search` as a safe/read-only built-in tool.
- Runtime support for agents to invoke `kb_search`.
- Run output or timeline visibility for retrieved chunks and citations.
- API and worker runtime composition with a RAG-aware tool registry.
- Explicit tool-request support for agent runs that call `kb_search`.

Implemented Day 20 API/runtime shape:

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

Day 20 should not implement provider-native function calling, automatic model planning, memory, or advanced retrieval ranking.

### Day 21 RAG Behavior Evals

Day 21 should implement:

- Deterministic RAG behavior eval cases.
- Regression cases for retrieval relevance.
- Regression cases for citation presence.
- Failure cases for empty or missing knowledge bases.

Implemented Day 21 eval foundation:

- `RagEvalCase` for deterministic retrieval expectations.
- `RagEvalRunner` for evaluating retrieval callables.
- Assertion-level failure messages for missing relevance terms, missing citations, empty results, and expected errors.
- Regression coverage for real `Retriever` behavior.

Day 21 should not implement large benchmark suites, rerankers, production analytics, LLM-as-judge, full eval API/CLI, or persisted eval runs.

## Deferred Retrieval Enhancements

The following are valuable but deferred beyond Phase 3:

- BM25 / keyword index.
- Hybrid search.
- RRF.
- Reranking.
- Query rewriting.

## API / CLI

Expected API:

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

Expected CLI:

```bash
agent-kernel kb create --name "Engineering Handbook"
agent-kernel kb list
agent-kernel kb inspect <knowledge-base-id>
agent-kernel document register <knowledge-base-id> --title "Deploy" --source-uri object://local/docs/deploy.md
agent-kernel document upload <knowledge-base-id> ./docs/deploy.md
agent-kernel document list <knowledge-base-id>
agent-kernel document inspect <document-id>
agent-kernel document ingest <document-id>
agent-kernel ingestion list <document-id>
agent-kernel ingestion inspect <job-id>
agent-kernel document chunk <document-id>
agent-kernel chunk list <document-id>
agent-kernel chunk inspect <chunk-id>
agent-kernel document index <document-id>
agent-kernel embedding list <document-id>
agent-kernel kb search <knowledge-base-id> --query "What is our deployment policy?"
```

## Failure Modes

- Unsupported file type.
- Upload exceeds size limit.
- Object store write failure.
- Invalid object URI.
- Parser failure.
- Chunking failure.
- Embedding provider failure.
- Vector insert failure.
- Retrieval returns irrelevant results.
- Citation cannot be built.

## Security

- Uploaded document access must be scoped.
- Retrieved content may contain prompt injection attempts.
- Full document content should not be logged by default.
- Large files require size limits.

## Observability

- Ingestion spans by phase.
- Chunk count.
- Embedding latency.
- Retrieval latency.
- Retrieved chunk IDs.
- Citation count.

## Test Plan

- Upload text/Markdown document.
- Ingest document into chunks.
- Store embeddings.
- Retrieve relevant chunks.
- Agent calls `kb_search`.
- Retrieval and `kb_search` tool results include citations.

## Acceptance Criteria

- A document can be uploaded, ingested, and retrieved.
- Retrieval can be used as a tool call.
- Retrieved chunks and citations are visible in the run timeline.

## Phase 3 Baseline

Phase 3 establishes a tested RAG baseline:

- Manual document upload, ingestion, chunking, indexing, and retrieval.
- Deterministic mock embeddings.
- SQLite-compatible JSON vector storage.
- Citation metadata for retrieved chunks.
- `kb_search` as a read-only tool.
- Explicit tool-request runtime integration.
- Deterministic RAG behavior evals and regression cases.

Phase 3 intentionally does not implement:

- pgvector-native vector columns or indexes.
- Async ingestion/indexing worker.
- BM25, hybrid search, RRF, query rewriting, or reranking.
- Provider-native function calling.
- Automatic agent planning for when to call `kb_search`.
- Final answer synthesis that automatically includes citations.

## Deferred: Provider-Native Function Calling And Answer Synthesis

These capabilities are part of the long-term production target, but they are not
part of the Phase 3 baseline.

Provider-native function calling should be implemented only after Agent Kernel
has provider-specific tool-call adapters, a durable model/tool/model run loop,
tool-result-to-model message handling, tool-call persistence, approval/retry/
fallback/resume semantics, prompt and tool schema versioning, and behavior evals
that can verify automatic tool choice.

Final answer synthesis with citations should be implemented only after the RAG
path can prove that final claims are grounded in retrieved chunks. The required
baseline includes citation-grounded answer evals, insufficient-evidence refusal
behavior, multi-chunk citation handling, document prompt-injection guardrails,
and clear observability for retrieved evidence versus generated claims.

The current Phase 3 implementation deliberately exposes `kb_search` through an
explicit tool request. That gives the project a testable retrieval and citation
foundation before adding provider-native planning and generated cited answers.
