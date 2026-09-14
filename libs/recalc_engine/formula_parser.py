"""A1-style cell reference parsing for Tracker formulas.

Formula.js itself only supplies spreadsheet *functions* (SUM, IF, etc.) --
per D-1, parsing which cells a formula references is engineering scope we
own, and its output (a list of {row_idx, col_idx} coordinates) is what
gets written into TrackerCell.depends_on (D-18) whenever a formula
changes.

Reference syntax for Phase 0: `A1`-style two-letter-max columns
(A..Z, AA..ZZ) and 1-based row numbers, e.g. `=SUM(A1:A10)` or
`=B2*C2`. Ranges expand to every cell in the rectangle at parse time --
Phase 0 does not need a compact "range dependency" representation, only
straightforward cell-level dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CELL_RE = re.compile(r"\$?([A-Za-z]{1,2})\$?(\d+)")
_RANGE_RE = re.compile(
    r"\$?([A-Za-z]{1,2})\$?(\d+)\s*:\s*\$?([A-Za-z]{1,2})\$?(\d+)"
)


@dataclass(frozen=True)
class CellRef:
    row_idx: int
    col_idx: int

    def to_dict(self) -> dict[str, int]:
        return {"row_idx": self.row_idx, "col_idx": self.col_idx}


def _col_letters_to_idx(letters: str) -> int:
    """A -> 0, B -> 1, ..., Z -> 25, AA -> 26, ... (0-based, matches
    tracker_cells.col_idx)."""
    idx = 0
    for ch in letters.upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def parse_dependencies(formula: str | None) -> list[CellRef]:
    """Extract every distinct cell a formula references.

    Ranges (A1:A10) are expanded to individual cells. Returns an empty
    list for a non-formula value (formula is None or doesn't start with
    '='), consistent with a plain literal cell having no dependencies.
    """
    if not formula or not formula.startswith("="):
        return []

    body = formula[1:]
    refs: set[tuple[int, int]] = set()

    # Expand ranges first, then strip them out so the plain-cell regex
    # doesn't double-count their endpoints.
    remaining = body
    for match in _RANGE_RE.finditer(body):
        c1, r1, c2, r2 = match.groups()
        col1, col2 = sorted((_col_letters_to_idx(c1), _col_letters_to_idx(c2)))
        row1, row2 = sorted((int(r1), int(r2)))
        for row in range(row1, row2 + 1):
            for col in range(col1, col2 + 1):
                refs.add((row, col))
        remaining = remaining.replace(match.group(0), " ")

    for match in _CELL_RE.finditer(remaining):
        col_letters, row_str = match.groups()
        refs.add((int(row_str), _col_letters_to_idx(col_letters)))

    return [CellRef(row_idx=r, col_idx=c) for r, c in sorted(refs)]
