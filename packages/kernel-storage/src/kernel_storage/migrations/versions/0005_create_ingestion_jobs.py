"""Create ingestion job table.

Revision ID: 0005_create_ingestion_jobs
Revises: 0004_create_kb_tables
Create Date: 2026-07-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_create_ingestion_jobs"
down_revision = "0004_create_kb_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("parser_name", sa.String(length=255), nullable=True),
        sa.Column("parsed_text_uri", sa.String(length=2000), nullable=True),
        sa.Column("parsed_text_checksum", sa.String(length=255), nullable=True),
        sa.Column("parsed_text_size_bytes", sa.Integer(), nullable=True),
        sa.Column("content_char_count", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=4000), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_ingestion_jobs_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_jobs")),
    )
    op.create_index(op.f("ix_ingestion_jobs_document_id"), "ingestion_jobs", ["document_id"])
    op.create_index(
        "ix_ingestion_jobs_document_id_created_at",
        "ingestion_jobs",
        ["document_id", "created_at"],
    )
    op.create_index(op.f("ix_ingestion_jobs_status"), "ingestion_jobs", ["status"])
    op.create_index(
        "ix_ingestion_jobs_status_created_at",
        "ingestion_jobs",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_status_created_at", table_name="ingestion_jobs")
    op.drop_index(op.f("ix_ingestion_jobs_status"), table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_document_id_created_at", table_name="ingestion_jobs")
    op.drop_index(op.f("ix_ingestion_jobs_document_id"), table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
