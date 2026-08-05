"""Add workspace scope to agents and runs.

Revision ID: 0010_scope_agents_runs
Revises: 0009_identity_tables
Create Date: 2026-08-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_scope_agents_runs"
down_revision = "0009_identity_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("workspace_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        op.f("fk_agents_workspace_id_workspaces"),
        "agents",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_agents_workspace_id"), "agents", ["workspace_id"])

    op.add_column("runs", sa.Column("workspace_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        op.f("fk_runs_workspace_id_workspaces"),
        "runs",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_runs_workspace_id"), "runs", ["workspace_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_runs_workspace_id"), table_name="runs")
    op.drop_constraint(op.f("fk_runs_workspace_id_workspaces"), "runs", type_="foreignkey")
    op.drop_column("runs", "workspace_id")

    op.drop_index(op.f("ix_agents_workspace_id"), table_name="agents")
    op.drop_constraint(op.f("fk_agents_workspace_id_workspaces"), "agents", type_="foreignkey")
    op.drop_column("agents", "workspace_id")
