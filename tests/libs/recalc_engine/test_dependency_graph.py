"""Tests for DependencyGraph: topological ordering, cycle detection, and
the circular_reference / upstream_error split (D-20)."""

from libs.recalc_engine.dependency_graph import DependencyGraph


def _rows(*cells):
    """cells: list of (row_idx, col_idx, formula, [deps]) tuples."""
    return [
        {"row_idx": r, "col_idx": c, "formula": f, "depends_on": deps}
        for r, c, f, deps in cells
    ]


def test_simple_chain_topological_order():
    # C2 = A1 + B1-ish chain: (0,0) <- (1,0) <- (2,0)
    rows = _rows(
        (0, 0, None, []),
        (1, 0, "=A1", [{"row_idx": 0, "col_idx": 0}]),
        (2, 0, "=A2", [{"row_idx": 1, "col_idx": 0}]),
    )
    graph = DependencyGraph.from_cell_rows(rows)
    plan = graph.plan(changed={(0, 0)})

    assert plan.circular == set()
    assert plan.upstream_of_circular == set()
    # (0,0) must come before (1,0), which must come before (2,0).
    assert plan.order.index((0, 0)) < plan.order.index((1, 0))
    assert plan.order.index((1, 0)) < plan.order.index((2, 0))


def test_direct_cycle_detected():
    # (0,0) depends on (0,1) and vice versa.
    rows = _rows(
        (0, 0, "=B1", [{"row_idx": 0, "col_idx": 1}]),
        (0, 1, "=A1", [{"row_idx": 0, "col_idx": 0}]),
    )
    graph = DependencyGraph.from_cell_rows(rows)
    plan = graph.plan(changed={(0, 0)})

    assert plan.circular == {(0, 0), (0, 1)}
    assert plan.upstream_of_circular == set()
    assert plan.order == []


def test_cell_downstream_of_cycle_marked_upstream_error_not_circular():
    # (0,0) <-> (0,1) cycle; (0,2) depends on (0,1) but isn't itself
    # part of the cycle.
    rows = _rows(
        (0, 0, "=B1", [{"row_idx": 0, "col_idx": 1}]),
        (0, 1, "=A1", [{"row_idx": 0, "col_idx": 0}]),
        (0, 2, "=B1", [{"row_idx": 0, "col_idx": 1}]),
    )
    graph = DependencyGraph.from_cell_rows(rows)
    plan = graph.plan(changed={(0, 0)})

    assert plan.circular == {(0, 0), (0, 1)}
    assert plan.upstream_of_circular == {(0, 2)}
    assert (0, 2) not in plan.order


def test_unaffected_cells_not_included_in_plan():
    # (5,5) has no relation to the changed cell's dependents at all.
    rows = _rows(
        (0, 0, None, []),
        (1, 0, "=A1", [{"row_idx": 0, "col_idx": 0}]),
        (5, 5, "=Z9", [{"row_idx": 8, "col_idx": 25}]),
    )
    graph = DependencyGraph.from_cell_rows(rows)
    plan = graph.plan(changed={(0, 0)})

    assert (5, 5) not in plan.order
    assert (5, 5) not in plan.circular
    assert (5, 5) not in plan.upstream_of_circular
