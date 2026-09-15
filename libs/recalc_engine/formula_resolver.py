"""Formula -> sidecar-call resolution.

This is the piece flagged as a `NotImplementedError` stub at the Data
stage (engine.py's old `_resolve_call`) and tracked there as real
Layer-wise Development scope: translating a formula's text into actual
Formula.js calls, with every cell reference substituted for its
already-computed value.

Scope for Phase 0 (L1+L2 per the PRD's Trackers line item):
  - Function calls: `=SUM(A1:A10)`, `=IF(B2>10, "big", "small")`,
    including nesting: `=SUM(A1:A5, MAX(B1:B5))`.
  - Basic infix arithmetic: `=B2*C2`, `=A1+A2-A3`. These aren't function
    calls at all, but Formula.js still supplies the underlying
    behavior (ADD/SUBTRACT/MULTIPLY/DIVIDE), so we translate operators to
    those function names rather than reimplementing arithmetic locally --
    keeping "what a formula evaluates to" fully owned by the sidecar,
    never partially computed in Python.
  - Cell refs (`A1`) and ranges (`A1:A10`) resolve to the *other* cell's
    `computed_value` (falling back to `raw_value` for a literal, non-
    formula cell) via the `rows_by_coord` map the caller already loaded
    for the recalc pass -- this module never queries the database itself.

Explicitly out of scope / not attempted here: operator precedence beyond
left-to-right, unary minus, string concatenation via `&`, and anything
Formula.js doesn't itself support. Malformed input raises
FormulaSyntaxError, which engine.py maps to the same `invalid_formula`
error_state as a sidecar-reported FormulaEvaluationError -- callers don't
need to distinguish "we couldn't parse it" from "Formula.js rejected it".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Union

from libs.recalc_engine import js_bridge
from libs.recalc_engine.dependency_graph import CellCoord
from libs.recalc_engine.formula_parser import _col_letters_to_idx

_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<number>\d+\.\d+|\d+)
      | (?P<string>"[^"]*")
      | (?P<range>\$?[A-Za-z]{1,2}\$?\d+\s*:\s*\$?[A-Za-z]{1,2}\$?\d+)
      | (?P<cell>\$?[A-Za-z]{1,2}\$?\d+)
      | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
      | (?P<op>[+\-*/,()])
      | (?P<compare><=|>=|<>|<|>|=)
    )
    """,
    re.VERBOSE,
)

_ARITHMETIC_FUNCS = {"+": "SUM", "-": "SUBTRACT", "*": "MULTIPLY", "/": "DIVIDE"}


class FormulaSyntaxError(Exception):
    """Raised when a formula can't be tokenized/parsed at all -- distinct
    from FormulaEvaluationError (js_bridge), which means Formula.js itself
    rejected an otherwise well-formed call."""


# --- AST -------------------------------------------------------------


@dataclass
class Literal:
    value: object


@dataclass
class CellRef:
    coord: CellCoord


@dataclass
class Range:
    coords: list[CellCoord]


@dataclass
class FuncCall:
    name: str
    args: list["Node"]


@dataclass
class BinOp:
    op: str
    left: "Node"
    right: "Node"


Node = Union[Literal, CellRef, Range, FuncCall, BinOp]


# --- Tokenizer + recursive-descent parser -----------------------------


