"""Create memory item table.

Revision ID: 0008_create_memory_items
Revises: 0007_create_chunk_embeddings
Create Date: 2026-07-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_create_memory_items"
down_revision = "0007_create_chunk_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("source_run_id", sa.String(length=36), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memory_items")),
    )
    op.create_index(op.f("ix_memory_items_created_at"), "memory_items", ["created_at"])
    op.create_index(op.f("ix_memory_items_scope"), "memory_items", ["scope"])
    op.create_index(
        "ix_memory_items_scope_created_at",
        "memory_items",
        ["scope", "created_at"],
    )
    op.create_index(
        "ix_memory_items_scope_type_created_at",
        "memory_items",
        ["scope", "type", "created_at"],
    )
    op.create_index(op.f("ix_memory_items_source_run_id"), "memory_items", ["source_run_id"])
    op.create_index(op.f("ix_memory_items_type"), "memory_items", ["type"])


def downgrade() -> None:
    op.drop_index(op.f("ix_memory_items_type"), table_name="memory_items")
    op.drop_index(op.f("ix_memory_items_source_run_id"), table_name="memory_items")
    op.drop_index("ix_memory_items_scope_type_created_at", table_name="memory_items")
    op.drop_index("ix_memory_items_scope_created_at", table_name="memory_items")
    op.drop_index(op.f("ix_memory_items_scope"), table_name="memory_items")
    op.drop_index(op.f("ix_memory_items_created_at"), table_name="memory_items")
    op.drop_table("memory_items")
