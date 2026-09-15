"""Tracker routes -- Layer-wise Development's first slice on top of the
Baseline auth+workspaces foundation.

Wires the recalc engine (libs/recalc_engine/engine.py), which had no
caller at all until now, to a real HTTP surface via
SQLAlchemyCellRepository (libs/recalc_engine/repository.py).

**Update (Session H): real access checks, matching Approvals.**
`libs/access_control/resolve.py` now exists (built for Approvals in
Session F), so these routes use it too: `edit_cell` requires `edit`+
access, reads require `view`+, resolved via any
`resource_workspace_access` binding(s) the tracker has. Same pragmatic
fallback as Approvals: a tenant Admin always passes, and so does the
tracker's own creator (nobody should be locked out of a tracker they
just made because no grant exists yet). A tracker with **no** workspace
binding at all falls back to tenant-scoping only -- same as before --
since there's nothing to resolve access against; `create_tracker`
optionally binds a new tracker to a workspace right away (via an
optional `workspace_id` on the request) specifically so that fallback
path is the exception, not the default, going forward.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, CurrentUserDep
from libs.access_control.resolve import effective_access
from libs.db import get_db_session
from libs.exceptions import AccessDeniedError, NotFoundError
from libs.models import (
    AccessLevel,
    GrantResourceType,
    ResourceWorkspaceAccess,
    TenantRole,
    Tracker,
    TrackerCell,
    User,
    Workspace,
)
from libs.recalc_engine import engine as recalc_engine
from libs.recalc_engine.repository import SQLAlchemyCellRepository

router = APIRouter(prefix="/v1/trackers", tags=["trackers"])


# --- Schemas -----------------------------------------------------------


class CreateTrackerRequest(BaseModel):
    name: str
    schema_definition: dict = {}
    # Optional: bind the new tracker to a workspace immediately (with
    # `edit` access for whoever's in that workspace already, via
    # whatever access_grants exist on it) so it isn't left in the
    # tenant-scoping-only fallback described above.
    workspace_id: uuid.UUID | None = None


class TrackerSummary(BaseModel):
    id: uuid.UUID
    name: str
    schema_definition: dict

    model_config = {"from_attributes": True}


class CellResponse(BaseModel):
    row_idx: int
    col_idx: int
    raw_value: str | None
    formula: str | None
    computed_value: str | None
    error_state: str

    model_config = {"from_attributes": True}


class TrackerDetail(TrackerSummary):
    cells: list[CellResponse]


class CellEditRequest(BaseModel):
    row_idx: int
    col_idx: int
    raw_value: str | None = None
    formula: str | None = None


# --- Routes --------------------------------------------------------------


@router.post("", response_model=TrackerSummary)
async def create_tracker(
    body: CreateTrackerRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> Tracker:
    tracker = Tracker(
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
        name=body.name,
        schema_definition=body.schema_definition,
    )
    session.add(tracker)
    await session.flush()

    if body.workspace_id is not None:
        workspace = await session.get(Workspace, body.workspace_id)
        if workspace is None or workspace.tenant_id != current_user.tenant_id:
            raise NotFoundError(f"No workspace {body.workspace_id} in this tenant.")
        session.add(
            ResourceWorkspaceAccess(
                resource_type=GrantResourceType.tracker,
                resource_id=tracker.id,
                workspace_id=body.workspace_id,
                access_level=AccessLevel.edit,
                granted_by=current_user.user_id,
            )
        )

    await session.commit()
    await session.refresh(tracker)
    return tracker


@router.get("", response_model=list[TrackerSummary])
async def list_trackers(
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[Tracker]:
    result = await session.scalars(
        select(Tracker).where(Tracker.tenant_id == current_user.tenant_id)
    )
    return list(result)


@router.get("/{tracker_id}", response_model=TrackerDetail)
async def get_tracker(
    tracker_id: uuid.UUID,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> TrackerDetail:
    tracker = await _get_tenant_tracker(session, tracker_id, current_user.tenant_id)
    await _require_access(session, tracker, current_user.user_id, AccessLevel.view)
    cells_result = await session.scalars(
        select(TrackerCell).where(TrackerCell.tracker_id == tracker_id)
    )
    return TrackerDetail(
        id=tracker.id,
        name=tracker.name,
        schema_definition=tracker.schema_definition,
        cells=[CellResponse.model_validate(c) for c in cells_result],
    )


@router.put("/{tracker_id}/cells", response_model=TrackerDetail)
async def edit_cell(
    tracker_id: uuid.UUID,
    body: CellEditRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> TrackerDetail:
    """Edits one cell and triggers recalculation of everything
    downstream, then returns the tracker's full current cell state so
    the frontend can repaint the grid from one response rather than
    issuing a second GET.

    This is the recalc engine's first real caller: `on_cell_edit` (parse
    dependencies + persist), then `recalculate` (topological
    re-evaluation via the Formula.js sidecar), both against the same
    SQLAlchemyCellRepository/session so the whole edit is one
    transaction.
    """
    tracker = await _get_tenant_tracker(session, tracker_id, current_user.tenant_id)
    await _require_access(session, tracker, current_user.user_id, AccessLevel.edit)

    repo = SQLAlchemyCellRepository(session, tenant_id=current_user.tenant_id)
    edit = recalc_engine.CellEdit(
        coord=(body.row_idx, body.col_idx),
        raw_value=body.raw_value,
        formula=body.formula,
    )
    await recalc_engine.on_cell_edit(repo, str(tracker_id), edit)
    await session.commit()

    return await get_tracker(tracker_id, current_user, session)


async def _get_tenant_tracker(
    session: AsyncSession, tracker_id: uuid.UUID, tenant_id: uuid.UUID
) -> Tracker:
    tracker = await session.get(Tracker, tracker_id)
    if tracker is None or tracker.tenant_id != tenant_id:
        raise NotFoundError(f"No tracker {tracker_id} in this tenant.")
    return tracker


_LEVEL_RANK = {
    AccessLevel.view: 0,
    AccessLevel.comment: 1,
    AccessLevel.edit: 2,
    AccessLevel.resource_admin: 3,
}


async def _require_access(
    session: AsyncSession, tracker: Tracker, user_id: uuid.UUID, required: AccessLevel
) -> None:
    # Pragmatic fallbacks, same spirit as approvals.py's Admin exception:
    # the tracker's own creator, and any tenant Admin, always pass --
    # neither should be locked out by a missing grant on something they
    # made or own the tenant for.
    user = await session.get(User, user_id)
    if user is not None and user.role == TenantRole.admin:
        return
    if tracker.created_by == user_id:
        return

    bindings = await session.scalars(
        select(ResourceWorkspaceAccess).where(
            ResourceWorkspaceAccess.resource_type == GrantResourceType.tracker,
            ResourceWorkspaceAccess.resource_id == tracker.id,
        )
    )
    if not list(bindings):
        # No workspace binding at all -- fall back to tenant-scoping
        # only (this tracker predates or skipped the optional
        # workspace_id binding at creation). Same behavior as before
        # this session's retrofit, not a new gap.
        return

    level = await effective_access(
        session, user_id=user_id, resource_type=GrantResourceType.tracker, resource_id=tracker.id
    )
    if level is not None and _LEVEL_RANK[level] >= _LEVEL_RANK[required]:
        return

    raise AccessDeniedError(f"You don't have {required.value}+ access to this tracker.")
