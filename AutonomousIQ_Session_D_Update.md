# AutonomousIQ — Session D Update

Builds on `AutonomousIQ_Continuation_Context_v3.md`. Layer-wise Development, first pass.

## What got built this session

### 1. Formula.js sidecar (`services/formula-sidecar/`)
- **Stack:** Node 20 + Express + `@formulajs/formulajs`.
- **How it works:** one endpoint, `POST /evaluate { function, args } -> { result }` or `{ error }`. Stateless, no DB, no knowledge of Trackers/cells/tenants at all.
- **Idea:** keep the JS-only function library behind a thin, cacheable, horizontally-scalable service; all graph/ordering/cycle logic stays in Python (per D-1).
- **Scope decision made this session (not previously locked):** an explicit allowlist of ~20 functions for Phase 0's L1+L2 formula support (SUM, AVERAGE, IF, VLOOKUP, MIN/MAX, ROUND family, etc.) rather than exposing formulajs's full few-hundred-function surface. Extending the list later is a one-line change.
- Wired into `docker-compose.yml` with a healthcheck; `api` now depends on it and gets `FORMULA_SIDECAR_URL` pointed at it.
- **Not run** — no npm registry access in this sandbox (same constraint as `pip` all session). `services/formula-sidecar/test.js` has hand-verified-logic smoke cases; real `npm install && node test.js` still needed locally.

### 2. `_resolve_call` stub replaced with a real formula resolver
- **New file:** `libs/recalc_engine/formula_resolver.py` — tokenizer + recursive-descent parser + async AST evaluator.
- **How it works:** parses a formula (`=SUM(A1:A10)`, `=B2*C2`, `=SUM(A1:A5, MAX(B1:B5))`) into an AST, then walks it bottom-up. Cell refs/ranges resolve from the already-loaded `rows_by_coord` map (never a new DB query); every function call *and* every arithmetic operator (translated to ADD/SUBTRACT/MULTIPLY/DIVIDE) is dispatched to the sidecar — Python never computes a formula result itself, only orchestrates.
- **Where it sits:** `libs/recalc_engine/`, called from `engine.py`'s `recalculate()` loop, same place the old stub lived.
- **Connects to:** reads `js_bridge.evaluate`; reuses `formula_parser._col_letters_to_idx` for column math; raises `FormulaSyntaxError` (new) which `engine.py` now catches alongside `js_bridge.FormulaEvaluationError`, both mapping to `error_state = invalid_formula`.
- **Verified in-sandbox:** hand-run with a stubbed sidecar (arithmetic, ranges, nesting, syntax errors) — all passed. Added `tests/libs/recalc_engine/test_formula_resolver.py` for a real `pytest` run.
- **Still not solved:** operator precedence is left-to-right only (no `*` before `+`), no unary minus, no `&` string concat — flagged in the module docstring, not silently dropped.

### 3. React frontend scaffold (`apps/frontend/`)
- **Stack:** Vite + React 18 + TypeScript, React Router, React Query, Zustand — per STANDARDS.md Section 2, feature-folder layout.
- **What's real (fully wired, would work once `npm install` runs):**
  - `main.tsx` → `App.tsx` → `router.tsx` → `AppLayout.tsx` (nav rail + outlet), all connected.
  - `shared/api/client.ts`: fetch wrapper unwrapping the standard `{error:{code,message,details}}` envelope into a typed `ApiError`.
  - `shared/auth/AuthContext.tsx`: JWT in `sessionStorage` (not `localStorage` — flagged reasoning in the file), `login()` hits real `POST /v1/auth/login`.
  - `features/workspaces/`: React Query hook + page hitting real `GET /v1/workspaces` — the frontend's version of the Baseline stage's "real DB round trip" proof.
  - `features/auth/LoginPage.tsx`: real email+password form.
  - `shared/store/uiStore.ts`: Zustand, holding exactly one thing (nav collapse) — deliberately not pre-populated with state for unbuilt features.
