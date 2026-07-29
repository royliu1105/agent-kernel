# Day 18: Embedding Interface and Vector Store Foundation

## Goal

Add the first embedding/indexing layer so chunked documents can be converted into deterministic vectors and stored for future retrieval.

Day 18 should establish this path:

```text
chunked Document -> embedding provider -> chunk embedding records -> indexed Document
```

## Scope

Day 18 should cover:

- Phase 3 planning alignment.
- Chunk embedding domain model.
- Chunk embedding storage table and Alembic migration.
- Chunk embedding repository operations.
- Embedding provider interface.
- Deterministic mock embedding provider.
- Basic vector similarity helper in storage/repository layer.
- Synchronous document indexing service.
- API endpoint to index a chunked document.
- API endpoint to list document embeddings.
- CLI command to index a document.
- CLI command to list document embeddings.
- Unit tests for embedding provider, repository, service, and CLI.
- Integration tests for indexing API.
- RAG spec, storage architecture, and milestone updates.

Day 18 should not cover:

- OpenAI embeddings.
- Async ingestion/indexing worker.
- pgvector-native column/index.
- User-facing retrieval API.
- Retriever abstraction.
- `kb_search` tool.
- Citation building.
- Reranking.
- Memory implementation.

## Domain Terms

- Embedding provider: component that converts text into fixed-size numeric vectors.
- Chunk embedding: persisted vector associated with one `DocumentChunk`.
- Vector store foundation: repository boundary for storing and similarity-scoring vectors. Day 18 uses JSON vectors for SQLite-compatible tests; pgvector-native storage is a later enhancement behind the same boundary.

## Tasks

- [x] Check current git status.
- [x] Read `docs/specs/rag.md`.
- [x] Read existing storage/API/CLI/RAG chunking patterns.
- [x] Create Day 18 daily plan.
- [x] Add `ChunkEmbedding` core model.
- [x] Add storage record and migration.
- [x] Add repository operations.
- [x] Add embedding provider interface.
- [x] Add deterministic mock embedding provider.
- [x] Add indexing service.
- [x] Add index API endpoints.
- [x] Add index CLI commands.
- [x] Add unit tests.
- [x] Add integration tests.
- [x] Update RAG spec.
- [x] Update storage architecture docs.
- [x] Update milestones.
- [x] Run verification commands.

## Acceptance

- [x] A chunked document can be indexed manually.
- [x] Each document chunk receives one persisted embedding for the selected model.
- [x] Re-indexing replaces prior embeddings for the document/model.
- [x] Document status moves from `chunked` to `embedding` to `indexed`.
- [x] Embedding records include model, dimension count, vector, checksum, and metadata.
- [x] Vector similarity can rank embeddings for a provided vector inside repository tests.
- [x] CLI can request indexing and list embeddings through the API.
- [x] Day 18 does not expose retrieval, citations, `kb_search`, or OpenAI embeddings.

## Verification

Run the available checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_embeddings.py tests/unit/test_chunk_embedding_repository.py tests/unit/test_cli_commands.py tests/integration/test_api_knowledge_base.py
```

## Notes

- JSON vectors keep SQLite tests simple while preserving the vector-store boundary.
- pgvector can replace or augment the storage implementation without changing public API semantics.
- Mock embeddings are deterministic so evals and regression tests remain stable.

## Completion Notes

- Added deterministic chunk embeddings and indexing service.
- Added manual index API and CLI.
- OpenAI embeddings, pgvector-native indexes, retriever, citations, `kb_search`, and memory remain deferred.

Verification passed:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 18：请按照 docs/daily/day-18.md 执行 Embedding Interface and Vector Store Foundation。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-18.md、docs/specs/rag.md、docs/storage-architecture.md 和 docs/milestones.md。
- 只实现 Day 18 scope 内的内容。
- 今天只做 chunked Document -> embedding provider -> chunk embedding records -> indexed Document。
- 不做 OpenAI embeddings、async worker、pgvector-native column/index、retriever、retrieval API、kb_search tool、citation builder 或 memory。
- Mock embeddings 必须 deterministic。
- Vector store 先保持 SQLite-test-compatible，但 repository 边界要能后续替换为 pgvector。
- 完成后运行 Day 18 verification commands。
- 更新 docs/daily/day-18.md 的 checklist。
- 更新 specs、storage docs 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
