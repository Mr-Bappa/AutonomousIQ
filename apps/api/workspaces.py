"""Workspaces route -- the Baseline slice's "one real DB round trip",
gated behind auth."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from apps.api.deps import CurrentUserDep, CurrentUser
from libs.db import async_session_factory
from libs.models import Workspace

router = APIRouter(prefix="/v1/workspaces", tags=["workspaces"])


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    self_serve: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(current_user: CurrentUser = CurrentUserDep) -> list[Workspace]:
    """Lists workspaces for the caller's tenant. Phase 0 has no
    workspace-level roles (D-9), so tenant scoping alone is the access
    check here -- per-workspace access_level (D-2) governs actions
    *inside* a workspace, not whether it's listed."""
    async with async_session_factory() as session:
        result = await session.scalars(
            select(Workspace).where(Workspace.tenant_id == current_user.tenant_id)
        )
        return list(result)
