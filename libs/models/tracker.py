"""Tracker / TrackerCell models.

TrackerCell is the sparse per-cell store locked at D-7, extended this
Data stage with:
  - D-18: `depends_on` -- derived dependency list, recomputed whenever
    `formula` changes (not recomputed on every recalc pass).
  - D-19: `tenant_id` denormalized directly onto the row for isolation
    defense-in-depth and index efficiency, even though it's reachable via
    tracker_id -> trackers.tenant_id.
  - D-20: `error_state` -- persisted so a circular-reference (or other
    recalc failure) is visible to the UI without re-running recalc.
"""

import enum
import uuid

from sqlalchemy import (
    JSON,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Tracker(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tenant-global, live-editable spreadsheet-like resource.

    `schema_definition` holds column definitions (name, type, formula
    column flag); actual cell data lives in TrackerCell, not here --
    "current row data or pointer to row-store" per the PRD is resolved to
    always be a pointer (the FK relationship to tracker_cells), never
    inline data, to avoid a second source of truth.
    """

    __tablename__ = "trackers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_definition: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    cells: Mapped[list["TrackerCell"]] = relationship(back_populates="tracker")


class CellErrorState(str, enum.Enum):
    """Persisted error classification for a cell (D-20)."""

    none = "none"
    circular_reference = "circular_reference"
    invalid_formula = "invalid_formula"
    upstream_error = "upstream_error"  # depends on a cell that itself errors


class TrackerCell(Base, TimestampMixin):
    """Sparse per-cell row. Composite primary key (tracker_id, row_idx,
    col_idx) rather than a synthetic id -- cell identity *is* its
    coordinate within a tracker, and this lets upserts on cell edit use a
    natural ON CONFLICT target."""

    __tablename__ = "tracker_cells"

    tracker_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trackers.id", ondelete="CASCADE"), primary_key=True
    )
    row_idx: Mapped[int] = mapped_column(Integer, primary_key=True)
    col_idx: Mapped[int] = mapped_column(Integer, primary_key=True)

    # D-19: denormalized for isolation defense-in-depth + index efficiency.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    # D-18: derived dependency list, e.g. [{"row_idx": 2, "col_idx": 1}, ...].
    # Recomputed by the recalc engine's formula parser whenever `formula`
    # is written; never hand-edited by API callers.
    depends_on: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # D-20: persisted so the UI can render an error badge without
    # re-running recalculation.
    error_state: Mapped[CellErrorState] = mapped_column(
        Enum(CellErrorState, name="cell_error_state"),
        nullable=False,
        default=CellErrorState.none,
    )

    tracker: Mapped["Tracker"] = relationship(back_populates="cells")

    __table_args__ = (
        # Reverse-lookup index: "which cells depend on (tracker, r, c)?"
        # is the hot path during recalc dispatch (topological propagation
        # walks forward from a changed cell to its dependents). Without
        # this, that walk is a full-table JSONB scan per changed cell.
        {
            "comment": (
                "See migration for the GIN index on depends_on supporting "
                "reverse dependency lookups."
            )
        },
    )
