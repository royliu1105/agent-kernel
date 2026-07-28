"""Create tool call persistence table.

Revision ID: 0002_create_tool_calls
Revises: 0001_create_execution_tables
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_create_tool_calls"
down_revision = "0001_create_execution_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("step_id", sa.String(length=36), nullable=True),
        sa.Column("tool_name", sa.String(length=255), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=64), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("span_id", sa.String(length=128), nullable=True),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=4000), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_tool_calls_run_id_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_calls")),
    )
    op.create_index(op.f("ix_tool_calls_approval_id"), "tool_calls", ["approval_id"], unique=False)
    op.create_index("ix_tool_calls_run_id_created_at", "tool_calls", ["run_id", "created_at"])
    op.create_index(op.f("ix_tool_calls_run_id"), "tool_calls", ["run_id"], unique=False)
    op.create_index(op.f("ix_tool_calls_span_id"), "tool_calls", ["span_id"], unique=False)
    op.create_index(op.f("ix_tool_calls_step_id"), "tool_calls", ["step_id"], unique=False)
    op.create_index(op.f("ix_tool_calls_tool_name"), "tool_calls", ["tool_name"], unique=False)
    op.create_index(op.f("ix_tool_calls_trace_id"), "tool_calls", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_calls_trace_id"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_tool_name"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_step_id"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_span_id"), table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_run_id"), table_name="tool_calls")
    op.drop_index("ix_tool_calls_run_id_created_at", table_name="tool_calls")
    op.drop_index(op.f("ix_tool_calls_approval_id"), table_name="tool_calls")
    op.drop_table("tool_calls")
