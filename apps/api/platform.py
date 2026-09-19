"""Platform Super Admin control-plane endpoints."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, PlatformAdminDep
from libs.db import get_db_session
from libs.exceptions import NotFoundError
from libs.models import Tenant, TenantRole, User

router = APIRouter(prefix="/v1/platform", tags=["platform"])

class TenantSummary(BaseModel):
    id: uuid.UUID
    name: str
    model_config = {"from_attributes": True}

class TenantUserSummary(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str

@router.get("/tenants", response_model=list[TenantSummary])
async def list_tenants(current_user: CurrentUser = PlatformAdminDep, session: AsyncSession = Depends(get_db_session)):
    return list(await session.scalars(select(Tenant).order_by(Tenant.created_at.desc())))

@router.get("/tenants/{tenant_id}/users", response_model=list[TenantUserSummary])
async def list_tenant_users(tenant_id: uuid.UUID, current_user: CurrentUser = PlatformAdminDep, session: AsyncSession = Depends(get_db_session)):
    if await session.get(Tenant, tenant_id) is None:
        raise NotFoundError("Tenant not found.")
    users = list(await session.scalars(select(User).where(User.tenant_id == tenant_id).order_by(User.email)))
    return [TenantUserSummary(id=u.id, email=u.email, role=u.role.value) for u in users]

@router.post("/tenants/{tenant_id}/users/{user_id}/make-admin", response_model=TenantUserSummary)
async def make_tenant_admin(tenant_id: uuid.UUID, user_id: uuid.UUID, current_user: CurrentUser = PlatformAdminDep, session: AsyncSession = Depends(get_db_session)):
    user = await session.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    if user is None:
        raise NotFoundError("User not found in tenant.")
    user.role = TenantRole.admin
    await session.commit()
    await session.refresh(user)
    return TenantUserSummary(id=user.id, email=user.email, role=user.role.value)
