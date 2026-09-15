"""Users API (FR-3): Admin can invite/add/remove users at any role,
tenant-wide. Developers can invite/add/remove Developer/User roles
within their own team only, and can never create Admins. All role
changes are logged (kept simple here: written into a `role_changed_at`-
style note isn't modeled, so this pass logs via the standard logger --
a proper audit trail table is a real follow-up, not built)."""

from __future__ import annotations

import logging
import secrets
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, CurrentUserDep
from libs.auth.passwords import hash_password
from libs.db import get_db_session
from libs.exceptions import AccessDeniedError, NotFoundError
from libs.models import TeamMembership, TenantRole, User

router = APIRouter(prefix="/v1/users", tags=["users"])
logger = logging.getLogger("autonomousiq.api.users")


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: TenantRole
    team_id: uuid.UUID | None = None


class InviteUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    temporary_password: str


class UpdateRoleRequest(BaseModel):
    role: TenantRole


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[User]:
    result = await session.scalars(select(User).where(User.tenant_id == current_user.tenant_id))
    return list(result)


@router.post("", response_model=InviteUserResponse)
async def invite_user(
    body: InviteUserRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> InviteUserResponse:
    actor = await session.get(User, current_user.user_id)
    if actor is None:
        raise AccessDeniedError("Unknown actor.")

    if actor.role == TenantRole.admin:
        pass  # Admins can invite at any role, tenant-wide.
    elif actor.role == TenantRole.developer:
        if body.role == TenantRole.admin:
            raise AccessDeniedError("Developers cannot create Admins.")
        if body.team_id is None:
            raise AccessDeniedError("Developers must invite within a specific team.")
        membership = await session.scalar(
            select(TeamMembership).where(
                TeamMembership.user_id == actor.id, TeamMembership.team_id == body.team_id
            )
        )
        if membership is None:
            raise AccessDeniedError("Developers can only invite within their own team.")
    else:
        raise AccessDeniedError("Only Admins and Developers can invite users.")

    temporary_password = secrets.token_urlsafe(12)
    new_user = User(
        tenant_id=current_user.tenant_id,
        email=body.email,
        role=body.role,
        password_hash=hash_password(temporary_password),
    )
    session.add(new_user)
    await session.flush()

    if body.team_id is not None:
        session.add(TeamMembership(user_id=new_user.id, team_id=body.team_id))

    await session.commit()
    await session.refresh(new_user)
    logger.info(
        "user_invited",
        extra={"actor_id": str(actor.id), "new_user_id": str(new_user.id), "role": body.role.value},
    )
    return InviteUserResponse(
        id=new_user.id, email=new_user.email, role=new_user.role.value, temporary_password=temporary_password
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_role(
    user_id: uuid.UUID,
    body: UpdateRoleRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    actor = await session.get(User, current_user.user_id)
    if actor is None or actor.role != TenantRole.admin:
        raise AccessDeniedError("Only an Admin can change a user's role.")

    target = await session.get(User, user_id)
    if target is None or target.tenant_id != current_user.tenant_id:
        raise NotFoundError(f"No user {user_id} in this tenant.")

    old_role = target.role
    target.role = body.role
    await session.commit()
    await session.refresh(target)
    logger.info(
        "user_role_changed",
        extra={"actor_id": str(actor.id), "target_id": str(target.id), "old_role": old_role.value, "new_role": body.role.value},
    )
    return target
