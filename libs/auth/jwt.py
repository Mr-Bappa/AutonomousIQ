"""JWT issuing and verification.

Stateless per the Baseline decision: all session state (user_id,
tenant_id, expiry) lives signed inside the token, nothing server-side to
look up. Secret comes from env, never hardcoded -- fails loudly on
import if missing, rather than silently using an insecure default.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

_SECRET = os.environ["JWT_SECRET"]  # intentionally no default -- see module docstring
_ALGORITHM = "HS256"
_ACCESS_TOKEN_TTL = timedelta(hours=12)


class InvalidTokenError(Exception):
    """Raised when a token is malformed, expired, or has a bad signature."""


def create_access_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "iat": now,
        "exp": now + _ACCESS_TOKEN_TTL,
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Returns the decoded payload ({"sub", "tenant_id", ...}). Raises
    InvalidTokenError for any failure -- callers shouldn't need to know
    whether it was expiry, bad signature, or malformed input; that
    distinction isn't actionable for an API caller."""
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
