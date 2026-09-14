"""In-memory dependency graph for a single Tracker's recalculation pass.

Design (Data stage, folded together with D-7 per the Architecture log):

  1. On a cell edit, the API/worker writes raw_value/formula, calls
     `formula_parser.parse_dependencies` on the new formula, and persists
     the result to `depends_on` (D-18) in the same transaction as the
     edit -- so depends_on is always in sync with formula, never stale.
  2. To recalculate, we don't rebuild the *whole* tracker's graph from
     every row every time. We load only:
       a. the changed cell(s), and
       b. every cell whose `depends_on` (JSONB, GIN-indexed, see
          migration 0001) contains one of the changed coordinates --
          the reverse-dependency frontier.
     ...then repeat outward until the frontier stops growing. This keeps
     recalc proportional to the affected subgraph, not tracker size.
  3. Topologically sort the affected subgraph (Kahn's algorithm) and
     recompute in that order, invoking the Formula.js sidecar
     (js_bridge.py) per cell with its already-resolved argument values.
  4. Any cell involved in a cycle gets `error_state =
     circular_reference` and a null `computed_value` (D-20), persisted
     immediately rather than left to a subsequent read -- everything
     downstream of a cycle gets `error_state = upstream_error`.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

CellCoord = tuple[int, int]  # (row_idx, col_idx)


@dataclass
class CellNode:
    coord: CellCoord
    formula: str | None
    depends_on: list[CellCoord] = field(default_factory=list)


@dataclass
class RecalcPlan:
    """Result of planning a recalculation: the order to evaluate cells
    in, plus any cells that can't be evaluated due to a cycle."""

    order: list[CellCoord]
    circular: set[CellCoord]
    upstream_of_circular: set[CellCoord]


class DependencyGraph:
    """Builds and topologically sorts the subgraph affected by a set of
    changed cells, using each node's persisted `depends_on`."""

    def __init__(self, nodes: dict[CellCoord, CellNode]) -> None:
        self._nodes = nodes
        # dependents[x] = set of cells whose formula references x --
        # i.e. the reverse edges, which is the direction we propagate in.
        self._dependents: dict[CellCoord, set[CellCoord]] = defaultdict(set)
        for coord, node in nodes.items():
            for dep in node.depends_on:
                self._dependents[dep].add(coord)

    @classmethod
    def from_cell_rows(cls, rows: list[dict]) -> "DependencyGraph":
        """Build from ORM/dict rows already loaded for the affected
        subgraph (see module docstring step 2)."""
        nodes = {
            (row["row_idx"], row["col_idx"]): CellNode(
                coord=(row["row_idx"], row["col_idx"]),
                formula=row.get("formula"),
                depends_on=[
                    (d["row_idx"], d["col_idx"]) for d in (row.get("depends_on") or [])
                ],
            )
            for row in rows
        }
        return cls(nodes)

    def affected_frontier(self, changed: set[CellCoord]) -> set[CellCoord]:
        """All cells reachable by walking forward through `dependents`
        from the changed set -- i.e. everything that needs recomputing
        as a result of this edit."""
        seen: set[CellCoord] = set()
        queue: deque[CellCoord] = deque(changed)
        while queue:
            coord = queue.popleft()
            if coord in seen:
                continue
            seen.add(coord)
            for dependent in self._dependents.get(coord, ()):
                if dependent not in seen:
                    queue.append(dependent)
        return seen

    def plan(self, changed: set[CellCoord]) -> RecalcPlan:
        """Kahn's-algorithm topological sort over the affected subgraph,
        detecting cycles and computing which cells are downstream of a
        cycle (they can't be safely evaluated either, per D-20's
        `upstream_error` classification)."""
        affected = self.affected_frontier(changed)

        in_degree: dict[CellCoord, int] = {coord: 0 for coord in affected}
        for coord in affected:
            node = self._nodes.get(coord)
            if node is None:
                continue
            for dep in node.depends_on:
                if dep in affected:
                    in_degree[coord] += 1

        queue: deque[CellCoord] = deque(
            coord for coord, deg in in_degree.items() if deg == 0
        )
        order: list[CellCoord] = []
        while queue:
            coord = queue.popleft()
            order.append(coord)
            for dependent in self._dependents.get(coord, ()):
                if dependent not in in_degree:
                    continue
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Anything left with in_degree > 0 never got dequeued -- it's
        # part of a cycle, or depends (transitively) on one.
        remaining = {coord for coord, deg in in_degree.items() if deg > 0}
        circular = self._cells_actually_in_a_cycle(remaining)
        upstream_of_circular = remaining - circular

        return RecalcPlan(order=order, circular=circular, upstream_of_circular=upstream_of_circular)

    def _cells_actually_in_a_cycle(self, candidates: set[CellCoord]) -> set[CellCoord]:
        """Among cells that failed to topologically sort, distinguish
        cells that are *on* a cycle from cells that merely depend on one
        (both fail Kahn's algorithm identically, but D-20 wants them
        classified differently: circular_reference vs upstream_error)."""
        in_cycle: set[CellCoord] = set()
        for start in candidates:
            # DFS looking for a path back to `start` using only edges
            # within `candidates` (edges outside are already resolved/
            # acyclic and irrelevant to cycle membership).
            path: set[CellCoord] = set()
            frontier = [start]
            found_cycle = False
            while frontier:
                coord = frontier.pop()
                if coord in path:
                    continue
                path.add(coord)
                node = self._nodes.get(coord)
                if node is None:
                    continue
                for dep in node.depends_on:
                    if dep == start:
                        found_cycle = True
                    if dep in candidates and dep not in path:
                        frontier.append(dep)
            if found_cycle:
                in_cycle.add(start)
        return in_cycle
