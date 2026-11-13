"""Add nullable knowledge ownership without claiming legacy data."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_scope_knowledge_bases"
down_revision = "0014_create_eval_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_bases") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.String(36), nullable=True))
        batch_op.create_foreign_key(
            op.f("fk_knowledge_bases_workspace_id_workspaces"),
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(op.f("ix_knowledge_bases_workspace_id"), ["workspace_id"])


def downgrade() -> None:
    with op.batch_alter_table("knowledge_bases") as batch_op:
        batch_op.drop_index(op.f("ix_knowledge_bases_workspace_id"))
        batch_op.drop_constraint(
            op.f("fk_knowledge_bases_workspace_id_workspaces"), type_="foreignkey"
        )
        batch_op.drop_column("workspace_id")
