"""Create knowledge base and document tables.

Revision ID: 0004_create_knowledge_base_tables
Revises: 0003_create_approvals
Create Date: 2026-07-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_create_knowledge_base_tables"
down_revision = "0003_create_approvals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_bases")),
    )
    op.create_index(op.f("ix_knowledge_bases_name"), "knowledge_bases", ["name"])
    op.create_index(op.f("ix_knowledge_bases_status"), "knowledge_bases", ["status"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("source_uri", sa.String(length=2000), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("checksum", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.String(length=4000), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            name=op.f("fk_documents_knowledge_base_id_knowledge_bases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_checksum"), "documents", ["checksum"])
    op.create_index(op.f("ix_documents_knowledge_base_id"), "documents", ["knowledge_base_id"])
    op.create_index(
        "ix_documents_knowledge_base_id_created_at",
        "documents",
        ["knowledge_base_id", "created_at"],
    )
    op.create_index(
        "ix_documents_knowledge_base_id_status",
        "documents",
        ["knowledge_base_id", "status"],
    )
    op.create_index(op.f("ix_documents_status"), "documents", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_status"), table_name="documents")
    op.drop_index("ix_documents_knowledge_base_id_status", table_name="documents")
    op.drop_index("ix_documents_knowledge_base_id_created_at", table_name="documents")
    op.drop_index(op.f("ix_documents_knowledge_base_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_checksum"), table_name="documents")
    op.drop_table("documents")
    op.drop_index(op.f("ix_knowledge_bases_status"), table_name="knowledge_bases")
    op.drop_index(op.f("ix_knowledge_bases_name"), table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
