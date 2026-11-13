"""Give memory and eval records explicit workspace ownership."""

import sqlalchemy as sa
from alembic import op

revision = "0016_scope_memory_evals"
down_revision = "0015_scope_knowledge_bases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("memory_items", "eval_runs"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("workspace_id", sa.String(36), nullable=True))
            batch.create_foreign_key(
                op.f(f"fk_{table}_workspace_id_workspaces"),
                "workspaces",
                ["workspace_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index(op.f(f"ix_{table}_workspace_id"), ["workspace_id"])


def downgrade() -> None:
    for table in ("eval_runs", "memory_items"):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(op.f(f"ix_{table}_workspace_id"))
            batch.drop_constraint(op.f(f"fk_{table}_workspace_id_workspaces"), type_="foreignkey")
            batch.drop_column("workspace_id")
