# Day 71: Production RAG/Storage Integration Tests

Goal:

Prove that the production-shaped RAG storage path works through API boundaries
when object storage is configured behind the generic `ObjectStore` contract.

Scope:

- Add integration coverage for S3/MinIO-compatible object storage through the
  knowledge base API.
- Exercise upload, ingest, chunk, index, retrieve, and citation behavior through
  one end-to-end API path.
- Keep default CI deterministic by using an injected fake S3-compatible client
  instead of live network services or cloud credentials.
- Update Beta milestone tracking.

Tasks:

- [x] Add Day 71 daily plan.
- [x] Add production RAG/storage integration tests.
- [x] Verify S3-backed document upload metadata.
- [x] Verify ingestion reads from S3 URI and writes parsed text artifacts to S3.
- [x] Verify chunking, indexing, retrieval, and citation behavior after S3-backed
  ingestion.
- [x] Update Beta milestone progress.

Acceptance:

- [x] A knowledge base document can be uploaded through the API using an
  S3-compatible object store.
- [x] The stored document metadata records an `s3://bucket/key` source URI and
  object key.
- [x] Ingestion can read source bytes back from object storage through the URI.
- [x] Parsed text artifacts are written back through the same object store.
- [x] Retrieval citations point to the S3-backed document source URI.
- [x] Tests require no live AWS, MinIO, or network credentials.

Verification:

- [x] `uv run pytest tests/integration/test_rag_storage_integration.py`
- [x] `uv run pytest tests/integration/test_api_knowledge_base.py tests/unit/test_local_object_store.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`
- [x] `git diff --check`

Notes:

- Day 71 intentionally keeps live MinIO/Postgres smoke testing outside default
  CI. That belongs in an opt-in production smoke profile once deployment
  credentials and services are available.
- This closes the immediate production RAG/storage confidence gap created by
  adding OpenAI embeddings, pgvector, and S3/MinIO backends in Day 68-70.
