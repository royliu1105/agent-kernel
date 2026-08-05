"""Add pgvector-native chunk embedding storage.

Revision ID: 0013_pgvector_embeddings
Revises: 0012_provider_tool_calls
Create Date: 2026-08-05
"""

from __future__ import annotations

from alembic import op

revision = "0013_pgvector_embeddings"
down_revision = "0012_provider_tool_calls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE chunk_embeddings ADD COLUMN IF NOT EXISTS vector_pg vector")
    op.execute(
        """
        UPDATE chunk_embeddings
        SET vector_pg = vector::text::vector
        WHERE vector_pg IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chunk_embeddings_vector_pg_cosine
        ON chunk_embeddings
        USING hnsw ((vector_pg::vector(1536)) vector_cosine_ops)
        WHERE dimensions = 1536
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS ix_chunk_embeddings_vector_pg_cosine")
    op.execute("ALTER TABLE chunk_embeddings DROP COLUMN IF EXISTS vector_pg")
