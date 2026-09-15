"""Shared FastAPI dependencies: current authenticated user, DB session
re-export for convenience."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header

from libs.auth.jwt import InvalidTokenError, decode_access_token
from libs.exceptions import AuthenticationError


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    tenant_id: uuid.UUID


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    """Extracts and verifies the Bearer JWT. Raises AuthenticationError
    (-> 401 via the standard error envelope) for anything missing or
    invalid -- no distinction surfaced to the caller between "no header",
    "malformed", or "expired", matching jwt.py's reasoning."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or malformed Authorization header.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    return CurrentUser(
        user_id=uuid.UUID(payload["sub"]), tenant_id=uuid.UUID(payload["tenant_id"])
    )


CurrentUserDep = Depends(get_current_user)
