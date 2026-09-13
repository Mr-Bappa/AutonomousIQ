# AutonomousIQ

The AI Analyst Layer for Data-Services Agencies — Phase 0.

This repo is scaffolded per `STANDARDS.md`. Read that first — it covers coding
conventions, the reasoning behind the repo layout below, API/error-envelope
conventions, and Git/branching rules.

## Status

Idea → Business Case → PRD → Architecture → **Standards ✅ → Repository ✅ (this scaffold)**
→ Data → Baseline → Layer-wise Development → Testing → Git/PR → CI → Containerization
→ Infrastructure → CD → Deployment → Monitoring → Experimentation → Continuous Improvement

See `AutonomousIQ_Architecture_Decision_Log.md` for the full set of locked
architecture decisions (D-1 through D-16) referenced throughout this codebase.

## Layout

```
apps/api/            FastAPI app: routes, auth, approvals inbox, tickets
apps/planner/          AI tool-router: sql_query_tool, tracker_query_tool, doc_search_tool, chart_tool
apps/worker/            transformation_jobs execution, sandboxed runtime, connector sync
apps/frontend/          React/TypeScript app

libs/models/            SQLAlchemy models (finalized at the Data stage)
libs/access_control/     access_grants + resource_workspace_access resolution
libs/connectors/         Postgres / MySQL / SQL Server / Snowflake adapters
libs/recalc_engine/      Tracker dependency graph + Formula.js bridge
libs/llm_provider/       model-agnostic planner adapter (single provider for Phase 0)

migrations/              Alembic
tests/                   mirrors apps/ + libs/
```

## Getting started (once dependencies are installable in your environment)

```bash
pip install -e ".[dev]"
ruff check .
mypy .
pytest
uvicorn apps.api.main:app --reload
```

Not yet runnable in a network-restricted sandbox — dependencies weren't
installable here (no PyPI access), so files are syntax-checked but not
test-executed. Run the above in CI or a normal dev environment to confirm.
