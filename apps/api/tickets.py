"""Tickets API -- straightforward CRUD over the Ticket model. Same
tenant-scoping-only precedent as Trackers/Approvals/Workspaces
(workspace-level access_level gating still needs libs/access_control's
resource_workspace_access path wired in per-route, not done here for
Tickets specifically)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, CurrentUserDep
from libs.db import get_db_session
from libs.exceptions import NotFoundError
from libs.models import Ticket, TicketStatus, Workspace

router = APIRouter(prefix="/v1/tickets", tags=["tickets"])


class CreateTicketRequest(BaseModel):
    workspace_id: uuid.UUID
    title: str
    description: str | None = None
    category: str = "general"


class UpdateTicketRequest(BaseModel):
    status: TicketStatus | None = None
    title: str | None = None
    description: str | None = None


class TicketResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: str | None
    category: str
    status: str

    model_config = {"from_attributes": True}


@router.post("", response_model=TicketResponse)
async def create_ticket(
    body: CreateTicketRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> Ticket:
    workspace = await session.get(Workspace, body.workspace_id)
    if workspace is None or workspace.tenant_id != current_user.tenant_id:
        raise NotFoundError(f"No workspace {body.workspace_id} in this tenant.")

    ticket = Ticket(
        workspace_id=body.workspace_id,
        title=body.title,
        description=body.description,
        category=body.category,
        created_by=current_user.user_id,
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    workspace_id: uuid.UUID | None = None,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[Ticket]:
    query = select(Ticket).join(Workspace, Workspace.id == Ticket.workspace_id).where(
        Workspace.tenant_id == current_user.tenant_id
    )
    if workspace_id is not None:
        query = query.where(Ticket.workspace_id == workspace_id)
    result = await session.scalars(query)
    return list(result)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: uuid.UUID,
    body: UpdateTicketRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> Ticket:
    ticket = await _get_tenant_ticket(session, ticket_id, current_user.tenant_id)
    if body.status is not None:
        ticket.status = body.status
    if body.title is not None:
        ticket.title = body.title
    if body.description is not None:
        ticket.description = body.description
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def _get_tenant_ticket(session: AsyncSession, ticket_id: uuid.UUID, tenant_id: uuid.UUID) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"No ticket {ticket_id}.")
    workspace = await session.get(Workspace, ticket.workspace_id)
    if workspace is None or workspace.tenant_id != tenant_id:
        raise NotFoundError(f"No ticket {ticket_id} in this tenant.")
    return ticket
