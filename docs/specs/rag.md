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
registered -> uploaded -> parsing -> chunking -> embedding -> indexed
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

## API / CLI

Expected API:

```http
POST /v1/knowledge-bases
GET  /v1/knowledge-bases
GET  /v1/knowledge-bases/{knowledge_base_id}
POST /v1/knowledge-bases/{knowledge_base_id}/documents
GET  /v1/knowledge-bases/{knowledge_base_id}/documents
GET  /v1/documents/{document_id}
POST /v1/documents/{document_id}/ingest
POST /v1/retrieval/query
```

Expected CLI:

```bash
agent-kernel kb create --name "Engineering Handbook"
agent-kernel kb list
agent-kernel kb inspect <knowledge-base-id>
agent-kernel document register <knowledge-base-id> --title "Deploy" --source-uri object://local/docs/deploy.md
agent-kernel document list <knowledge-base-id>
agent-kernel document inspect <document-id>
agent-kernel document upload <knowledge-base-id> ./docs/*.md
agent-kernel document ingest <document-id>
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
