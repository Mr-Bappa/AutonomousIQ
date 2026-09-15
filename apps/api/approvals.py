"""Approvals inbox -- surfaces `transformation_jobs` rows sitting in
`pending_approval` (FR-11/FR-14/FR-15, TransformationJobStatus) so a
human can approve or reject before anything AI-proposed actually runs.

**Update (this session): is_approver is now enforced.** Earlier this
session, approve/reject were tenant-scoped only because
`libs/access_control/` didn't exist. It now does
(`libs/access_control/resolve.py`), so `approve_job`/`reject_job` check
`is_approver(user, workspace_id)` (D-17) before acting -- resolved via
the job's dataset's `resource_workspace_access` binding(s). A job whose
dataset has no workspace binding at all has no approver path and is
correctly rejected with AccessDeniedError rather than silently allowed.

`list_pending_approvals` still lists tenant-wide rather than filtering
to "workspaces where I'm an approver" -- seeing the queue and being
allowed to act on it are different questions, and PRD doesn't say
non-approvers can't see what's pending, only that they can't act on it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, CurrentUserDep
from libs.access_control.resolve import is_approver
from libs.db import get_db_session
from libs.exceptions import AccessDeniedError, NotFoundError
from libs.models import (
    Dataset,
    GrantResourceType,
    ResourceWorkspaceAccess,
    TenantRole,
    TransformationJob,
    TransformationJobStatus,
    User,
)

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])


class TransformationJobResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    code_version: str
    dataset_version: int
    sample_used: bool
    approval_metadata: dict
    execution_target: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TransformationJobResponse])
async def list_pending_approvals(
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[TransformationJob]:
    """Every `pending_approval` job whose dataset belongs to the
    caller's tenant. See module docstring re: is_approver not yet
    enforced -- this is tenant-wide visibility, not workspace-scoped."""
    result = await session.scalars(
        select(TransformationJob)
        .join(Dataset, Dataset.id == TransformationJob.dataset_id)
        .where(
            Dataset.tenant_id == current_user.tenant_id,
            TransformationJob.status == TransformationJobStatus.pending_approval,
        )
    )
    return list(result)


@router.post("/{job_id}/approve", response_model=TransformationJobResponse)
async def approve_job(
    job_id: uuid.UUID,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> TransformationJob:
    job = await _get_tenant_job(session, job_id, current_user.tenant_id)
    await _require_approver(session, job, current_user.user_id)
    job.status = TransformationJobStatus.approved
    job.approval_metadata = {
        **job.approval_metadata,
        "approved_by": str(current_user.user_id),
        "approved_at": datetime.now(timezone.utc).isoformat(),
    }
    await session.commit()
    await session.refresh(job)
    return job


@router.post("/{job_id}/reject", response_model=TransformationJobResponse)
async def reject_job(
    job_id: uuid.UUID,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> TransformationJob:
    job = await _get_tenant_job(session, job_id, current_user.tenant_id)
    await _require_approver(session, job, current_user.user_id)
    job.status = TransformationJobStatus.rejected
    job.approval_metadata = {
        **job.approval_metadata,
        "rejected_by": str(current_user.user_id),
        "rejected_at": datetime.now(timezone.utc).isoformat(),
    }
    await session.commit()
    await session.refresh(job)
    return job


async def _require_approver(session: AsyncSession, job: TransformationJob, user_id: uuid.UUID) -> None:
    """D-17: the job's dataset must be bound to at least one workspace
    where the caller holds is_approver. A dataset with no workspace
    binding at all has no valid approver path -- fail closed, not open.

    Pragmatic exception: tenant Admins can always approve/reject,
    without needing an explicit is_approver grant. FR-3 already gives
    Admins tenant-wide authority over users/teams; requiring them to
    additionally self-grant is_approver on every workspace before they
    can act on their own tenant's queue would be a paper cut with no
    real security benefit.
    """
    user = await session.get(User, user_id)
    if user is not None and user.role == TenantRole.admin:
        return

    bindings = await session.scalars(
        select(ResourceWorkspaceAccess).where(
            ResourceWorkspaceAccess.resource_type == GrantResourceType.dataset,
            ResourceWorkspaceAccess.resource_id == job.dataset_id,
        )
    )
    for binding in bindings:
        if await is_approver(session, user_id=user_id, workspace_id=binding.workspace_id):
            return
    raise AccessDeniedError(
        "You don't hold is_approver on any workspace this job's dataset is bound to."
    )


async def _get_tenant_job(
    session: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID
) -> TransformationJob:
    job = await session.get(TransformationJob, job_id)
    if job is None:
        raise NotFoundError(f"No transformation job {job_id}.")
    dataset = await session.get(Dataset, job.dataset_id)
    if dataset is None or dataset.tenant_id != tenant_id:
        raise NotFoundError(f"No transformation job {job_id} in this tenant.")
    return job
