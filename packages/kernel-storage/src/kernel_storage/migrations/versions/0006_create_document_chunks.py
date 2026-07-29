"""Create document chunk table.

Revision ID: 0006_create_document_chunks
Revises: 0005_create_ingestion_jobs
Create Date: 2026-07-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_create_document_chunks"
down_revision = "0005_create_ingestion_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(length=12000), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("token_count_estimate", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=255), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_document_chunks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
    )
    op.create_index(op.f("ix_document_chunks_checksum"), "document_chunks", ["checksum"])
    op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"])
    op.create_index(
        "ix_document_chunks_document_id_index",
        "document_chunks",
        ["document_id", "index"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_document_id_index", table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_checksum"), table_name="document_chunks")
    op.drop_table("document_chunks")
