"""Create chunk embedding table.

Revision ID: 0007_create_chunk_embeddings
Revises: 0006_create_document_chunks
Create Date: 2026-07-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_create_chunk_embeddings"
down_revision = "0006_create_document_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chunk_embeddings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(length=255), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            name=op.f("fk_chunk_embeddings_chunk_id_document_chunks"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_chunk_embeddings_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunk_embeddings")),
    )
    op.create_index(op.f("ix_chunk_embeddings_checksum"), "chunk_embeddings", ["checksum"])
    op.create_index(op.f("ix_chunk_embeddings_chunk_id"), "chunk_embeddings", ["chunk_id"])
    op.create_index(
        "ix_chunk_embeddings_chunk_id_model",
        "chunk_embeddings",
        ["chunk_id", "model"],
        unique=True,
    )
    op.create_index(op.f("ix_chunk_embeddings_document_id"), "chunk_embeddings", ["document_id"])
    op.create_index(
        "ix_chunk_embeddings_document_id_model",
        "chunk_embeddings",
        ["document_id", "model"],
    )
    op.create_index(op.f("ix_chunk_embeddings_model"), "chunk_embeddings", ["model"])


def downgrade() -> None:
    op.drop_index(op.f("ix_chunk_embeddings_model"), table_name="chunk_embeddings")
    op.drop_index("ix_chunk_embeddings_document_id_model", table_name="chunk_embeddings")
    op.drop_index(op.f("ix_chunk_embeddings_document_id"), table_name="chunk_embeddings")
    op.drop_index("ix_chunk_embeddings_chunk_id_model", table_name="chunk_embeddings")
    op.drop_index(op.f("ix_chunk_embeddings_chunk_id"), table_name="chunk_embeddings")
    op.drop_index(op.f("ix_chunk_embeddings_checksum"), table_name="chunk_embeddings")
    op.drop_table("chunk_embeddings")
