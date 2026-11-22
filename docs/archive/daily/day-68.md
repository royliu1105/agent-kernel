# Day 68: OpenAI Embeddings Backend

## Goal

Add a real OpenAI embeddings provider behind the existing RAG embedding
interface while keeping deterministic mock embeddings as the default local and
CI path.

## Scope

- Add OpenAI embedding provider constants and API-key resolution.
- Implement `/v1/embeddings` request/response handling with injectable HTTP
  transport for tests.
- Normalize and validate embedding vectors before indexing or retrieval uses
  them.
- Add tests for request payloads, response parsing, missing API key, malformed
  responses, HTTP failures, and indexing integration.
- Update RAG docs, milestones, and daily index.

## Tasks

- [x] Add OpenAI embedding provider configuration constants.
- [x] Implement OpenAI embedding provider.
- [x] Add response validation and typed errors.
- [x] Export provider symbols from `kernel_rag`.
- [x] Add no-network unit tests with mock HTTP transport.
- [x] Add indexing integration coverage.
- [x] Update milestone progress.
- [x] Update RAG and release-facing docs.

## Acceptance

- [x] `OpenAIEmbeddingProvider.embed_texts()` posts to `/v1/embeddings`.
- [x] Empty input returns an empty vector list without network I/O.
- [x] Missing `OPENAI_API_KEY` fails clearly.
- [x] HTTP and malformed response failures raise typed indexing-safe errors.
- [x] `DocumentIndexingService` can persist vectors from the OpenAI provider.
- [x] Mock embeddings remain the default.

## Verification

- [x] `uv run pytest tests/unit/test_embeddings.py`
- [x] `uv run pytest tests/unit/test_embeddings.py tests/unit/test_retrieval.py tests/unit/test_rag_evals.py tests/integration/test_api_knowledge_base.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`

## Notes

- Day 68 does not make OpenAI embeddings the default.
- Day 68 does not add pgvector-native storage, hybrid retrieval, reranking, or
  async ingestion workers.
- Day 68 does not run live OpenAI calls in CI.
