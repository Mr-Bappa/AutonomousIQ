"""JWT issuing and verification for tenant and platform identities."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

_SECRET = os.environ["JWT_SECRET"]
_ALGORITHM = "HS256"
_ACCESS_TOKEN_TTL = timedelta(hours=12)


class InvalidTokenError(Exception):
    pass


def create_access_token(*, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": str(user_id), "tenant_id": str(tenant_id), "identity_type": "tenant",
        "iat": now, "exp": now + _ACCESS_TOKEN_TTL,
    }, _SECRET, algorithm=_ALGORITHM)


def create_platform_access_token(*, user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": str(user_id), "identity_type": "platform", "is_platform_admin": True,
        "iat": now, "exp": now + _ACCESS_TOKEN_TTL,
    }, _SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
