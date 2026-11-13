"""Store private, versioned execution continuation state."""

import sqlalchemy as sa
from alembic import op

revision = "0019_execution_checkpoint"
down_revision = "0018_usage_attribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("execution_checkpoint", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("runs") as batch:
        batch.drop_column("execution_checkpoint")
