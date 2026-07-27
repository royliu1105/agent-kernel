"""Create execution lifecycle tables.

Revision ID: 0001_create_execution_tables
Revises:
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_create_execution_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("prompt_id", sa.String(length=36), nullable=True),
        sa.Column("default_model_policy_id", sa.String(length=36), nullable=True),
        sa.Column("memory_policy", sa.JSON(), nullable=False),
        sa.Column("tool_policy", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agents")),
    )

    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=4000), nullable=True),
        sa.Column("input_tokens_total", sa.Integer(), nullable=False),
        sa.Column("output_tokens_total", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_total", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name=op.f("fk_runs_agent_id_agents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
    )
    op.create_index(op.f("ix_runs_agent_id"), "runs", ["agent_id"], unique=False)
    op.create_index(op.f("ix_runs_trace_id"), "runs", ["trace_id"], unique=False)

    op.create_table(
        "run_steps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("span_id", sa.String(length=128), nullable=True),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=4000), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_run_steps_run_id_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_steps")),
    )
    op.create_index(op.f("ix_run_steps_run_id"), "run_steps", ["run_id"], unique=False)
    op.create_index("ix_run_steps_run_id_index", "run_steps", ["run_id", "index"], unique=False)
    op.create_index(op.f("ix_run_steps_trace_id"), "run_steps", ["trace_id"], unique=False)

    op.create_table(
        "run_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_run_events_run_id_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_events")),
    )
    op.create_index(op.f("ix_run_events_run_id"), "run_events", ["run_id"], unique=False)
    op.create_index(
        "ix_run_events_run_id_sequence",
        "run_events",
        ["run_id", "sequence"],
        unique=True,
    )
    op.create_index(op.f("ix_run_events_trace_id"), "run_events", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_run_events_trace_id"), table_name="run_events")
    op.drop_index("ix_run_events_run_id_sequence", table_name="run_events")
    op.drop_index(op.f("ix_run_events_run_id"), table_name="run_events")
    op.drop_table("run_events")

    op.drop_index(op.f("ix_run_steps_trace_id"), table_name="run_steps")
    op.drop_index("ix_run_steps_run_id_index", table_name="run_steps")
    op.drop_index(op.f("ix_run_steps_run_id"), table_name="run_steps")
    op.drop_table("run_steps")

    op.drop_index(op.f("ix_runs_trace_id"), table_name="runs")
    op.drop_index(op.f("ix_runs_agent_id"), table_name="runs")
    op.drop_table("runs")

    op.drop_table("agents")
