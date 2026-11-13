"""Enforce one unreleased execution lease per run."""

import sqlalchemy as sa
from alembic import op

revision = "0017_unique_active_lease"
down_revision = "0016_scope_memory_evals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Conflicting legacy leases require operator review, not silent ownership reassignment.
    op.create_index(
        "uq_worker_leases_unreleased_run",
        "worker_leases",
        ["run_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
        sqlite_where=sa.text("released_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_worker_leases_unreleased_run", table_name="worker_leases")