def _tokenize(body: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(body):
        match = _TOKEN_RE.match(body, pos)
        if not match or match.end() == pos:
            remainder = body[pos:].strip()
            if not remainder:
                break
            raise FormulaSyntaxError(f"Unrecognized token near: {remainder[:20]!r}")
        pos = match.end()
        kind = match.lastgroup
        text = match.group(kind)
        tokens.append((kind, text))
    return tokens


class _Parser:
    """Small recursive-descent parser: expr := term (('+'|'-') term)*,
    term := factor (('*'|'/') factor)*, factor := call | range | cell |
    literal | '(' expr ')'."""

    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self._tokens = tokens
        self._pos = 0

    def parse(self) -> Node:
        node = self._expr()
        if self._pos != len(self._tokens):
            raise FormulaSyntaxError("Unexpected trailing tokens in formula.")
        return node

    def _peek(self) -> tuple[str, str] | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _advance(self) -> tuple[str, str]:
        tok = self._peek()
        if tok is None:
            raise FormulaSyntaxError("Unexpected end of formula.")
        self._pos += 1
        return tok

    def _expr(self) -> Node:
        node = self._term()
        while (tok := self._peek()) and tok[1] in ("+", "-"):
            self._advance()
            node = BinOp(op=tok[1], left=node, right=self._term())
        return node

    def _term(self) -> Node:
        node = self._factor()
        while (tok := self._peek()) and tok[1] in ("*", "/"):
            self._advance()
            node = BinOp(op=tok[1], left=node, right=self._factor())
        return node

    def _factor(self) -> Node:
        kind, text = self._advance()

        if kind == "op" and text == "(":
            node = self._expr()
            self._expect_op(")")
            return node
        if kind == "number":
            return Literal(float(text) if "." in text else int(text))
        if kind == "string":
            return Literal(text[1:-1])
        if kind == "range":
            return Range(coords=_expand_range(text))
        if kind == "cell":
            return CellRef(coord=_cell_to_coord(text))
        if kind == "name":
            self._expect_op("(")
            args: list[Node] = []
            if not (self._peek() and self._peek()[1] == ")"):
                args.append(self._expr())
                while self._peek() and self._peek()[1] == ",":
                    self._advance()
                    args.append(self._expr())
            self._expect_op(")")
            return FuncCall(name=text.upper(), args=args)

        raise FormulaSyntaxError(f"Unexpected token: {text!r}")

    def _expect_op(self, expected: str) -> None:
        tok = self._peek()
        if not tok or tok[1] != expected:
            raise FormulaSyntaxError(f"Expected {expected!r}.")
        self._advance()


def _cell_to_coord(text: str) -> CellCoord:
    match = re.fullmatch(r"\$?([A-Za-z]{1,2})\$?(\d+)", text)
    assert match is not None  # guaranteed by the tokenizer's regex
    col_letters, row_str = match.groups()
    return (int(row_str), _col_letters_to_idx(col_letters))


def _expand_range(text: str) -> list[CellCoord]:
    match = re.fullmatch(
        r"\$?([A-Za-z]{1,2})\$?(\d+)\s*:\s*\$?([A-Za-z]{1,2})\$?(\d+)", text
    )
    assert match is not None
    c1, r1, c2, r2 = match.groups()
    col1, col2 = sorted((_col_letters_to_idx(c1), _col_letters_to_idx(c2)))
    row1, row2 = sorted((int(r1), int(r2)))
    return [(row, col) for row in range(row1, row2 + 1) for col in range(col1, col2 + 1)]


def parse_formula(formula: str) -> Node:
    """Parse a formula string (including its leading '=') into an AST."""
    if not formula or not formula.startswith("="):
        raise FormulaSyntaxError("Formula must start with '='.")
    return _Parser(_tokenize(formula[1:])).parse()


# --- Evaluation --------------------------------------------------------


def _coerce_cell_value(row: dict | None) -> object:
    """A referenced cell contributes its computed_value if it's itself a
    formula, else its raw_value -- and we try to coerce to a number since
    that's what almost every downstream function call expects."""
    if row is None:
        return None
    value = row.get("computed_value") if row.get("formula") else row.get("raw_value")
    if value is None:
        return None
    try:
        return float(value) if "." in str(value) else int(value)
    except (TypeError, ValueError):
        return value


async def _eval_node(node: Node, rows_by_coord: dict[CellCoord, dict]) -> object:
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, CellRef):
        return _coerce_cell_value(rows_by_coord.get(node.coord))
    if isinstance(node, Range):
        return [_coerce_cell_value(rows_by_coord.get(c)) for c in node.coords]
    if isinstance(node, BinOp):
        left = await _eval_node(node.left, rows_by_coord)
        right = await _eval_node(node.right, rows_by_coord)
        function_name = _ARITHMETIC_FUNCS[node.op]
        return await js_bridge.evaluate(function_name, [left, right])
    if isinstance(node, FuncCall):
        resolved_args: list[object] = []
        for arg in node.args:
            value = await _eval_node(arg, rows_by_coord)
            # A range argument (e.g. inside SUM(A1:A10)) contributes each
            # of its cells as a separate positional arg -- matching
            # Formula.js's variadic (...args) signatures (D-1's "SUM,
            # VLOOKUP-equivalents, etc." functions all work this way).
            if isinstance(arg, Range):
                resolved_args.extend(value)  # type: ignore[arg-type]
            else:
                resolved_args.append(value)
        return await js_bridge.evaluate(node.name, resolved_args)

    raise FormulaSyntaxError(f"Unhandled AST node: {node!r}")  # pragma: no cover


async def evaluate_formula(formula: str, rows_by_coord: dict[CellCoord, dict]) -> object:
    """Full formula -> value pipeline used by engine.py's recalculate
    loop: parse, then evaluate bottom-up, dispatching every function call
    (including each arithmetic operator) to the Formula.js sidecar.

    Raises FormulaSyntaxError for anything unparsable and lets
    js_bridge.FormulaEvaluationError propagate from a Formula.js-level
    rejection -- engine.py maps both to `error_state = invalid_formula`.
    """
    ast = parse_formula(formula)
    return await _eval_node(ast, rows_by_coord)
