"""Shared FastAPI authentication dependencies."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header

from libs.auth.jwt import InvalidTokenError, decode_access_token
from libs.exceptions import AccessDeniedError, AuthenticationError


@dataclass(frozen=True)
class CurrentUser:
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    is_platform_admin: bool = False


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or malformed Authorization header.")
    try:
        payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
    except InvalidTokenError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    identity_type = payload.get("identity_type", "tenant")
    tenant_raw = payload.get("tenant_id")
    return CurrentUser(
        user_id=uuid.UUID(payload["sub"]),
        tenant_id=uuid.UUID(tenant_raw) if tenant_raw else None,
        is_platform_admin=identity_type == "platform" and bool(payload.get("is_platform_admin")),
    )


async def require_platform_admin(authorization: str | None = Header(default=None)) -> CurrentUser:
    user = await get_current_user(authorization)
    if not user.is_platform_admin:
        raise AccessDeniedError("Platform Super Admin access required.")
    return user


CurrentUserDep = Depends(get_current_user)
PlatformAdminDep = Depends(require_platform_admin)
