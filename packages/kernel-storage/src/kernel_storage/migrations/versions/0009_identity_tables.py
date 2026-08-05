"""Create identity and workspace tables.

Revision ID: 0009_identity_tables
Revises: 0008_create_memory_items
Create Date: 2026-08-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_identity_tables"
down_revision = "0008_create_memory_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "principals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_principals")),
    )
    op.create_index(op.f("ix_principals_created_at"), "principals", ["created_at"])
    op.create_index(op.f("ix_principals_disabled"), "principals", ["disabled"])
    op.create_index(op.f("ix_principals_type"), "principals", ["type"])

    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
        sa.UniqueConstraint("slug", name=op.f("uq_workspaces_slug")),
    )
    op.create_index(op.f("ix_workspaces_created_at"), "workspaces", ["created_at"])
    op.create_index(op.f("ix_workspaces_slug"), "workspaces", ["slug"])
    op.create_index(op.f("ix_workspaces_status"), "workspaces", ["status"])

    op.create_table(
        "workspace_memberships",
        sa.Column("principal_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["principal_id"],
            ["principals.id"],
            name=op.f("fk_workspace_memberships_principal_id_principals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_workspace_memberships_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "principal_id",
            "workspace_id",
            name=op.f("pk_workspace_memberships"),
        ),
    )
    op.create_index(
        op.f("ix_workspace_memberships_created_at"),
        "workspace_memberships",
        ["created_at"],
    )
    op.create_index(op.f("ix_workspace_memberships_role"), "workspace_memberships", ["role"])
    op.create_index(
        "ix_workspace_memberships_workspace_id_role",
        "workspace_memberships",
        ["workspace_id", "role"],
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("principal_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=64), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["principal_id"],
            ["principals.id"],
            name=op.f("fk_api_keys_principal_id_principals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_api_keys_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
        sa.UniqueConstraint("key_hash", name=op.f("uq_api_keys_key_hash")),
    )
    op.create_index(op.f("ix_api_keys_created_at"), "api_keys", ["created_at"])
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"])
    op.create_index(op.f("ix_api_keys_key_prefix"), "api_keys", ["key_prefix"])
    op.create_index(op.f("ix_api_keys_principal_id"), "api_keys", ["principal_id"])
    op.create_index(
        "ix_api_keys_principal_id_status",
        "api_keys",
        ["principal_id", "status"],
    )
    op.create_index(op.f("ix_api_keys_status"), "api_keys", ["status"])
    op.create_index(op.f("ix_api_keys_workspace_id"), "api_keys", ["workspace_id"])
    op.create_index(
        "ix_api_keys_workspace_id_status",
        "api_keys",
        ["workspace_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_api_keys_workspace_id_status", table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_workspace_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_status"), table_name="api_keys")
    op.drop_index("ix_api_keys_principal_id_status", table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_principal_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key_prefix"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key_hash"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_created_at"), table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index(
        "ix_workspace_memberships_workspace_id_role",
        table_name="workspace_memberships",
    )
    op.drop_index(op.f("ix_workspace_memberships_role"), table_name="workspace_memberships")
    op.drop_index(op.f("ix_workspace_memberships_created_at"), table_name="workspace_memberships")
    op.drop_table("workspace_memberships")

    op.drop_index(op.f("ix_workspaces_status"), table_name="workspaces")
    op.drop_index(op.f("ix_workspaces_slug"), table_name="workspaces")
    op.drop_index(op.f("ix_workspaces_created_at"), table_name="workspaces")
    op.drop_table("workspaces")

    op.drop_index(op.f("ix_principals_type"), table_name="principals")
    op.drop_index(op.f("ix_principals_disabled"), table_name="principals")
    op.drop_index(op.f("ix_principals_created_at"), table_name="principals")
    op.drop_table("principals")
