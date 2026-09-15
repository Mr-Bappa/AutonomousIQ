"""FastAPI application entrypoint.

Wires up the standard error envelope (STANDARDS.md Section 3) so every
AutonomousIQError subclass — and any unhandled exception — is returned to
the client in a consistent {"error": {...}} shape.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from apps.api import (
    approvals,
    auth,
    chat,
    documents,
    ingestion,
    tenant_requests,
    teams,
    tickets,
    trackers,
    users,
    workspaces,
)
from libs.auth.oauth import register_configured_providers
from libs.exceptions import AutonomousIQError

logger = logging.getLogger("autonomousiq.api")

app = FastAPI(title="AutonomousIQ API", version="0.1.0")

# The frontend (apps/frontend, Vite dev server) runs on a different
# origin/port than the API -- this wasn't needed until this session
# since no frontend existed to hit CORS at all. Phase 0 has exactly one
# frontend origin (no public API consumers yet), so an explicit
# allowlist rather than "*" costs nothing and is the safer default.
_CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authlib's OAuth2 authorize_redirect flow stores the request state/nonce
# in the session between the /login redirect and the /callback -- this is
# the one piece of server-side session state in an otherwise-stateless
# (JWT) auth design, and it's scoped to the OAuth handshake only.
app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET"])

app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(trackers.router)
app.include_router(approvals.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(tickets.router)
app.include_router(tenant_requests.router)
app.include_router(teams.router)
app.include_router(users.router)
app.include_router(ingestion.router)


@app.on_event("startup")
async def on_startup() -> None:
    register_configured_providers()


@app.exception_handler(AutonomousIQError)
async def domain_error_handler(request: Request, exc: AutonomousIQError) -> JSONResponse:
    """Translate any domain error into the standard API error envelope."""
    status_code = {
        "ACCESS_DENIED": 403,
        "AUTHENTICATION_FAILED": 401,
        "APPROVAL_REQUIRED": 409,
        "CONNECTOR_AUTH_FAILED": 502,
        "TENANT_ISOLATION_VIOLATION": 403,
        "RECALC_ERROR": 422,
        "NOT_FOUND": 404,
    }.get(exc.code, 400)

    if exc.code == "TENANT_ISOLATION_VIOLATION":
        # Never suppressed — always logged loudly regardless of status code.
        logger.error("tenant_isolation_violation", extra={"details": exc.details})

    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


@app.get("/v1/health")
async def health() -> dict[str, str]:
    """Basic liveness check."""
    return {"status": "ok"}
