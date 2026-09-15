"""Recalc engine orchestrator: the entry point the API/worker call on a
cell edit.

Owns the write-path contract that keeps `depends_on` (D-18) and
`error_state` (D-20) always consistent with `formula`:

  1. on_cell_edit persists the new raw_value/formula and its freshly
     parsed depends_on in the same transaction.
  2. recalculate loads the affected subgraph, plans it (cycle detection
     included), evaluates non-circular cells in topological order via
     the Formula.js sidecar, and persists computed_value/error_state for
     every touched cell -- circular and upstream_error cells included,
     so nothing is left stale.

This module intentionally has no direct SQLAlchemy session handling --
it's called with a small repository-shaped interface so it stays
testable without a real database (see tests/libs/recalc_engine/).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from libs.recalc_engine import js_bridge
from libs.recalc_engine.dependency_graph import CellCoord, DependencyGraph
from libs.recalc_engine.formula_parser import parse_dependencies
from libs.recalc_engine.formula_resolver import FormulaSyntaxError, evaluate_formula


class CellRepository(Protocol):
    """Narrow interface the engine needs from persistence. Implemented
    against SQLAlchemy in apps/api and apps/worker; a fake in tests."""

    async def load_subgraph(
        self, tracker_id: str, changed: set[CellCoord]
    ) -> list[dict]:
        """Return every cell row needed to plan recalculation: the
        changed cells plus their full reverse-dependency closure (see
        DependencyGraph.affected_frontier)."""
        ...

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
    ) -> None: ...


@dataclass
class CellEdit:
    coord: CellCoord
    raw_value: str | None
    formula: str | None


async def on_cell_edit(repo: CellRepository, tracker_id: str, edit: CellEdit) -> None:
    """Persist an edit and its parsed dependencies, then trigger
    recalculation of everything downstream."""
    deps = parse_dependencies(edit.formula)
    await repo.save_cell(
        tracker_id,
        edit.coord,
        formula=edit.formula,
        raw_value=edit.raw_value,
        depends_on=[d.to_dict() for d in deps],
    )
    await recalculate(repo, tracker_id, changed={edit.coord})


async def recalculate(
    repo: CellRepository, tracker_id: str, changed: set[CellCoord]
) -> None:
    """Recompute every cell affected by `changed`, per the module
    docstring's write-path contract."""
    rows = await repo.load_subgraph(tracker_id, changed)
    graph = DependencyGraph.from_cell_rows(rows)
    plan = graph.plan(changed)

    rows_by_coord = {(r["row_idx"], r["col_idx"]): r for r in rows}

    for coord in plan.circular:
        await repo.save_cell(
            tracker_id, coord, computed_value=None, error_state="circular_reference"
        )
    for coord in plan.upstream_of_circular:
        await repo.save_cell(
            tracker_id, coord, computed_value=None, error_state="upstream_error"
        )

    for coord in plan.order:
        row = rows_by_coord.get(coord)
        if row is None:
            continue
        formula = row.get("formula")
        if not formula:
            # Literal value, nothing to evaluate -- computed_value mirrors
            # raw_value and error_state stays "none".
            continue
        try:
            # Layer-wise Development: the Data-stage stub is now real.
            # formula_resolver parses the formula into an AST and walks
            # it bottom-up, dispatching every function call (and every
            # arithmetic operator, translated to its Formula.js
            # equivalent) to the sidecar -- so nested calls like
            # `=SUM(A1:A5, MAX(B1:B5))` work, not just a single top-level
            # call.
            result = await evaluate_formula(formula, rows_by_coord)
            await repo.save_cell(
                tracker_id, coord, computed_value=str(result), error_state="none"
            )
        except (js_bridge.FormulaEvaluationError, FormulaSyntaxError):
            await repo.save_cell(
                tracker_id, coord, computed_value=None, error_state="invalid_formula"
            )
