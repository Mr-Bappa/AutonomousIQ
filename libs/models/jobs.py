"""transformation_jobs, tickets, tenant_requests."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from libs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TransformationJobStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    rejected = "rejected"


class ExecutionTarget(str, enum.Enum):
    cloud = "cloud"
    local = "local"


class TransformationJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """FR-11/FR-14/FR-15: AI-proposed + human-approved transformation,
    memoized by (code_version, dataset_version)."""

    __tablename__ = "transformation_jobs"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_version: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_version: Mapped[int] = mapped_column(nullable=False)
    sample_used: Mapped[bool] = mapped_column(nullable=False, default=True)
    status: Mapped[TransformationJobStatus] = mapped_column(
        Enum(TransformationJobStatus, name="transformation_job_status"), nullable=False
    )
    approval_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # FR-15 memoization key: (code_version, dataset_version) uniqueness
    # enforced via composite unique index in the migration.
    cache_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    execution_target: Mapped[ExecutionTarget] = mapped_column(
        Enum(ExecutionTarget, name="execution_target"), nullable=False
    )


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Ticket(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Single merged entity replacing the earlier separate
    tickets/tracker_entries split."""

    __tablename__ = "tickets"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status"), nullable=False, default=TicketStatus.open
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Session F+ addition: the model as locked at the Data stage had no
    # human-facing text fields at all -- title/description are the
    # minimum needed for a usable Ticket CRUD surface.
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled ticket")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class TenantRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class TenantRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """FR-1: public 'Request Access' form submission. No tenant_id FK --
    a request precedes tenant existence by definition."""

    __tablename__ = "tenant_requests"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_info: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TenantRequestStatus] = mapped_column(
        Enum(TenantRequestStatus, name="tenant_request_status"),
        nullable=False,
        default=TenantRequestStatus.pending,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Explicit field (distinct from updated_at) since PRD calls it out by
    # name and it has specific meaning: "when was this reviewed", not
    # "when was this row last touched for any reason".
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
