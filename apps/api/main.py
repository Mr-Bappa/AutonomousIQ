"""FastAPI application entrypoint.

Wires up the standard error envelope (STANDARDS.md Section 3) so every
AutonomousIQError subclass — and any unhandled exception — is returned to
the client in a consistent {"error": {...}} shape.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from libs.exceptions import AutonomousIQError

logger = logging.getLogger("autonomousiq.api")

app = FastAPI(title="AutonomousIQ API", version="0.1.0")


@app.exception_handler(AutonomousIQError)
async def domain_error_handler(request: Request, exc: AutonomousIQError) -> JSONResponse:
    """Translate any domain error into the standard API error envelope."""
    status_code = {
        "ACCESS_DENIED": 403,
        "APPROVAL_REQUIRED": 409,
        "CONNECTOR_AUTH_FAILED": 502,
        "TENANT_ISOLATION_VIOLATION": 403,
        "RECALC_ERROR": 422,
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
