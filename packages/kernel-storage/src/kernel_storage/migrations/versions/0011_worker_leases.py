"""Create worker leases.

Revision ID: 0011_worker_leases
Revises: 0010_scope_agents_runs
Create Date: 2026-08-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_worker_leases"
down_revision = "0010_scope_agents_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_leases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("worker_id", sa.String(length=255), nullable=False),
        sa.Column("lease_token", sa.String(length=255), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_worker_leases_run_id_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_worker_leases")),
        sa.UniqueConstraint("lease_token", name=op.f("uq_worker_leases_lease_token")),
    )
    op.create_index(op.f("ix_worker_leases_run_id"), "worker_leases", ["run_id"])
    op.create_index(op.f("ix_worker_leases_worker_id"), "worker_leases", ["worker_id"])
    op.create_index("ix_worker_leases_run_released", "worker_leases", ["run_id", "released_at"])
    op.create_index("ix_worker_leases_expires_at", "worker_leases", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_worker_leases_expires_at", table_name="worker_leases")
    op.drop_index("ix_worker_leases_run_released", table_name="worker_leases")
    op.drop_index(op.f("ix_worker_leases_worker_id"), table_name="worker_leases")
    op.drop_index(op.f("ix_worker_leases_run_id"), table_name="worker_leases")
    op.drop_table("worker_leases")
