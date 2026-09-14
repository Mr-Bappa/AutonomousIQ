"""Tests for A1-style cell reference parsing (D-18 depends_on source)."""

from libs.recalc_engine.formula_parser import CellRef, parse_dependencies


def test_no_formula_has_no_dependencies():
    assert parse_dependencies(None) == []
    assert parse_dependencies("42") == []  # literal value, not a formula


def test_single_cell_reference():
    assert parse_dependencies("=A1") == [CellRef(row_idx=1, col_idx=0)]


def test_multiple_cell_references():
    result = set(parse_dependencies("=B2*C2"))
    assert result == {CellRef(row_idx=2, col_idx=1), CellRef(row_idx=2, col_idx=2)}


def test_range_expands_to_every_cell():
    result = set(parse_dependencies("=SUM(A1:A3)"))
    assert result == {
        CellRef(row_idx=1, col_idx=0),
        CellRef(row_idx=2, col_idx=0),
        CellRef(row_idx=3, col_idx=0),
    }


def test_two_letter_column():
    # AA is column index 26 (0-based): A=1..Z=26 -> AA = 26*1 + 1 - 1 = 26
    assert parse_dependencies("=AA1") == [CellRef(row_idx=1, col_idx=26)]


def test_duplicate_references_deduplicated():
    assert parse_dependencies("=A1+A1") == [CellRef(row_idx=1, col_idx=0)]
