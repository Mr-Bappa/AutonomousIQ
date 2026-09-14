# AutonomousIQ — Architecture Decision & Risk Log

*Running log started at the Architecture/Standards stage. Append new entries here rather than re-opening the Business Case each time; batch any Business Case revision until this stage is complete.*

**Status: Business Case (v0.3), PRD (v0.2), and this Architecture Decision Log are all in sync as of this session. Ready for the Standards stage (coding conventions, repo scaffolding).**

---

## Locked decisions (this session)

### D-1: Formula engine for Trackers
**Decision:** Formula.js (MIT-licensed function library) + a custom-built recalculation layer, rather than HyperFormula (GPLv3 / commercial license).
**Why:** Avoids ongoing license cost/obligations of HyperFormula for a closed-source commercial product.
**What this commits us to building:** dependency-graph construction across tracker cells, topological recalculation on cell change, circular-reference detection, and cell-reference parsing (A1-style or equivalent). None of this is supplied by Formula.js — it only provides the underlying spreadsheet functions (SUM, VLOOKUP-equivalents, etc.).
**Follow-up needed — resolved:** the recalc-engine design will be folded into the **Data stage**, alongside the already-open `tracker_cells` schema question, rather than spun out as a separate spec. The two are being decided together since the row/cell storage shape directly constrains how the dependency graph is built and traversed.
**Risk contribution:** adds real engineering scope vs. the off-the-shelf alternative — noted below in the risk section.

### D-2: `resource_workspace_access.access_level` granularity
**Decision:** Four-tier enum — `view` / `comment` / `edit` / `admin` — rather than the simpler two-tier `view`/`edit`.
**Per-resource-type meaning to formalize at Standards stage:**
- Dataset / Document: `comment` = annotate without modifying; `admin` = can re-grant access to others at that resource+workspace pairing
- Tracker: `comment` = cell-level comment threads, separate from value/formula editing; `admin` = same re-grant meaning as above
**Naming resolved:** the access_level value is renamed to **`resource_admin`** (enum becomes `view` / `comment` / `edit` / `resource_admin`). The tenant-level **Admin** role is unchanged. This applies everywhere in code, schema, and docs going forward — any earlier mention of an `admin` access_level in this log or the PRD should be read as `resource_admin`.

### D-3: DB connector list & security model
**Decision:** Connector list expanded to Postgres, MySQL, SQL Server, and Snowflake (broader than the originally proposed Postgres+MySQL-only Phase 0 scope).
**Security model (unchanged from proposal):** IP allowlisting as default (client adds our static egress IP to their DB firewall), SSH tunnel as fallback for clients who can't allowlist. Credentials in GCP Secret Manager per PRD NFR-2 regardless of connector type.
**Risk contribution:** SQL Server and Snowflake each bring distinct auth models (Snowflake typically key-pair or OAuth, not simple user/pass) and separate schema-introspection logic — more surface than a Postgres/MySQL-only list.

---

## Locked decisions — Frontend (Round 1)

### D-4: Frontend framework
**Decision:** React + TypeScript.
**Why:** Broadest ecosystem fit for the component-heavy surface (approvals inbox, Tracker grid, ticketing board, chart viewer); TS mirrors the type-safety discipline already set on the backend via mypy.

### D-5: State management
**Decision:** React Query (server state) + Zustand (local/UI state), not Redux Toolkit.
**Why:** The app is dominated by async server state (approval queues, job statuses, live query results) which React Query handles natively; Redux Toolkit would add boilerplate for a smaller amount of actual local state.

### D-6: Tracker grid UI
**Decision:** AG Grid Community (MIT) as the rendering/interaction layer, wired to our own recalc engine (D-1/D-13).
**Why:** Production-grade virtualization and cell-editing for free under MIT; we still own all formula/recalc logic ourselves — AG Grid never becomes a paid spreadsheet-formula dependency.

---

## Locked decisions — Tracker/Data specifics (Round 2)

### D-7: tracker_cells storage shape
**Decision:** Sparse per-cell rows table: `tracker_id, row_idx, col_idx, raw_value, formula, computed_value`.
**Why:** Matches how spreadsheet backends are typically modeled; lets the recalc engine (D-1) target only changed cells instead of rewriting dense row blobs; indexes cleanly at scale.

### D-8: FR-17 default behavior (re-approval on logic change)
**Decision:** Default to **forward-only** when not explicitly configured per dataset.
**Why:** Quietly reprocessing historical data without explicit opt-in cuts against the product's core approval-gate trust story; forward-only is the safer, less-surprising default. Full reprocess remains available as an explicit per-dataset choice.

### D-9: Workspace-level roles
**Decision:** Not adding workspace-level roles in Phase 0.
**Why:** The 3 tenant-level roles (Admin/Developer/Viewer) plus the now-4-tier `resource_workspace_access.access_level` (view/comment/edit/resource_admin, see D-2) already cover workspace-scoped granularity without a second role system layered on top.

---

## Locked decisions — Platform/Infra (Round 3)

### D-10: Model-agnostic planner abstraction
**Decision:** Build a thin `LLMProvider`-style adapter interface now, with a single provider implemented behind it for Phase 0.
**Why:** Cheap insurance — a new provider later becomes a new adapter, not a planner rewrite — without over-building full multi-provider routing/fallback logic that Phase 0 doesn't need yet.

### D-11: Postgres read-replica trigger point
**Decision:** Deferred to post-launch measurement, same posture as the numeric SLA targets already deferred under NFR-7.
**Why:** No production traffic data exists yet to size a sensible trigger threshold against.

