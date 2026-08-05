# Day 69: pgvector-Native Vector Store

## Goal

Add a pgvector-native storage and retrieval path for chunk embeddings while
preserving SQLite-compatible JSON-vector behavior for local development and CI.

## Scope

- Add vector store mode configuration.
- Add a Postgres-only migration that installs `vector`, adds a pgvector column,
  backfills it from existing JSON vectors, and creates a cosine index.
- Teach `ChunkEmbeddingRepository` to write pgvector data when enabled.
- Teach similarity search to use pgvector distance ordering on Postgres.
- Keep JSON-vector similarity as the default fallback for SQLite and tests.
- Update RAG/storage docs and milestone progress.

## Tasks

- [x] Add vector store mode configuration.
- [x] Add pgvector Alembic migration.
- [x] Add pgvector literal validation helper.
- [x] Update embedding replacement to populate pgvector column.
- [x] Update similarity search to use pgvector when configured.
- [x] Add unit tests for config, fallback behavior, and pgvector SQL helpers.
- [x] Update docs and milestones.

## Acceptance

- [x] SQLite JSON-vector tests remain unchanged.
- [x] `auto` mode uses pgvector on PostgreSQL and JSON vectors elsewhere.
- [x] `json` mode always uses JSON-vector fallback.
- [x] `pgvector` mode requires PostgreSQL and fails clearly otherwise.
- [x] pgvector migration is no-op on SQLite and active on PostgreSQL.
- [x] pgvector query orders by cosine distance through `vector_pg <=> query`.

## Verification

- [x] `uv run pytest tests/unit/test_storage_config.py tests/unit/test_chunk_embedding_repository.py tests/unit/test_migrations.py`
- [x] `uv run pytest tests/unit/test_retrieval.py tests/unit/test_rag_evals.py tests/integration/test_api_knowledge_base.py`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`

## Notes

- Day 69 does not require live Postgres in default CI.
- Day 69 does not remove JSON-vector storage.
- Day 69 does not add hybrid retrieval, BM25, RRF, reranking, or query
  rewriting.