- **What's stubbed on purpose:** `trackers/`, `approvals/`, `tickets/`, `ingestion/`, `chat-planner/` pages exist as folders with a "Not built yet" placeholder each, matching the Standards folder shape but with zero real logic — next session's actual Layer-wise Development work.
- **What's not wired up at all:** OAuth login buttons (backend supports Google/Facebook/LinkedIn; frontend has no redirect flow yet), AG Grid (not installed — no Tracker UI exists to need it yet), any design system beyond inline styles + `tokens.css` variables.
- **Not run** — no Node/npm in this sandbox; nothing here has been `npm install`'d, type-checked, or rendered. First thing to do locally: `cd apps/frontend && npm install && npm run dev` (or `docker compose up --build`, now that `frontend` is a compose service).

## Flags carried forward

1. Docker compose (previous version, pre-sidecar/frontend) was confirmed working locally. **Re-verify** `docker compose up --build` now that `formula-sidecar` and `frontend` services were added — they haven't been tested together.
2. Formula resolver's arithmetic precedence is naive (left-to-right, no PEMDAS) — fine for the simple cases tested, likely wrong for anything with mixed `+`/`*` in one expression without parens. Real scope for a follow-up pass if it matters for Phase 0's actual formula usage.
3. Frontend has no Tracker grid, no approvals inbox, no ticket UI, no ingestion panel, no chat-planner UI yet — all placeholders.
4. OAuth frontend flow (redirect + callback landing) not built — backend-only currently.

## Suggested next steps
- Tracker CRUD endpoint (wires the now-working recalc engine to a real API route) + a first real AG Grid slice in `features/trackers/`.
- Or: approvals inbox, since `ApprovalRequiredError` and the `pending_approval` envelope shape are already locked in Standards but nothing implements them yet.

---

## Session E — Tracker CRUD + AG Grid slice, CORS fix

### CORS fix
`apps/api/main.py` now has `CORSMiddleware`, allowlisting `CORS_ALLOWED_ORIGINS` (env var, defaults to `http://localhost:5173`) rather than `*` — Phase 0 has exactly one frontend origin, so an explicit allowlist costs nothing.

### Tracker CRUD (`apps/api/trackers.py`) — the recalc engine's first real caller
- `POST /v1/trackers`, `GET /v1/trackers`, `GET /v1/trackers/{id}` (tracker + all cells), `PUT /v1/trackers/{id}/cells` (single-cell edit).
- The `PUT` route calls `recalc_engine.on_cell_edit` then returns the tracker's full fresh cell state in one response, so the frontend repaints from one round trip.
- New `libs/recalc_engine/repository.py`: `SQLAlchemyCellRepository`, the first real implementation of `engine.py`'s `CellRepository` Protocol (previously only a test fake existed).
  - **Flagged simplification:** `load_subgraph` loads every cell in the tracker rather than computing the true reverse-dependency frontier server-side (would need a recursive JSONB query) — correct for Phase 0's small, human-edited grids, not yet optimized for scale.
- **Flagged gap, not silently skipped:** these routes are tenant-scoped only, same precedent as `workspaces.py`. The PRD's workspace-level `resource_workspace_access` gating (D-2) isn't enforced here because `libs/access_control/` is still an empty stub nobody has built yet.
- New `NotFoundError` added to `libs/exceptions.py`'s hierarchy (404), used when a tracker id doesn't exist in the caller's tenant.

### Frontend Tracker grid (`apps/frontend/src/features/trackers/`)
- `useTrackers.ts`: React Query hooks for list/create/detail/cell-edit. The edit mutation writes the server's full recalculated response straight into cache (no client-side recompute — matches STANDARDS.md's AG Grid boundary).
- `TrackersPage.tsx`: real list + create form (replaces the earlier placeholder).
- `TrackerGridPage.tsx`: real AG Grid Community instance. **Fixed 15-row × 8-column window for Phase 0**, not driven by `Tracker.schema_definition` yet — flagged as real remaining scope. Editing a cell sends raw text to the API; `=`-prefixed text is sent as a formula, everything else as a raw value. The renderer shows computed values (or an error badge) for formula cells and raw text otherwise — editing always shows the underlying stored text, never the computed result, so you can see and change the formula itself.
- Route added: `/trackers/:trackerId`.
- `package.json` now includes `ag-grid-community` + `ag-grid-react` (^30.2.1).

### Not verified
Nothing in Session E has touched a real Postgres or run through real npm — same sandbox constraint as before. `docker compose up --build` is the next real test, and specifically: creating a tracker, opening its grid, typing `=A1+A2`-style formulas into cells, and confirming values + error states repaint correctly.

