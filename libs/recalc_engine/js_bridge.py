"""Client for the Formula.js sidecar.

Formula.js is a JS library; our backend is Python/FastAPI (per
STANDARDS.md). Rather than reimplementing every spreadsheet function
natively in Python, Phase 0 runs a small long-running Node.js process
(`services/formula-sidecar/`, not yet built -- out of scope for this
stage, flagged for the Infrastructure/Deployment stage) that exposes one
endpoint:

    POST /evaluate
    { "function": "SUM", "args": [1, 2, 3] }
    -> { "result": 6 }
    -> { "error": "..." }  (Formula.js threw, e.g. wrong arg count)

All dependency-graph construction, topological ordering, and cycle
detection stay in Python (dependency_graph.py) -- the sidecar is a pure
function evaluator called once per cell, in topological order, with
already-resolved argument values substituted in. It never sees the
tracker's formula text or cell coordinates, only literal values, which
also keeps it stateless and trivially horizontally scalable.

This is a thin async HTTP client stub; no retry/circuit-breaker policy
is decided yet -- that's an Infrastructure-stage concern, not Data-stage.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

_SIDECAR_URL = os.environ.get("FORMULA_SIDECAR_URL", "http://localhost:8801")


class FormulaEvaluationError(Exception):
    """Raised when the sidecar reports Formula.js itself failed to
    evaluate a function call (bad args, unsupported function, etc.) --
    distinct from a network/transport failure."""


async def evaluate(function_name: str, args: list[Any]) -> Any:
    """Evaluate a single Formula.js function call and return its result.

    Raises FormulaEvaluationError on a Formula.js-level failure; lets
    httpx transport errors (connection refused, timeout) propagate as-is
    since those are infrastructure failures, not formula-logic failures,
    and should be handled by the caller's retry/backoff policy once one
    exists.
    """
    async with httpx.AsyncClient(base_url=_SIDECAR_URL, timeout=5.0) as client:
        response = await client.post(
            "/evaluate", json={"function": function_name, "args": args}
        )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise FormulaEvaluationError(payload["error"])
        return payload["result"]
