"""Teams API (FR-2): Admin-only create/rename/archive; Developers can
view teams they belong to."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, CurrentUserDep
from libs.db import get_db_session
from libs.exceptions import AccessDeniedError, NotFoundError
from libs.models import Team, TeamMembership, TenantRole, User

router = APIRouter(prefix="/v1/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    name: str


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    archived: bool

    model_config = {"from_attributes": True}


@router.post("", response_model=TeamResponse)
async def create_team(
    body: CreateTeamRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> Team:
    await _require_admin(session, current_user.user_id)
    team = Team(tenant_id=current_user.tenant_id, name=body.name)
    session.add(team)
    await session.commit()
    await session.refresh(team)
    return team


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[Team]:
    """Admins see every team in the tenant; everyone else sees only
    teams they belong to (FR-2: "Developers may view teams they belong
    to" -- extended here to Users/Viewers too, since nothing in the PRD
    says they can't see their own team)."""
    user = await session.get(User, current_user.user_id)
    if user is not None and user.role == TenantRole.admin:
        result = await session.scalars(select(Team).where(Team.tenant_id == current_user.tenant_id))
        return list(result)

    result = await session.scalars(
        select(Team)
        .join(TeamMembership, TeamMembership.team_id == Team.id)
        .where(Team.tenant_id == current_user.tenant_id, TeamMembership.user_id == current_user.user_id)
    )
    return list(result)


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: uuid.UUID,
    body: CreateTeamRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> Team:
    await _require_admin(session, current_user.user_id)
    team = await session.get(Team, team_id)
    if team is None or team.tenant_id != current_user.tenant_id:
        raise NotFoundError(f"No team {team_id} in this tenant.")
    team.name = body.name
    await session.commit()
    await session.refresh(team)
    return team


@router.delete("/{team_id}", response_model=TeamResponse)
async def archive_team(
    team_id: uuid.UUID,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> Team:
    await _require_admin(session, current_user.user_id)
    team = await session.get(Team, team_id)
    if team is None or team.tenant_id != current_user.tenant_id:
        raise NotFoundError(f"No team {team_id} in this tenant.")
    team.archived = True
    await session.commit()
    await session.refresh(team)
    return team


async def _require_admin(session: AsyncSession, user_id: uuid.UUID) -> None:
    user = await session.get(User, user_id)
    if user is None or user.role != TenantRole.admin:
        raise AccessDeniedError("Only a tenant Admin can create, rename, or archive teams.")