### D-12: Cache invalidation beyond dataset_version-TTL
**Decision:** Event-based invalidation layered on top of the existing TTL rule — invalidate on the actual write-path events that change data (transformation job completion, tracker cell recalculation), not just TTL expiry.
**Why:** Pure TTL alone permits stale reads for up to the TTL window immediately after a known change, undercutting the "reproducible, authoritative number" trust story.

---

## Locked decisions — Connector auth & business mechanics (Round 4)

### D-13: SQL Server connector auth
**Decision:** Native SQL auth (username/password) only for Phase 0 — no Windows Auth, no Azure AD.
**Why:** Portable across any client's SQL Server setup without coupling to their identity provider; Azure AD support can follow later for enterprise-tier Azure-hosted clients specifically.

### D-14: Snowflake connector auth
**Decision:** Key-pair auth as the sole method for Phase 0.
**Why:** Snowflake's own recommended approach for programmatic/service access; avoids MFA prompts breaking automated connections; more secure than a stored username/password.

### D-15: Workspace count limit enforcement
**Decision:** Hard cap per tier with an upgrade prompt, not soft-cap + overage billing.
**Why:** Simpler to build for Phase 0; overage-billing infrastructure is scope Phase 0 (proving the workflow with 1–3 design partners) doesn't need yet.

### D-16: Sample-size reduction formula
**Decision:** Fixed rule for Phase 0 — `min(10% of rows, 50,000 rows)` — not the originally-envisioned adaptive-per-data-type formula.
**Why:** The adaptive version needs real usage data to tune sensibly, which is exactly what Phase 0 is meant to generate. Revisit with real data before Phase 1.

---

## Running risk log (compounding scope — now reconciled)

| Date/Stage | Item | Compounds with | Status |
|---|---|---|---|
| PRD stage | Documents, Trackers w/ formulas, live DB connectors, tenant-request intake pulled into Phase 0 | Original lean Phase 0 framing | Reflected in Business Case v0.2 |
| Architecture stage | Custom-built formula recalc engine (D-1) instead of off-the-shelf HyperFormula | PRD-stage Tracker addition | Reflected in Business Case v0.3 |
| Architecture stage | Connector list broadened to 4 DBs incl. SQL Server/Snowflake (D-3) | PRD-stage DB connector addition | Reflected in Business Case v0.3 |
| Architecture stage | Frontend stack now fully specified (React/TS, AG Grid, custom recalc UI wiring) | All of the above | Reflected in Business Case v0.3 |
| Architecture stage | Model-agnostic planner adapter, event-based cache invalidation, sparse tracker_cells model | Above | Internal engineering decisions, not separately cost-material — no addendum needed |

**No further scope pulled forward is anticipated before implementation begins.** Remaining open items (real-time Tracker collaboration, is_approver scoping, tenant-request status-lookup mechanism, numeric SLA targets) are explicitly deferred past Phase 0 by design — not expected sources of further pre-build scope growth.

---

## Locked decisions — Data stage (Round 5)

### D-17: `is_approver` scoping
**Decision:** Resource-scoped, not global-per-user. An `access_grants` row with `resource_type='is_approver'` carries `resource_id = workspace_id`, exactly like every other grant type.
**Why:** FR-4 already requires Developers to grant only within resources their team has access to; a global `is_approver` would have been the one grant type that broke that model. Resolving it as resource-scoped keeps `effective_access(user)` (FR-6) uniform across all six resource_types with no special case.

### D-18: Tracker cell dependency storage
**Decision:** `tracker_cells.depends_on` (JSONB) stores the parsed dependency list, recomputed by the recalc engine's formula parser whenever `formula` changes — not re-derived by parsing on every recalculation pass.
**Why:** Recalculation needs to answer "what depends on this changed cell?" on every edit; walking that reverse-dependency frontier against a GIN-indexed JSONB column is far cheaper than re-parsing every formula in the tracker on each edit. Trade-off accepted: the write path (cell edit) must keep `depends_on` in sync with `formula`, enforced by routing all formula writes through the recalc engine's `on_cell_edit`, never a raw column update.

### D-19: `tracker_cells.tenant_id` denormalization
**Decision:** `tracker_cells` carries `tenant_id` directly, in addition to the FK chain through `trackers.tenant_id`.
**Why:** Defense-in-depth for tenant isolation (matches the existing `TenantIsolationError` posture in the exception hierarchy) and avoids a join on the highest-cardinality, hottest-path table in the schema.

### D-20: Recalc error-state persistence
**Decision:** `tracker_cells.error_state` (`none` / `circular_reference` / `invalid_formula` / `upstream_error`) is persisted immediately when detected, not left as a runtime-only condition.
**Why:** The UI needs to show a stuck/broken cell without re-running recalculation on every read; persisting also lets the same information survive across API instances/workers since detection and display can happen in different processes.

**Open item resolved as part of this stage:** the Formula.js/Python cross-runtime execution gap (implicit in D-1, not previously surfaced) is resolved as a small Node.js sidecar (`services/formula-sidecar/`, stateless, pure function evaluation only) called from `libs/recalc_engine/js_bridge.py`. All graph/ordering/cycle-detection logic stays in Python. Sidecar build itself is out of scope for the Data stage — flagged for Infrastructure/Deployment.

---

## Open items carried into Standards

- Exact `LLMProvider` adapter interface shape (D-10) and the `resource_admin` naming convention (D-2) should be reflected explicitly once the Standards doc (coding conventions) is written.
- All other prior open items (D-1 through D-16) are resolved and reflected in PRD v0.2 and Business Case v0.3.
