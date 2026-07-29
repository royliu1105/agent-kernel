# Day 17: Chunker and DocumentChunk Storage Foundation

## Goal

Add the parsed-text chunking layer so ingested documents can be split into durable chunks for future embedding and retrieval.

Day 17 should establish this path:

```text
parsed Document -> parsed text artifact -> chunker -> DocumentChunk records -> chunked Document
```

## Scope

Day 17 should cover:

- Phase 3 planning alignment.
- `DocumentChunk` domain model.
- Document chunk storage table and Alembic migration.
- Document chunk repository operations.
- Deterministic text chunker with overlap.
- Chunking service for synchronous manual chunking.
- API endpoint to chunk a parsed document.
- API endpoint to list document chunks.
- CLI command to chunk a document.
- CLI command to list document chunks.
- Unit tests for chunker, repository, and CLI.
- Integration tests for chunk API.
- RAG spec, storage architecture, and milestone updates.

Day 17 should not cover:

- Async ingestion worker.
- Embeddings.
- OpenAI embeddings.
- Mock embeddings.
- pgvector storage.
- Retriever.
- `kb_search` tool.
- Citation building.
- Reranking.
- Memory implementation.

## Domain Terms

- Document chunk: durable text segment with source offsets and stable ordering.
- Chunk index: zero-based order of a chunk within one document.
- Token estimate: approximate token count for scheduling, cost planning, and future retrieval limits.

## Tasks

- [x] Check current git status.
- [x] Read `docs/specs/rag.md`.
- [x] Read existing storage/API/CLI/RAG ingestion patterns.
- [x] Create Day 17 daily plan.
- [x] Add `chunked` document status.
- [x] Add `DocumentChunk` core model.
- [x] Add storage record and migration.
- [x] Add repository operations.
- [x] Add deterministic text chunker.
- [x] Add chunking service.
- [x] Add chunk API endpoints.
- [x] Add chunk CLI commands.
- [x] Add unit tests.
- [x] Add integration tests.
- [x] Update RAG spec.
- [x] Update storage architecture docs.
- [x] Update milestones.
- [x] Run verification commands.

## Acceptance

- [x] A parsed text/Markdown document can be chunked manually.
- [x] Chunk records are persisted with stable indexes.
- [x] Chunk records include content, offsets, checksum, and token estimate.
- [x] Document status moves from `parsed` to `chunking` to `chunked`.
- [x] Re-chunking replaces old chunks for the document.
- [x] Chunk listing returns chunks in index order.
- [x] CLI can request chunking and list chunks through the API.
- [x] Day 17 does not embed, retrieve, cite, or call tools.

## Verification

Run the available checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_chunker.py tests/unit/test_document_chunk_repository.py tests/unit/test_cli_commands.py tests/integration/test_api_knowledge_base.py
```

## Notes

- Day 17 stores chunk content in Postgres to keep v0.1 retrieval and citation inspection simple.
- Embedding vectors are intentionally deferred to keep storage responsibilities separate.
- The chunker is deterministic so future evals and regression tests can rely on stable chunk indexes.

## Completion Notes

- Added durable document chunks and chunking service.
- Added manual chunk API and CLI.
- Async worker, embeddings, vector storage, retrieval, citations, and memory remain deferred.

Verification passed:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 17：请按照 docs/daily/day-17.md 执行 Chunker and DocumentChunk Storage Foundation。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-17.md、docs/specs/rag.md、docs/storage-architecture.md 和 docs/milestones.md。
- 只实现 Day 17 scope 内的内容。
- 今天只做 parsed Document -> parsed text artifact -> chunker -> DocumentChunk records -> chunked Document。
- 不做 async ingestion worker、embedding、pgvector retrieval、kb_search tool、citation builder 或 memory。
- Chunker 必须 deterministic，chunk index 必须稳定。
- 不要把 embeddings 或 vector schema 提前塞进 chunk 表。
- 完成后运行 Day 17 verification commands。
- 更新 docs/daily/day-17.md 的 checklist。
- 更新 specs、storage docs 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
