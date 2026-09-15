"""SQLAlchemy-backed implementation of engine.py's `CellRepository`
Protocol -- the piece that was deliberately left out at the Data stage
("no direct SQLAlchemy session handling" in engine.py's docstring, so it
stays testable without a real database).

**Phase 0 simplification, flagged rather than silently done:**
`load_subgraph` loads *every* cell in the tracker, not just the changed
cell plus its reverse-dependency frontier as the module docstring in
dependency_graph.py describes. Computing that frontier server-side would
mean either (a) a recursive CTE walking the JSONB `depends_on` column
backwards, or (b) pulling the whole tracker into Python and filtering
there -- and given Trackers are grids a human is actively editing (not
bulk data), "whole tracker" is realistically small for Phase 0. Real
frontier-limited loading is deferred until a Tracker size shows up where
it matters; DependencyGraph.plan() still only *acts* on the affected
subgraph, so behavior is correct today, just not yet optimized for scale.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from libs.models.tracker import CellErrorState, TrackerCell
from libs.recalc_engine.dependency_graph import CellCoord


class SQLAlchemyCellRepository:
    """One instance per request/job, wrapping a single AsyncSession so
    on_cell_edit's write + recalculate's writes share one transaction."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def load_subgraph(
        self, tracker_id: str, changed: set[CellCoord]
    ) -> list[dict]:
        result = await self._session.scalars(
            select(TrackerCell).where(TrackerCell.tracker_id == uuid.UUID(tracker_id))
        )
        return [
            {
                "row_idx": cell.row_idx,
                "col_idx": cell.col_idx,
                "formula": cell.formula,
                "raw_value": cell.raw_value,
                "computed_value": cell.computed_value,
                "depends_on": cell.depends_on,
            }
            for cell in result
        ]

    async def save_cell(
        self,
        tracker_id: str,
        coord: CellCoord,
        *,
        formula: str | None = None,
        raw_value: str | None = None,
        depends_on: list[dict] | None = None,
        computed_value: str | None = None,
        error_state: str = "none",
    ) -> None:
        row_idx, col_idx = coord

        # Upsert on the natural (tracker_id, row_idx, col_idx) primary
        # key (D-7's rationale) -- a cell edit is "create if this
        # coordinate has never been written, else update in place".
        # Only the fields the caller actually passed get updated, so a
        # recalculate()-only call (formula/raw_value omitted) doesn't
        # clobber them back to NULL.
        values: dict[str, object] = {
            "tracker_id": uuid.UUID(tracker_id),
            "row_idx": row_idx,
            "col_idx": col_idx,
            "tenant_id": self._tenant_id,
            "computed_value": computed_value,
            "error_state": CellErrorState(error_state),
        }
        update_values: dict[str, object] = {
            "computed_value": computed_value,
            "error_state": CellErrorState(error_state),
        }
        if formula is not None or raw_value is not None or depends_on is not None:
            values["formula"] = formula
            values["raw_value"] = raw_value
            values["depends_on"] = depends_on
            update_values["formula"] = formula
            update_values["raw_value"] = raw_value
            update_values["depends_on"] = depends_on

        stmt = pg_insert(TrackerCell).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["tracker_id", "row_idx", "col_idx"],
            set_=update_values,
        )
        await self._session.execute(stmt)
