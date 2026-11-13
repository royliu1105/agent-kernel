"""Persist trusted run initiators and per-response model usage."""

import sqlalchemy as sa
from alembic import op

revision = "0018_usage_attribution"
down_revision = "0017_unique_active_lease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runs") as batch:
        batch.add_column(sa.Column("principal_id", sa.String(36), nullable=True))
        batch.create_foreign_key(
            "fk_runs_principal_id", "principals", ["principal_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index("ix_runs_principal_id", ["principal_id"])
    op.create_table(
        "model_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id", sa.String(36), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_usage_run_id", "model_usage", ["run_id"])
    # Do not infer a historical provider/model or user from untrusted input JSON.
    op.execute(
        sa.text("""
        INSERT INTO model_usage (id, run_id, provider, model, input_tokens, output_tokens,
                                 estimated_cost, created_at)
        SELECT id, id, 'unknown', 'unknown', input_tokens_total, output_tokens_total,
               estimated_cost_total, created_at FROM runs
        WHERE input_tokens_total > 0 OR output_tokens_total > 0 OR estimated_cost_total > 0
    """)
    )


def downgrade() -> None:
    op.drop_table("model_usage")
    with op.batch_alter_table("runs") as batch:
        batch.drop_index("ix_runs_principal_id")
        batch.drop_constraint("fk_runs_principal_id", type_="foreignkey")
        batch.drop_column("principal_id")
