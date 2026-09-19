"""FR-1: public 'Request Access' intake + admin-side manual tenant
provisioning. No self-serve tenant creation or billing (explicitly out
of scope per the PRD) -- approval always means a human (an internal
operator, modeled here as any tenant Admin) reviews and, on approval,
this endpoint creates the Tenant + its initial Admin user itself.

**Demo simplification, flagged:** there's no email system in this repo,
so the generated initial-Admin password is returned directly in the
approve response instead of being emailed -- fine for a demo, not for
production (a real flow must never return a live password over the API
response body to whoever clicked Approve).
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, PlatformAdminDep
from libs.auth.passwords import hash_password
from libs.db import get_db_session
from libs.exceptions import AccessDeniedError, NotFoundError
from libs.models import Tenant, TenantRequest, TenantRequestStatus, TenantRole, User

router = APIRouter(prefix="/v1/tenant-requests", tags=["tenant-requests"])


class SubmitTenantRequest(BaseModel):
    company_name: str
    contact_info: str


class TenantRequestResponse(BaseModel):
    id: uuid.UUID
    company_name: str
    contact_info: str
    status: str

    model_config = {"from_attributes": True}


class ApprovalResponse(BaseModel):
    tenant_id: uuid.UUID
    admin_user_id: uuid.UUID
    admin_email: str
    temporary_password: str


@router.post("", response_model=TenantRequestResponse)
async def submit_request(
    body: SubmitTenantRequest, session: AsyncSession = Depends(get_db_session)
) -> TenantRequest:
    """No auth -- this is the public product page's intake form."""
    request = TenantRequest(company_name=body.company_name, contact_info=body.contact_info)
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return request


@router.get("", response_model=list[TenantRequestResponse])
async def list_requests(
    current_user: CurrentUser = PlatformAdminDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[TenantRequest]:
    """Admin-only. Tenant requests have no tenant_id (they precede
    tenant existence), so this is scoped to "is the caller an Admin of
    *any* tenant" rather than tenant-scoped -- matching that these are
    reviewed by internal AutonomousIQ operators, not by the requester's
    own (not-yet-existing) tenant."""
    result = await session.scalars(select(TenantRequest).order_by(TenantRequest.created_at))
    return list(result)


@router.post("/{request_id}/approve", response_model=ApprovalResponse)
async def approve_request(
    request_id: uuid.UUID,
    current_user: CurrentUser = PlatformAdminDep,
    session: AsyncSession = Depends(get_db_session),
) -> ApprovalResponse:
    request = await session.get(TenantRequest, request_id)
    if request is None:
        raise NotFoundError(f"No tenant request {request_id}.")

    tenant = Tenant(name=request.company_name)
    session.add(tenant)
    await session.flush()

    temporary_password = secrets.token_urlsafe(12)
    admin_user = User(
        tenant_id=tenant.id,
        email=request.contact_info,
        role=TenantRole.admin,
        password_hash=hash_password(temporary_password),
    )
    session.add(admin_user)

    request.status = TenantRequestStatus.approved
    request.reviewed_by = current_user.user_id
    request.reviewed_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(tenant)
    await session.refresh(admin_user)

    return ApprovalResponse(
        tenant_id=tenant.id,
        admin_user_id=admin_user.id,
        admin_email=admin_user.email,
        temporary_password=temporary_password,
    )


@router.post("/{request_id}/reject", response_model=TenantRequestResponse)
async def reject_request(
    request_id: uuid.UUID,
    current_user: CurrentUser = PlatformAdminDep,
    session: AsyncSession = Depends(get_db_session),
) -> TenantRequest:
    request = await session.get(TenantRequest, request_id)
    if request is None:
        raise NotFoundError(f"No tenant request {request_id}.")
    request.status = TenantRequestStatus.rejected
    request.reviewed_by = current_user.user_id
    request.reviewed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(request)
    return request


