"""Shared declarative base and mixins for all AutonomousIQ ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base shared by every AutonomousIQ ORM model."""


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key, matching the multi-tenant convention.

    UUIDs (not serial ints) are used tenant-wide so that resource ids are
    never guessable across tenants and can be generated client-side or in
    the worker without a round trip to get an id.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    """Adds created_at / updated_at, maintained server-side."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
