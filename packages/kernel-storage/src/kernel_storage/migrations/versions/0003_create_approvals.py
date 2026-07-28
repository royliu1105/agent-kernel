"""Create approval persistence table.

Revision ID: 0003_create_approvals
Revises: 0002_create_tool_calls
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_create_approvals"
down_revision = "0002_create_tool_calls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("tool_call_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=4000), nullable=False),
        sa.Column("requested_by", sa.String(length=36), nullable=True),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("decision_note", sa.String(length=4000), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_approvals_run_id_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tool_call_id"],
            ["tool_calls.id"],
            name=op.f("fk_approvals_tool_call_id_tool_calls"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approvals")),
    )
    op.create_index(op.f("ix_approvals_requested_by"), "approvals", ["requested_by"])
    op.create_index(op.f("ix_approvals_reviewed_by"), "approvals", ["reviewed_by"])
    op.create_index(op.f("ix_approvals_run_id"), "approvals", ["run_id"])
    op.create_index("ix_approvals_status_requested_at", "approvals", ["status", "requested_at"])
    op.create_index(op.f("ix_approvals_tool_call_id"), "approvals", ["tool_call_id"])
    op.create_index(op.f("ix_approvals_trace_id"), "approvals", ["trace_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_approvals_trace_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_tool_call_id"), table_name="approvals")
    op.drop_index("ix_approvals_status_requested_at", table_name="approvals")
    op.drop_index(op.f("ix_approvals_run_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_reviewed_by"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_requested_by"), table_name="approvals")
    op.drop_table("approvals")
