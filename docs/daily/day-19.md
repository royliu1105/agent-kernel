# Day 19: Retriever, Citation Builder, Retrieval API, and CLI

## Goal

Turn indexed document chunks into a user-facing retrieval path.

Day 19 should establish this path:

```text
query -> query embedding -> vector search -> ranked chunks -> citations -> API/CLI response
```

## Scope

Day 19 should cover:

- Retrieval domain models.
- Retriever service.
- Citation builder.
- Query embedding with the deterministic mock embedding provider.
- Vector similarity search over persisted chunk embeddings.
- Top-k retrieval constrained to one knowledge base.
- Retrieval result enrichment with document and chunk metadata.
- Retrieval API endpoint.
- Retrieval CLI command.
- Unit tests for retriever, citations, and retrieval edge cases.
- Integration tests for retrieval API.
- CLI tests for retrieval command wiring.
- RAG spec and milestone updates.

Day 19 should not cover:

- `kb_search` tool.
- Agent runtime integration.
- Persisted retrieval calls.
- Memory.
- OpenAI embeddings.
- pgvector-native vector columns or indexes.
- BM25 keyword search.
- Hybrid search.
- RRF.
- Reranking.
- Query rewriting.

## Domain Terms

- Retriever: service that embeds a query and fetches relevant indexed chunks from a knowledge base.
- Retrieval result: ranked chunk match with similarity score and source metadata.
- Citation: stable source reference for a retrieved chunk, including knowledge base, document, chunk, and character offsets.
- Top-k: maximum number of ranked chunks returned to the caller.

## Tasks

- [x] Check current git status.
- [x] Read `docs/specs/rag.md`.
- [x] Read existing embedding, storage, API, CLI, and test patterns.
- [x] Create Day 19 daily plan.
- [x] Add retrieval domain models.
- [x] Add citation builder.
- [x] Add retriever service.
- [x] Add storage support needed to hydrate retrieved chunks and documents.
- [x] Add retrieval API schema.
- [x] Add retrieval API endpoint.
- [x] Add retrieval CLI command.
- [x] Add unit tests.
- [x] Add integration tests.
- [x] Update RAG spec.
- [x] Update milestones.
- [x] Run verification commands.

## Acceptance

- [x] A caller can search one knowledge base by text query.
- [x] Retrieval embeds the query with the selected embedding provider.
- [x] Retrieval ranks indexed chunks by vector similarity.
- [x] Retrieval returns at most `top_k` matches.
- [x] Retrieval returns citations with knowledge base ID, document ID, document title, chunk ID, chunk index, and character offsets.
- [x] Empty knowledge bases return an empty result set.
- [x] Missing knowledge bases return a not-found error.
- [x] CLI can call the retrieval API and print JSON.
- [x] Day 19 does not implement `kb_search`, agent runtime integration, memory, RRF, BM25, hybrid search, or reranking.

## Verification

Run the available checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_retrieval.py tests/unit/test_cli_commands.py tests/integration/test_api_knowledge_base.py
```

## Notes

- Retrieval remains deterministic because Day 19 uses `MockEmbeddingProvider`.
- JSON vector search is acceptable for the current SQLite-compatible foundation.
- Citations should preserve enough source identity to support Day 20 agent timeline integration and Day 21 behavior evals.

## Completion Notes

- Added retrieval domain models, citation builder, and retriever service.
- Added `POST /v1/knowledge-bases/{knowledge_base_id}/retrieve`.
- Added `agent-kernel kb search <knowledge-base-id> --query "..."`.
- Added unit, integration, and CLI command coverage.
- Updated RAG spec and milestones.
- Confirmed Day 19 does not implement `kb_search`, agent runtime integration, memory, RRF, BM25, hybrid search, or reranking.

Verification passed:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 19：请按照 docs/daily/day-19.md 执行 Retriever, Citation Builder, Retrieval API, and CLI。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-19.md、docs/specs/rag.md、docs/milestones.md 和现有 embedding/storage/API/CLI/test patterns。
- 只实现 Day 19 scope 内的内容。
- 今天只做 query -> query embedding -> vector search -> ranked chunks -> citations -> API/CLI response。
- 不做 kb_search tool、agent runtime integration、persisted retrieval calls、memory、OpenAI embeddings、pgvector-native index、BM25、hybrid search、RRF、reranking 或 query rewriting。
- Retrieval 必须 deterministic，默认使用 MockEmbeddingProvider。
- Citation 必须包含 KB、document、chunk 和 char offset 信息。
- 完成后运行 Day 19 verification commands。
- 更新 docs/daily/day-19.md 的 checklist。
- 更新 RAG spec 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
