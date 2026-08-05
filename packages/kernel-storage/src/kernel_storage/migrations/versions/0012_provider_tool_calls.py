"""Add provider-native tool call metadata.

Revision ID: 0012_provider_tool_calls
Revises: 0011_worker_leases
Create Date: 2026-08-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_provider_tool_calls"
down_revision = "0011_worker_leases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tool_calls", sa.Column("provider_name", sa.String(length=64), nullable=True))
    op.add_column(
        "tool_calls",
        sa.Column("provider_tool_call_id", sa.String(length=255), nullable=True),
    )
    op.add_column("tool_calls", sa.Column("raw_provider_payload", sa.JSON(), nullable=True))
    op.create_index(op.f("ix_tool_calls_provider_name"), "tool_calls", ["provider_name"])
    op.create_index(
        op.f("ix_tool_calls_provider_tool_call_id"),
        "tool_calls",
        ["provider_tool_call_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_calls_provider_tool_call_id"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_provider_name"), table_name="tool_calls")
    op.drop_column("tool_calls", "raw_provider_payload")
    op.drop_column("tool_calls", "provider_tool_call_id")
    op.drop_column("tool_calls", "provider_name")