### Flags carried forward
1. Tracker access control is tenant-scoped only — no workspace-level view/edit/admin gating yet (real scope, `libs/access_control/` still unbuilt).
2. `load_subgraph` loads a whole tracker per edit — fine for Phase 0 grid sizes, not scale-tested.
3. Grid dimensions are hardcoded (15×8), not schema-driven.
4. Formula resolver's precedence is still left-to-right only (flagged last session, unchanged).
5. OAuth frontend flow still not built.

---

## Session F — Approvals inbox

### `apps/api/approvals.py`
- `GET /v1/approvals` (pending jobs for the tenant), `POST /v1/approvals/{id}/approve`, `POST /v1/approvals/{id}/reject` — built directly on the `transformation_jobs` table and `TransformationJobStatus` enum that already existed in the schema/migration but had no API surface at all until now.
- **Flagged prominently, not a quiet gap:** this is tenant-scoped only, same precedent as trackers/workspaces. The PRD's real approval gate needs an `is_approver` grant check scoped to the job's workspace (D-17) — that requires `libs/access_control/`, still an empty stub. Any authenticated tenant user can currently approve/reject any pending job in their tenant. This is explicitly called out in the route module's docstring as not production-ready gating.
- **Can't be exercised end-to-end yet:** nothing creates a `pending_approval` job — that's the planner app (`apps/planner/`), still unbuilt. The inbox will correctly show an empty state until then.
- Reused `NotFoundError` (added last session) for missing/foreign-tenant jobs.

### Frontend (`apps/frontend/src/features/approvals/`)
- `useApprovals.ts`: list + approve + reject React Query hooks.
- `ApprovalsPage.tsx`: replaces the placeholder — real list UI with Approve/Reject buttons, honest empty state explaining why it's empty rather than faking sample rows.

### Not verified
Same sandbox constraint as every prior session — no real Postgres/npm run. Additionally, this feature genuinely cannot be smoke-tested end-to-end even locally yet, since nothing produces a `pending_approval` job to approve. A manual `INSERT` into `transformation_jobs` (with a matching `datasets` row) would be the only way to see the inbox populated before the planner exists.

### Flags carried forward (updated)
1. Tracker + Approvals access control is tenant-scoped only — no workspace-level gating (`libs/access_control/` still unbuilt). **This is now the single biggest cross-cutting gap** since two features depend on it.
2. `load_subgraph` loads a whole tracker per edit — fine for Phase 0 grid sizes, not scale-tested.
3. Grid dimensions are hardcoded (15×8), not schema-driven.
4. Formula resolver's precedence is still left-to-right only.
5. OAuth frontend flow still not built.
6. Approvals inbox has no real data source yet (planner app unbuilt) — can't be tested end-to-end even locally.

### Suggested next step
`libs/access_control/` itself — resolving `effective_access(user)` from `access_grants` + `resource_workspace_access` — is now blocking honest completion of both Tracker and Approvals gating. Building that once, and retrofitting both routes to use it, is likely higher-leverage than adding a third feature on the same tenant-only shortcut.

---

## Session G — Full feature build-out (backend + frontend), per explicit "build everything, keep it simple, optimize later" direction

This session built out effectively everything remaining in Layer-wise Development at demo/simple fidelity, plus GCP/Vertex AI wiring and a full public website. Scope was deliberately breadth-first: every corner cut is flagged in the code's own docstrings, not hidden.

### `libs/access_control/resolve.py` — built (closes last session's flagged gap)
`effective_access()` and `is_approver()`, resolving `access_grants` + `resource_workspace_access`, including team-based grants via `team_memberships`. **Approvals now actually enforces `is_approver`** (with a pragmatic "tenant Admins can always approve" fallback) instead of the tenant-only shortcut. Trackers were *not* retrofitted this session — still tenant-scoped only, now the one remaining gap of this kind.

### `libs/connectors/` — Postgres, MySQL, SQL Server, Snowflake adapters + registry
Demo-level: each adapter local-imports its real driver (asyncpg/aiomysql/pyodbc/snowflake-connector-python) so the app doesn't hard-depend on all four; `/test` reports "driver not installed" cleanly if missing. New `pyproject.toml` `[connectors]` extra.

