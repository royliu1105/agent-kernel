# Day 15: Document Upload and Local Object Store Foundation

## Goal

Add the first RAG data-plane path by uploading local files into a local object store and creating uploaded document metadata.

Day 15 should establish this path:

```text
local file -> upload API -> LocalObjectStore -> uploaded Document metadata
```

## Scope

Day 15 should cover:

- Phase 3 planning alignment.
- Local object store interface and filesystem implementation.
- Safe object key generation.
- File checksum and size calculation.
- Upload size limit.
- API multipart file upload endpoint.
- CLI file upload command.
- Document metadata creation with `uploaded` status.
- Unit tests for object store and CLI.
- Integration tests for upload API.
- RAG spec, storage architecture, and milestone updates.

Day 15 should not cover:

- Parsing uploaded files.
- Chunking.
- Embeddings.
- pgvector retrieval.
- `kb_search` tool.
- Ingestion worker.
- Document deduplication policy.
- Remote S3/MinIO backend.
- Document-level authorization.
- Memory implementation.

## Domain Terms

- Local object store: a filesystem-backed storage adapter that writes uploaded document bytes under a configured root directory.
- Object key: stable internal storage key used to find the uploaded bytes.
- Source URI: externalized document source reference, using `object://local/<object-key>` for local object storage.

## Tasks

- [x] Check current git status.
- [x] Read `docs/specs/rag.md`.
- [x] Read `docs/storage-architecture.md`.
- [x] Read existing API/CLI/repository patterns.
- [x] Create Day 15 daily plan.
- [x] Add local object store config.
- [x] Add local object store implementation.
- [x] Add object store exports.
- [x] Allow document repository to create uploaded documents.
- [x] Add multipart upload API endpoint.
- [x] Add CLI upload command.
- [x] Add object store unit tests.
- [x] Add CLI upload tests.
- [x] Add API upload integration tests.
- [x] Update RAG spec.
- [x] Update storage architecture docs.
- [x] Update milestones.
- [x] Run verification commands.

## Acceptance

- [x] Uploading a text/Markdown file writes bytes to the local object store.
- [x] Uploaded documents are persisted with `uploaded` status.
- [x] Uploaded documents include source URI, checksum, size, MIME type, and original filename metadata.
- [x] Missing knowledge bases return 404 without creating a document.
- [x] Oversized uploads return a clear error.
- [x] CLI can upload a file through the API.
- [x] Day 15 does not parse, chunk, embed, retrieve, or call tools.

## Verification

Run the available checks:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy .
```

Focused checks during implementation:

```bash
uv run pytest tests/unit/test_local_object_store.py tests/unit/test_cli_commands.py tests/integration/test_api_knowledge_base.py
```

## Notes

- Day 15 stores document bytes on local disk to keep development simple and production-shaped.
- S3/MinIO can be added later behind the same object store boundary.
- Full document content must not be persisted in document metadata or logs.

## Completion Notes

- Added `LocalObjectStore` with safe object key generation, checksum calculation, and size limits.
- Added document upload API and CLI command.
- Uploaded document metadata is persisted with `uploaded` status and object-store source URI.
- Remote object storage, parsing, chunking, embeddings, retrieval, and memory remain deferred.

Verification passed:

- `uv sync`
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy .`

## Start Prompt

Use this prompt to begin implementation:

```text
开始 Day 15：请按照 docs/daily/day-15.md 执行 Document Upload and Local Object Store Foundation。

要求：
- 先检查 git 状态，不要覆盖用户已有改动。
- 读取 docs/daily/day-15.md、docs/specs/rag.md、docs/storage-architecture.md 和 docs/milestones.md。
- 只实现 Day 15 scope 内的内容。
- 今天只做 local file upload -> LocalObjectStore -> uploaded document metadata。
- 不做 parser、chunker、embedding、pgvector retrieval、kb_search tool、ingestion worker 或 memory。
- 上传路径必须避免 path traversal。
- 不要把完整文档内容写入日志、events 或 metadata。
- 完成后运行 Day 15 verification commands。
- 更新 docs/daily/day-15.md 的 checklist。
- 更新 specs、storage docs 和 docs/milestones.md。
- 最后总结完成内容、验证结果、已知风险和下一步。
```
