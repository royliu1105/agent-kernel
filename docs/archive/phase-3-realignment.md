# Phase 3 Realignment

## Summary

Phase 3 is realigned from:

```text
Day 14-18: RAG and Memory
```

to:

```text
Day 14-24: RAG Retrieval, Agent Integration, and Memory
```

The project goal is not reduced. The change makes the plan match the production-grade delivery style already used in Days 14-18.

## Why This Changed

The original Day 14-18 scope included too many production-grade capabilities for a five-day implementation window:

- Document metadata.
- Upload and object storage.
- Ingestion jobs.
- Parsing.
- Chunking.
- Embeddings.
- Vector storage.
- Retrieval.
- Citations.
- `kb_search` tool.
- Agent integration.
- Memory domain.
- Memory retrieval.

Days 14-18 implemented each layer as a tested vertical slice with domain models, storage, migrations, repositories, API, CLI, tests, and docs. That produced a stronger foundation, but it means Phase 3 needs additional days for retrieval, agent integration, memory, and closure.

## Completed: Phase 3A

Phase 3A is complete:

```text
Day 14-18: RAG Ingestion + Indexing Foundation
```

Completed capabilities:

- Knowledge base metadata.
- Document metadata.
- Document upload.
- Local object store.
- Ingestion jobs.
- Text/Markdown parser.
- Parsed text artifacts.
- Document chunks.
- Deterministic chunker.
- Embedding provider interface.
- Deterministic mock embeddings.
- JSON vector-store foundation.
- API and CLI operations for upload, ingest, chunk, index, and inspection.

Current end-to-end foundation:

```text
create KB
-> upload document
-> ingest / parse
-> chunk
-> embed with mock provider
-> persist embeddings
-> indexed document
```

## Completed: Phase 3B

Phase 3B completed retrieval and agent integration:

```text
Day 19-21: RAG Retrieval + Agent Integration
```

Completed days:

- Day 19: Retriever + Citation Builder + Retrieval API/CLI.
- Day 20: `kb_search` Tool + Agent Runtime Integration.
- Day 21: RAG Behavior Evals + Regression Cases.

Completed acceptance:

- Query embedding can retrieve relevant chunks.
- Retrieval response includes citation metadata.
- Agent can call `kb_search`.
- Retrieved chunks and citations are visible in run output or run timeline.
- Regression tests cover core RAG behavior.

## Completed: Phase 3C

Phase 3C completed memory foundation:

```text
Day 22-23: Memory Foundation
```

Completed days:

- Day 22: Memory Domain + Storage + API/CLI.
- Day 23: Memory Retrieval + Agent Context Integration.

Completed acceptance:

- Memory items can be written, listed, inspected, and deleted.
- Memory records are scoped.
- User preferences and task context have explicit types.
- Memory retrieval can provide context to an agent run.
- Memory behavior is inspectable and tested.

## Completed: Phase 3 Closure

Phase 3 closure completed:

```text
Day 24: Phase 3 Closure + Summary Docs + Full Verification
```

Closure includes:

- Confirm Phase 3 functionality forms a coherent baseline.
- Update phase summary docs.
- Update specs and milestones.
- Document MVP limitations.
- Run full verification.
- Leave Day 25 ready for Phase 4.

## Explicitly Deferred Beyond Phase 3

The following are not required for Phase 3 closure:

- OpenAI embeddings.
- pgvector-native vector column and index.
- Hybrid search.
- BM25.
- RRF.
- Reranking.
- Async ingestion/indexing worker.
- Advanced document permission inheritance.

These remain valuable but are post-Phase-3 enhancements.

## Updated Timeline

The v0.1 target is realigned:

```text
Day 1-38: v0.1.0 published release
Day 39-51: Public Alpha
Day 52-75: Beta production hardening
Day 76-90: v1.0 release candidate and release work
```

This preserves the original quality bar while making the remaining scope explicit and traceable.
