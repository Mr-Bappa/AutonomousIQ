"""Layer-wise Development additions: demo RAG text on documents,
human-facing fields on tickets, connector_configs (ingestion), and
chat_messages (chat-planner transcript).

Same caveat as 0001/0002: hand-written, not run against a real Postgres
in this sandbox -- verify with `alembic upgrade head` before treating
this as confirmed-working.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- documents: demo RAG text -------------------------------------
    op.add_column("documents", sa.Column("name", sa.String(255), nullable=False, server_default="untitled"))
    op.add_column("documents", sa.Column("content_text", sa.Text(), nullable=True))

    # --- tickets: human-facing fields ----------------------------------
    op.add_column(
        "tickets",
        sa.Column("title", sa.String(255), nullable=False, server_default="Untitled ticket"),
    )
    op.add_column("tickets", sa.Column("description", sa.Text(), nullable=True))

    # --- connector_configs (ingestion) -----------------------------------
    connector_type = postgresql.ENUM(
        "postgres", "mysql", "sqlserver", "snowflake", name="connector_type", create_type=False
    )
    connector_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "connector_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("connector_type", connector_type, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_connector_configs_tenant_id", "connector_configs", ["tenant_id"])

    # --- chat_messages (chat-planner transcript) ----------------------------
    chat_role = postgresql.ENUM("user", "assistant", name="chat_role", create_type=False)
    chat_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", chat_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_chat_messages_tenant_id", "chat_messages", ["tenant_id"])
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.execute("DROP TYPE IF EXISTS chat_role")
    op.drop_table("connector_configs")
    op.execute("DROP TYPE IF EXISTS connector_type")
    op.drop_column("tickets", "description")
    op.drop_column("tickets", "title")
    op.drop_column("documents", "content_text")
    op.drop_column("documents", "name")
