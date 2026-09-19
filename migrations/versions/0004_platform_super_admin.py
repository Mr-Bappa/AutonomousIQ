"""Add platform-level super admins.

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_super_admin", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_platform_users_email", "platform_users", ["email"], unique=True)
    op.execute("UPDATE tenant_requests SET reviewed_by = NULL WHERE reviewed_by IS NOT NULL")
    op.drop_constraint("tenant_requests_reviewed_by_fkey", "tenant_requests", type_="foreignkey")
    op.create_foreign_key("tenant_requests_reviewed_by_fkey", "tenant_requests", "platform_users", ["reviewed_by"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("tenant_requests_reviewed_by_fkey", "tenant_requests", type_="foreignkey")
    op.create_foreign_key("tenant_requests_reviewed_by_fkey", "tenant_requests", "users", ["reviewed_by"], ["id"], ondelete="SET NULL")
    op.drop_index("ix_platform_users_email", table_name="platform_users")
    op.drop_table("platform_users")
