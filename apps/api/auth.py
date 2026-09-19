"""Auth routes: email+password register/login, and OAuth login/callback
for google/facebook/linkedin (Baseline decision -- all four methods
included from the start, per explicit product decision, even though
that's more than a minimal Baseline slice would otherwise carry).

Pydantic schemas here double as the request/response contract per
STANDARDS.md Section 1.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from starlette.responses import RedirectResponse

from libs.auth.jwt import create_access_token, create_platform_access_token
from libs.auth.oauth import is_provider_configured, oauth
from libs.auth.passwords import hash_password, verify_password
from libs.db import async_session_factory
from libs.exceptions import AuthenticationError
from libs.models import OAuthIdentity, PlatformUser, Tenant, TenantRole, User

router = APIRouter(prefix="/v1/auth", tags=["auth"])

_SUPPORTED_PROVIDERS = {"google", "facebook", "linkedin"}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: uuid.UUID  # Phase 0: tenants are created manually (FR-1);
    # registration adds a user to an existing tenant, it never creates one.


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest) -> TokenResponse:
    async with async_session_factory() as session:
        existing = await session.scalar(
            select(User).where(User.tenant_id == body.tenant_id, User.email == body.email)
        )
        if existing is not None:
            raise AuthenticationError("A user with this email already exists in this tenant.")

        tenant = await session.get(Tenant, body.tenant_id)
        if tenant is None:
            raise AuthenticationError("Unknown tenant.")

        user = User(
            tenant_id=body.tenant_id,
            email=body.email,
            role=TenantRole.viewer,  # Default role on self-registration; an
            # Admin promotes as needed per FR-3 -- registration itself never
            # grants elevated access.
            password_hash=hash_password(body.password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    async with async_session_factory() as session:
        platform_user = await session.scalar(select(PlatformUser).where(PlatformUser.email == body.email))
        if platform_user is not None:
            if not platform_user.active or not verify_password(body.password, platform_user.password_hash):
                raise AuthenticationError("Invalid email or password.")
            token = create_platform_access_token(user_id=platform_user.id)
            return TokenResponse(access_token=token)

        user = await session.scalar(select(User).where(User.email == body.email))
        if user is None or user.password_hash is None:
            raise AuthenticationError("Invalid email or password.")
        if not verify_password(body.password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

    token = create_access_token(user_id=user.id, tenant_id=user.tenant_id)
    return TokenResponse(access_token=token)


@router.get("/{provider}/login")
async def oauth_login(provider: str, request: Request) -> RedirectResponse:
    if provider not in _SUPPORTED_PROVIDERS:
        raise AuthenticationError(f"Unsupported provider: {provider}")
    if not is_provider_configured(provider):
        raise AuthenticationError(
            f"{provider} is not configured (missing client id/secret env vars)."
        )
    client = oauth.create_client(provider)
    redirect_uri = request.url_for("oauth_callback", provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback", name="oauth_callback")
async def oauth_callback(
    provider: str, request: Request, tenant_id: uuid.UUID
) -> TokenResponse:
    """`tenant_id` is passed through as a query param from the frontend's
    initiating request (Phase 0 has no self-serve tenant creation, so we
    can't infer it from the OAuth profile alone -- the user must already
    be invited to a tenant, matching the password-registration flow's
    tenant_id requirement above)."""
    if provider not in _SUPPORTED_PROVIDERS:
        raise AuthenticationError(f"Unsupported provider: {provider}")
    if not is_provider_configured(provider):
        raise AuthenticationError(f"{provider} is not configured.")

    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)
    profile = token.get("userinfo") or await client.userinfo(token=token)
    provider_user_id = str(profile["sub"])
    email = profile.get("email")

    async with async_session_factory() as session:
        identity = await session.scalar(
            select(OAuthIdentity).where(
                OAuthIdentity.provider == provider,
                OAuthIdentity.provider_user_id == provider_user_id,
            )
        )
        if identity is not None:
            user = await session.get(User, identity.user_id)
        else:
            # First time linking this provider account: find-or-create a
            # User by (tenant_id, email), then attach the identity.
            user = await session.scalar(
                select(User).where(User.tenant_id == tenant_id, User.email == email)
            )
            if user is None:
                user = User(
                    tenant_id=tenant_id, email=email, role=TenantRole.viewer
                )
                session.add(user)
                await session.flush()  # populate user.id before the FK below
            session.add(
                OAuthIdentity(
                    user_id=user.id, provider=provider, provider_user_id=provider_user_id
                )
            )
            await session.commit()

        assert user is not None
        access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id)

    return TokenResponse(access_token=access_token)
