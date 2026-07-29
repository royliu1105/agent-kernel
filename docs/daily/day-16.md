# Day 16: Ingestion Job and Text Parser Foundation

## Goal

Add the first document ingestion control path: create an ingestion job, parse uploaded text/Markdown bytes, and persist the parsed text as an object-store artifact.

Day 16 should establish this path:

```text
uploaded Document -> ingestion job -> parser -> parsed text artifact -> parsed Document
```

## Scope

Day 16 should cover:

- Phase 3 planning alignment.
- `IngestionJob` domain model and status lifecycle.
- Ingestion job storage table and Alembic migration.
- Ingestion job repository operations.
- Text/Markdown parser abstraction and default parser.
- Ingestion service for synchronous manual ingestion.
- Object store support for parsed text artifacts.
- API endpoint to ingest a document.
- API endpoint to inspect ingestion jobs.
- CLI command to ingest a document.
- Unit tests for parser, object store, repository, and CLI.
- Integration tests for the ingest API.
- RAG spec and milestone updates.

Day 16 should not cover:

- Async ingestion worker.
- Chunking.
- Embeddings.
- pgvector retrieval.
- `kb_search` tool.
- Citation building.
- Parser support for PDF, DOCX, HTML, or binary files.
- Deduplication policy.
- Memory implementation.

## Domain Terms

- Ingestion job: durable record of a document ingestion attempt.
- Parsed text artifact: normalized text extracted from the uploaded source and stored in object storage.
- Parser: component that validates supported MIME types and converts source bytes to normalized text.

## Tasks

- [x] Check current git status.
- [x] Read `docs/specs/rag.md`.
- [x] Read existing storage/API/CLI/RAG object store patterns.
- [x] Create Day 16 daily plan.
- [x] Add `parsed` document status.
- [x] Add ingestion job core model and status.
- [x] Add storage record and migration.
- [x] Add repository operations.
- [x] Add text/Markdown parser.
- [x] Add ingestion service.
- [x] Add parsed artifact object-store write support.
- [x] Add ingest API endpoints.
- [x] Add ingest CLI command.
- [x] Add unit tests.
- [x] Add integration tests.
- [x] Update RAG spec.
- [x] Update milestones.
- [x] Run verification commands.

## Acceptance

- [x] An uploaded text/Markdown document can be ingested manually.
- [x] Ingestion creates a durable ingestion job.
- [x] Ingestion job status transitions are persisted.
- [x] Document status moves from `uploaded` to `parsing` to `parsed`.
- [x] Parsed text is stored as an object-store artifact.
- [x] Parsed text content is not stored in document metadata, logs, or run events.
- [x] Unsupported documents fail with a clear job error.
- [x] CLI can request document ingestion through the API.
- [x] Day 16 does not chunk, embed, retrieve, cite, or call tools.

## Verification

Run the available checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_ingestion_repository.py tests/unit/test_text_parser.py tests/unit/test_cli_commands.py tests/integration/test_api_knowledge_base.py
```

## Notes

- Day 16 uses synchronous ingestion to keep the behavior simple and testable.
- A future async worker can call the same ingestion service.
- Parsed text is an artifact, not relational metadata.

## Completion Notes

- Added durable ingestion jobs and parser foundation.
- Added manual ingest API and CLI.
- Added parsed text artifact storage.
- Async worker, chunking, embeddings, retrieval, citations, and memory remain deferred.

Verification passed:

- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 16：请按照 docs/daily/day-16.md 执行 Ingestion Job and Text Parser Foundation。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-16.md、docs/specs/rag.md、docs/storage-architecture.md 和 docs/milestones.md。
- 只实现 Day 16 scope 内的内容。
- 今天只做 uploaded Document -> ingestion job -> parser -> parsed text artifact -> parsed Document。
- 不做 async ingestion worker、chunker、embedding、pgvector retrieval、kb_search tool、citation builder 或 memory。
- 不要把完整 parsed text 写入 DB metadata、logs 或 run events。
- 完成后运行 Day 16 verification commands。
- 更新 docs/daily/day-16.md 的 checklist。
- 更新 specs 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
