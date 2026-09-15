"""Tests for formula_resolver: the formula -> sidecar-call pipeline that
replaced engine.py's old `_resolve_call` NotImplementedError stub.

These mock js_bridge.evaluate so the tests don't need a running sidecar
-- they check parsing/AST-walking correctness, not Formula.js itself.
"""

from __future__ import annotations

import pytest

from libs.recalc_engine import js_bridge
from libs.recalc_engine.formula_resolver import FormulaSyntaxError, evaluate_formula

# A1 -> row_idx=1, col_idx=0 (row_idx matches the formula's literal row
# number; see formula_parser tests) -- NOT zero-indexed from "A1".
_ROWS = {
    (1, 0): {"formula": None, "raw_value": "2"},  # A1
    (1, 1): {"formula": None, "raw_value": "3"},  # B1
    (2, 0): {"formula": None, "raw_value": "4"},  # A2
    (2, 1): {"formula": None, "raw_value": "5"},  # B2
}


@pytest.fixture(autouse=True)
def _fake_sidecar(monkeypatch):
    async def fake_evaluate(function_name: str, args: list):
        if function_name == "MULTIPLY":
            return args[0] * args[1]
        if function_name == "SUM":
            return sum(a for a in args if a is not None)
        if function_name == "MAX":
            return max(args)
        if function_name == "IF":
            return args[1] if args[0] else args[2]
        raise AssertionError(f"unstubbed function in test: {function_name}")

    monkeypatch.setattr(js_bridge, "evaluate", fake_evaluate)


@pytest.mark.asyncio
async def test_simple_arithmetic_translated_to_sidecar_call():
    assert await evaluate_formula("=A1*B1", _ROWS) == 6


@pytest.mark.asyncio
async def test_range_expands_into_function_args():
    # SUM(A1:B2) -> SUM(2, 3, 4, 5)
    assert await evaluate_formula("=SUM(A1:B2)", _ROWS) == 14


@pytest.mark.asyncio
async def test_nested_function_calls():
    # SUM(A1:A2, MAX(B1:B2)) -> SUM(2, 4, MAX(3, 5)) -> SUM(2, 4, 5)
    assert await evaluate_formula("=SUM(A1:A2, MAX(B1:B2))", _ROWS) == 11


@pytest.mark.asyncio
async def test_function_call_with_string_and_cell_args():
    assert await evaluate_formula('=IF(A1, "big", "small")', _ROWS) == "big"


@pytest.mark.asyncio
async def test_unparsable_formula_raises_syntax_error_not_a_crash():
    with pytest.raises(FormulaSyntaxError):
        await evaluate_formula("=SUM(A1", _ROWS)  # unbalanced parens


@pytest.mark.asyncio
async def test_missing_cell_reference_resolves_to_none():
    # A cell with no row loaded (e.g. genuinely blank) contributes None,
    # not a crash -- SUM filters Nones per the fake sidecar above, mirroring
    # Formula.js's own real behavior for blank cells.
    rows = {**_ROWS}
    assert await evaluate_formula("=SUM(A1:A3)", rows) in (6, 2, 6)  # A3 missing -> None
