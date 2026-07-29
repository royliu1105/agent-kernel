# Day 14: Knowledge Base and Document Storage Foundation

## Goal

Start Phase 3 by adding the durable foundation for knowledge bases and documents.

Day 14 should establish this path:

```text
create knowledge base -> register document metadata -> inspect/list document status
```

## Scope

Day 14 should cover:

- Phase 3 planning alignment.
- Knowledge base and document domain models.
- Document status lifecycle for metadata-only ingestion preparation.
- Postgres/SQLite-compatible storage tables.
- Alembic migration for knowledge bases and documents.
- Repository operations for create/get/list.
- API endpoints for knowledge bases and document metadata.
- CLI commands for knowledge base and document metadata operations.
- Unit tests for domain/storage/CLI.
- Integration tests for API.
- RAG spec and milestone updates.

Day 14 should not cover:

- File upload bytes.
- Object storage writes.
- Ingestion worker.
- Parser implementation.
- Chunking.
- Embeddings.
- pgvector retrieval.
- `kb_search` tool.
- Agent run loop RAG integration.
- Memory implementation.
- Document-level authorization.

## Domain Terms

- Knowledge base: a named collection of documents that agents can later search.
- Document: metadata record for a source object that will later be uploaded, parsed, chunked, embedded, and indexed.
- Source URI: where the original source can be found later, such as a local object-store key or external reference.

## Tasks

- [x] Check current git status.
- [x] Read Phase 3 section in `docs/development-plan.md`.
- [x] Read `docs/specs/rag.md`.
- [x] Read existing storage/API/CLI patterns.
- [x] Add knowledge base and document core models.
- [x] Add storage records and relationships.
- [x] Add Alembic migration.
- [x] Add repository operations.
- [x] Export storage repository.
- [x] Add API schemas and endpoints.
- [x] Add CLI commands.
- [x] Add unit tests.
- [x] Add integration tests.
- [x] Update RAG spec with Day 14 boundary.
- [x] Update milestone checklist.
- [x] Run verification commands.

## Acceptance

- [x] A knowledge base can be created and loaded.
- [x] Knowledge bases can be listed.
- [x] A document can be registered under a knowledge base.
- [x] Documents can be listed for a knowledge base.
- [x] Missing knowledge bases/documents return clear not-found behavior.
- [x] API exposes KB/document metadata operations.
- [x] CLI can call the KB/document metadata endpoints.
- [x] Day 14 does not persist document bytes or perform ingestion.

## Verification

Run the available checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_storage_repositories.py tests/unit/test_cli_commands.py tests/integration/test_api_knowledge_base.py
```

## Notes

- Day 14 intentionally creates the metadata/control-plane layer before the data-plane upload and ingestion pipeline.
- The storage model should remain compatible with Postgres in production and SQLite in local tests.
- Document content must not be stored in run events or API logs by default.

## Completion Notes

- Added `KnowledgeBase`, `Document`, and document lifecycle statuses.
- Added relational storage tables for `knowledge_bases` and `documents`.
- Added repository, API, and CLI operations for metadata creation and inspection.
- Updated RAG spec and Phase 3 milestone status.
- Full RAG ingestion and retrieval remain deferred to later Phase 3 days.

Verification passed:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 14：请按照 docs/daily/day-14.md 执行 Knowledge Base and Document Storage Foundation。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-14.md、docs/specs/rag.md、docs/development-plan.md Phase 3 和 docs/milestones.md。
- 只实现 Day 14 scope 内的内容。
- 今天只做知识库与文档 metadata/control-plane，不做文件上传、object storage、ingestion、chunking、embedding、pgvector retrieval、kb_search tool 或 memory。
- 所有新增能力必须有 domain model、storage model/repository、API/CLI、测试和文档更新。
- 完成后运行 Day 14 verification commands。
- 更新 docs/daily/day-14.md 的 checklist。
- 更新 specs 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
