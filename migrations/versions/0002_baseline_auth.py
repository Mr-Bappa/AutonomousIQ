"""Baseline auth: password_hash on users, oauth_identities table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(255),
            nullable=True,
        ),
    )

    oauth_provider = postgresql.ENUM(
        "google",
        "facebook",
        "linkedin",
        name="oauth_provider",
        create_type=False,
    )

    oauth_provider.create(
        op.get_bind(),
        checkfirst=True,
    )

    op.create_table(
        "oauth_identities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "provider",
            oauth_provider,
            nullable=False,
        ),
        sa.Column(
            "provider_user_id",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_oauth_identities_user_id",
        "oauth_identities",
        ["user_id"],
    )

    op.create_unique_constraint(
        "uq_oauth_identities_provider_provider_user_id",
        "oauth_identities",
        ["provider", "provider_user_id"],
    )


def downgrade() -> None:
    op.drop_table("oauth_identities")
    op.execute("DROP TYPE IF EXISTS oauth_provider")
    op.drop_column("users", "password_hash")