/**
 * Formula.js sidecar (Architecture Decision Log D-1, resolved as a
 * dedicated service at the Data stage — see D-20's note in the log).
 *
 * Purpose: our backend is Python/FastAPI (STANDARDS.md), but the
 * spreadsheet function library we locked (Formula.js) is JS-only. Rather
 * than reimplementing SUM/IF/VLOOKUP-equivalents/etc. natively in Python,
 * this sidecar is a small, stateless, horizontally-scalable process that
 * evaluates ONE function call per request and returns the result.
 *
 * It intentionally knows nothing about Trackers, cells, tenants, or
 * formula text -- libs/recalc_engine/js_bridge.py (Python side) resolves
 * a formula down to (function_name, args) using already-fetched cell
 * values *before* calling here. That separation keeps all graph/ordering/
 * cycle-detection/multi-tenant logic in Python, and keeps this service
 * a pure, cacheable, trivially-replicable function evaluator.
 *
 * Contract (must match js_bridge.py exactly):
 *   POST /evaluate
 *   { "function": "SUM", "args": [1, 2, 3] }
 *   -> 200 { "result": 6 }
 *   -> 200 { "error": "..." }   (known Formula.js function, bad args/semantics)
 *   -> 404 { "error": "..." }   (unknown/unsupported function name)
 */

const express = require("express");
const formulajs = require("@formulajs/formulajs");

const app = express();
app.use(express.json({ limit: "1mb" }));

// Phase 0 supported function surface. Deliberately an allowlist, not
// "any key on the formulajs export object" -- Formula.js ships several
// hundred functions (financial, engineering, statistical, ...) and PRD
// L1+L2 formula support only needs a focused set. Extending this list
// later is a one-line change, not a re-architecture.
const SUPPORTED_FUNCTIONS = new Set([
  // L1: basic arithmetic / single-value helpers
  "SUM",
  "SUBTRACT",
  "MULTIPLY",
  "DIVIDE",
  "ABS",
  "ROUND",
  "ROUNDUP",
  "ROUNDDOWN",
  "MIN",
  "MAX",
  // L2: aggregation, lookup, and conditional logic
  "AVERAGE",
  "COUNT",
  "COUNTA",
  "MEDIAN",
  "IF",
  "AND",
  "OR",
  "NOT",
  "VLOOKUP",
  "CONCATENATE",
]);

app.post("/evaluate", (req, res) => {
  const { function: functionName, args } = req.body ?? {};

  if (typeof functionName !== "string" || !Array.isArray(args)) {
    return res.status(400).json({
      error: "Request must be { function: string, args: array }.",
    });
  }

  const upperName = functionName.toUpperCase();

  if (!SUPPORTED_FUNCTIONS.has(upperName)) {
    return res.status(404).json({
      error: `Unsupported function for Phase 0: ${functionName}`,
    });
  }

  const impl = formulajs[upperName];
  if (typeof impl !== "function") {
    // Allowlisted above but not actually exported by this formulajs
    // version -- a config/version mismatch, not a caller error.
    return res.status(500).json({
      error: `${upperName} is allowlisted but not available in this formulajs build.`,
    });
  }

  try {
    const result = impl(...args);

    // Formula.js reports its own errors as sentinel Error objects
    // (e.g. #DIV/0!, #VALUE!) rather than throwing, for spreadsheet-like
    // semantics -- surface those as evaluation errors, not silent results.
    if (result instanceof Error) {
      return res.status(200).json({ error: result.message });
    }

    return res.status(200).json({ result });
  } catch (err) {
    return res.status(200).json({ error: err.message ?? String(err) });
  }
});

app.get("/healthz", (_req, res) => {
  res.status(200).json({ status: "ok", supported_functions: SUPPORTED_FUNCTIONS.size });
});

const port = process.env.PORT || 8801;
app.listen(port, () => {
  console.log(`formula-sidecar listening on :${port}`);
});
