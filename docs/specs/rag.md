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
uploaded -> parsing -> chunking -> embedding -> indexed -> failed
```

Detailed ingestion semantics will be completed during Phase 3 implementation.

## API / CLI

Expected API:

```http
POST /v1/documents
GET  /v1/documents
GET  /v1/documents/{document_id}
POST /v1/documents/{document_id}/ingest
POST /v1/retrieval/query
```

Expected CLI:

```bash
agent-kernel doc upload ./docs/*.md
agent-kernel doc ingest <document-id>
agent-kernel kb query "What is our deployment policy?"
```

## Failure Modes

- Unsupported file type.
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
- Final answer includes citations.

## Acceptance Criteria

- A document can be uploaded, ingested, and retrieved.
- Retrieval can be used as a tool call.
- Retrieved chunks and citations are visible in the run timeline.
