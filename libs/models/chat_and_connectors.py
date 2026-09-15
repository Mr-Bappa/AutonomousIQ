"""Connector configs (ingestion sources) and chat messages (chat-planner
transcript). Both are Session F+ additions -- not present at the
original Data stage -- built simple/demo-level per this session's brief
rather than fully productionized.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from libs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConnectorType(str, enum.Enum):
    postgres = "postgres"
    mysql = "mysql"
    sqlserver = "sqlserver"
    snowflake = "snowflake"


class ConnectorConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A saved live-DB connector (D-3/D-13/D-14: Postgres/MySQL/SQL
    Server/Snowflake). `config` holds connection parameters.

    **Security flag:** STANDARDS.md/PRD NFR-2 calls for credentials in
    GCP Secret Manager. This demo stores `config` as a plain JSONB
    column -- explicitly NOT production-safe, matching this session's
    "keep it simple, demo-level" instruction. `libs/gcp/secrets.py` has
    the real Secret Manager client wired and ready; swapping
    `ConnectorConfig.config` to hold a secret *reference* instead of raw
    credentials is the follow-up, not done here.
    """

    __tablename__ = "connector_configs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connector_type: Mapped[ConnectorType] = mapped_column(
        Enum(ConnectorType, name="connector_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class ChatRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class ChatMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One turn in a chat-planner conversation (PRD's "hybrid chat +
    editable code/output cell interaction model" -- this is the plain
    transcript half; the editable-cell half is a frontend concern not
    built in this pass)."""

    __tablename__ = "chat_messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole, name="chat_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Which tool(s) the planner invoked to produce this message, if any
    # (sql_query_tool/tracker_query_tool/doc_search_tool/chart_tool) --
    # kept as JSONB for the demo rather than a normalized join table.
    tool_calls: Mapped[list | None] = mapped_column(JSONB, nullable=True)
