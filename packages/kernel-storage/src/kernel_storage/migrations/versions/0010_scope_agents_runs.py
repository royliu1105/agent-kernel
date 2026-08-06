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
    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_agents_workspace_id_workspaces"),
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(op.f("ix_agents_workspace_id"), ["workspace_id"])

    with op.batch_alter_table("runs") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_runs_workspace_id_workspaces"),
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(op.f("ix_runs_workspace_id"), ["workspace_id"])


def downgrade() -> None:
    with op.batch_alter_table("runs") as batch_op:
        batch_op.drop_index(op.f("ix_runs_workspace_id"))
        batch_op.drop_constraint(op.f("fk_runs_workspace_id_workspaces"), type_="foreignkey")
        batch_op.drop_column("workspace_id")

    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_index(op.f("ix_agents_workspace_id"))
        batch_op.drop_constraint(op.f("fk_agents_workspace_id_workspaces"), type_="foreignkey")
        batch_op.drop_column("workspace_id")
