"""Workspace / Dataset / Document models (FR-19 workspace creation,
ingestion + profiling sources feeding Datasets and Documents)."""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DatasetVisibility(str, enum.Enum):
    tenant_wide = "tenant_wide"
    restricted = "restricted"


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Created by Admin or Developer only (FR-19); Viewer/User never
    self-initiates a workspace."""

    __tablename__ = "workspaces"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    self_serve: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Dataset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A raw or processed dataset. Versioned; lineage_pointer references
    the transformation_job (or prior dataset version) that produced this
    version, per FR-14/FR-16 lineage tracking."""

    __tablename__ = "datasets"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    visibility: Mapped[DatasetVisibility] = mapped_column(
        Enum(DatasetVisibility, name="dataset_visibility"), nullable=False
    )
    is_processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lineage_pointer: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An uploaded document (not a tabular Dataset, not a Tracker)."""

    __tablename__ = "documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    storage_pointer: Mapped[str] = mapped_column(String(1024), nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False)