### `libs/gcp/` + `libs/llm_provider/vertex.py` — real GCP/Vertex AI wiring
- `storage.py`: GCS upload/download for Documents, falling back to local disk if `GCS_BUCKET` is unset.
- `secrets.py`: Secret Manager read/write -- built but **not yet called from anywhere** (connector credentials still stored as plain JSONB, flagged).
- `vertex.py`: real Vertex AI/Gemini adapter satisfying the D-10 `LLMProvider` Protocol, with native function-calling.
- `naive.py` + `factory.py`: a zero-dependency keyword-based provider is the *default* (`LLM_PROVIDER=naive`), so the whole chat-planner feature works with no GCP setup at all. Set `LLM_PROVIDER=vertex` + the GCP env vars to switch.
- `infra/gcp/README.md`: what's wired vs. planned, IAM roles, and an explicit note that this doesn't use Vertex AI's provisioned/cluster endpoints (serverless Gemini API only) -- with a stated path to add that if ever needed.
- New `pyproject.toml` `[gcp]` extra.

### `apps/planner/` — built from scratch
- `intent_classifier.py`: keyword-based intent -> narrows which tools are offered per turn.
- `rag.py`: naive keyword-overlap search over `Document.content_text` -- explicitly not real embeddings/vector search, flagged as the swap point for later.
- `tools.py`: all four PRD tools. `sql_query_tool` persists a real `pending_approval` `TransformationJob` (shows up in the Approvals inbox). `tracker_query_tool` and `chart_tool` are also gated per Standards, but **their gate is ephemeral** (an `ApprovalRequiredError` with proposed details, not a persisted queue row) since neither maps onto `TransformationJob`'s dataset-shaped model -- flagged clearly, real follow-up is giving every gated tool a persisted queue entry.
- `planner.py`: orchestrates a full chat turn -- persists the user message, loads history, classifies intent, calls the active `LLMProvider`, dispatches tool calls, persists the assistant message with `tool_calls` metadata.

### `apps/worker/job_runner.py` — built
Executes `approved` `TransformationJob` rows. **Demo-level, explicitly flagged:** no real sandboxed execution, no sample-vs-full-data toggle, no FR-15 cache_key memoization check before running -- it marks the job `succeeded` and bumps the dataset's `version` as a stand-in. Run via `python -m apps.worker.job_runner` or wire to a scheduler; there's no queue consumer/poll loop (Kafka is explicitly out of scope per the PRD).

### New API routes, all wired into `main.py`
`chat.py`, `documents.py` (upload only extracts text for txt/md/csv/json -- other formats store but aren't searchable, flagged), `tickets.py`, `tenant_requests.py` (public submit + Admin-only review; **provisions a real Tenant + Admin User on approval**, returning a temporary password in the response body since no email system exists -- explicitly flagged as not production-safe), `teams.py`, `users.py` (FR-3's Admin-vs-Developer invite rules enforced), `ingestion.py` (connector config CRUD + test-connection).

### New migration `0003`
`documents.name`/`content_text`, `tickets.title`/`description`, `connector_configs` table, `chat_messages` table. Same caveat as 0001/0002: hand-written, not run against real Postgres in this sandbox.

### Frontend — full rebuild
- **Rebrand**: white + light green (`tokens.css` fully replaced; every hardcoded dark-theme color across Login/Trackers/AppLayout swapped for the new tokens; AG Grid switched from `ag-theme-alpine-dark` to `ag-theme-alpine`).
- **Public marketing site** (`features/marketing/`): `MarketingLayout` (top nav: Home/Product/Pricing/About + Sign in/Request access), `HomePage`, `ProductPage`, `PricingPage` (no real billing -- every tier routes to Request Access), `AboutPage`, `RequestAccessPage` (real POST to `/v1/tenant-requests`, no auth). Mounted at `/`.
- **App moved to `/app/*`**, still behind `RequireAuth`. Nav rail (`AppLayout`) now lists Workspaces/Trackers/Approvals/Tickets/Ingestion/Documents/Chat-Planner/Team.
- **New real feature pages**, replacing the last remaining placeholders: `TicketsPage` (real CRUD, workspace-scoped), `IngestionPage` (connector config CRUD + test-connection button), `ChatPlannerPage` (real chat UI against `/v1/chat`, shows a pending-approval badge on gated tool calls -- the PRD's editable-code-cell half of the "hybrid chat" model is *not* built, flagged), `DocumentsPage` (upload + list, shows which uploads are search-indexed), `TeamPage` (Users + Teams + an Admin-only Tenant-requests review panel that just doesn't render for non-Admins on a 403).

