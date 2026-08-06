"""Create eval run persistence table.

Revision ID: 0014_create_eval_runs
Revises: 0013_pgvector_embeddings
Create Date: 2026-08-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_create_eval_runs"
down_revision = "0013_pgvector_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("suite_type", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False),
        sa.Column("passed_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.String(length=4000), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_eval_runs_name"), "eval_runs", ["name"], unique=False)
    op.create_index(op.f("ix_eval_runs_passed"), "eval_runs", ["passed"], unique=False)
    op.create_index(op.f("ix_eval_runs_status"), "eval_runs", ["status"], unique=False)
    op.create_index(op.f("ix_eval_runs_suite_type"), "eval_runs", ["suite_type"], unique=False)
    op.create_index(op.f("ix_eval_runs_trace_id"), "eval_runs", ["trace_id"], unique=False)
    op.create_index(
        "ix_eval_runs_suite_type_created_at",
        "eval_runs",
        ["suite_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_eval_runs_status_created_at",
        "eval_runs",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_eval_runs_status_created_at", table_name="eval_runs")
    op.drop_index("ix_eval_runs_suite_type_created_at", table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_trace_id"), table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_suite_type"), table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_status"), table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_passed"), table_name="eval_runs")
    op.drop_index(op.f("ix_eval_runs_name"), table_name="eval_runs")
    op.drop_table("eval_runs")
