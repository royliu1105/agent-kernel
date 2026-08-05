# Day 70: S3/MinIO Object Storage Backend

## Goal

Add a production-shaped S3-compatible object storage backend while keeping the
local filesystem object store as the default developer and CI path.

## Scope

- Add object store backend configuration.
- Add a small `ObjectStore` protocol for ingestion/chunking/API wiring.
- Add `S3ObjectStore` with S3-compatible URI handling and injectable client for
  no-network tests.
- Add a factory that selects local or S3 storage from environment variables.
- Keep `LocalObjectStore` behavior unchanged.
- Update storage/RAG docs and milestones.

## Tasks

- [x] Add object store backend configuration constants.
- [x] Add `ObjectStore` protocol.
- [x] Implement S3-compatible object store.
- [x] Implement backend factory.
- [x] Update ingestion, chunking, and API typing to depend on the protocol.
- [x] Add local and S3 object store unit tests.
- [x] Update docs and milestones.

## Acceptance

- [x] Local object storage remains the default.
- [x] `AGENT_KERNEL_OBJECT_STORE_BACKEND=s3` creates an S3-compatible store.
- [x] S3 writes include deterministic object keys, content type, and checksum
  metadata.
- [x] S3 reads support stored `s3://bucket/key` URIs.
- [x] Unsafe keys and bucket mismatches fail clearly.
- [x] Tests do not require network access or real S3 credentials.

## Verification

- [x] `uv run pytest tests/unit/test_local_object_store.py`
- [x] `uv run pytest tests/unit/test_chunker.py tests/integration/test_api_knowledge_base.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`

## Notes

- Day 70 does not require live MinIO/S3 in default CI.
- Day 70 does not add multipart uploads, presigned URLs, lifecycle policies, or
  object encryption management.
- Day 70 expects production deployments to provide credentials through standard
  AWS-compatible environment variables or platform secrets.