### Not verified (same constraint as every session)
No real Postgres/npm/GCP run in this sandbox. Verified only via `py_compile` (62 backend files, 0 errors) and a manual check that every frontend `@/` import resolves to a real file (32 frontend source files). Nothing has been through a real `docker compose up --build`, `npm install`, or an actual Vertex AI/GCS call.

### Flags carried forward (full current list)
1. **Trackers access control is still tenant-scoped only** — Approvals got the real `is_approver` check this session, Trackers didn't. This is now the single biggest inconsistency: two routes on different standards.
2. `tracker_query_tool`/`chart_tool`'s approval gate is ephemeral (not persisted) — only `sql_query_tool` shows up durably in the Approvals inbox.
3. Secret Manager (`libs/gcp/secrets.py`) is built but unused — connector credentials are still plain JSONB.
4. Document text extraction only works for txt/md/csv/json uploads — PDF/DOCX store but aren't searchable yet.
5. RAG is naive keyword overlap, not embeddings — flagged as the intended swap point.
6. Worker has no real execution engine, no memoization check, no queue consumer.
7. Tenant-request approval returns a live temporary password in the API response body — explicitly not production-safe, no email system exists to do this properly.
8. `load_subgraph` (Trackers) still loads a whole tracker per edit; grid is still hardcoded 15×8; formula resolver precedence is still left-to-right only.
9. OAuth frontend flow still not built.
10. Chat-planner UI has no editable-code-cell interaction, just a plain transcript.
11. No Terraform/Cloud Build/actual GCP deployment exists — `infra/gcp/README.md` is a plan, not an implementation. Nothing uses Vertex AI provisioned/cluster endpoints, only the serverless Gemini API.

### Suggested next step
Pick one: (a) retrofit Trackers to use `libs/access_control` so both gated features are on the same standard, or (b) give `tracker_query_tool`/`chart_tool` a real persisted approval-queue entry instead of the ephemeral one, or (c) start the Testing stage properly — a real `pytest` run against a real Postgres instance, since nothing in this entire repo has executed against a live database yet across every session so far.

---

## Session H — Retrofit Trackers onto real access control

Closed flag #1 from Session G: Trackers now use `libs/access_control.effective_access()` the same way Approvals uses `is_approver()`.

- `apps/api/trackers.py`: `get_tracker` now requires `view`+ access, `edit_cell` requires `edit`+ access. Both resolved via any `resource_workspace_access` binding(s) on the tracker.
- **Same pragmatic fallbacks as Approvals**, for the same reason (nobody should be locked out of something they made or own the tenant for): a tenant Admin always passes; the tracker's own creator always passes.
- **Same "fail open" precedent preserved, not silently changed**: a tracker with *no* workspace binding at all still falls back to tenant-scoping only — there's nothing to resolve access against. What changed is `create_tracker` now accepts an optional `workspace_id` and, if given, creates the `resource_workspace_access` binding (`edit` level) immediately — so going forward the no-binding fallback is opt-in-to-skip, not the unavoidable default.
- Frontend: `TrackersPage.tsx` create form now has a workspace picker (defaults to "No workspace (tenant-wide fallback)", making the tradeoff visible rather than silent); `useCreateTracker` passes `workspace_id` through.
- `libs/models/__init__.py` now also exports `AccessLevel`, `GrantResourceType`, `GrantedVia` (needed by the retrofit, weren't exported before).

### Remaining flags (updated)
Item #1 from Session G's list is now resolved. Items #2 (ephemeral tracker/chart approval gate), #3 (Secret Manager unused), #4 (limited text extraction), #5 (naive RAG), #6 (worker has no real execution engine), #7 (temp password in API response), #8 (hardcoded grid, left-to-right formula precedence), #9 (no OAuth frontend flow), #10 (no editable-code-cell chat UI), #11 (no real GCP deployment) all still stand exactly as flagged in Session G.

### Not verified
Same constraint as always — `_require_access`'s SQL logic (querying `resource_workspace_access` + delegating to `effective_access`) is untested against a real database. Compile-checked only.

