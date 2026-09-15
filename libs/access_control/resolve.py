"""Grant resolution -- the piece flagged as an empty stub across two
prior sessions and blocking real access gating on Trackers and
Approvals.

Two independent things a caller needs to know, matching the PRD/D-2/D-17
design:

1. **effective_access(user, resource_type, resource_id, workspace_id)**
   -- what access_level (view/comment/edit/resource_admin) does this
   user have on this resource, resolved as the union of their own
   user-level grants and every grant held by teams they belong to
   (FR-4/FR-5: "team_baseline_grants UNION user_level_grants").
2. **is_approver(user, workspace_id)** -- D-17: does this user hold an
   is_approver grant scoped to this workspace (directly, or via a team).

**Kept intentionally simple for this pass:** no caching, no batch
resolution for "does this user have access to N resources" (each check
is its own query) -- fine for Phase 0 traffic, a real optimization pass
would batch this. Also note FR-5's "deleting a team_membership
auto-retracts team-granted access" is naturally true here because
resolution is done live from current `team_memberships` rows every call
-- there's no separate retraction step needed, since a stale grant with
no matching membership row simply never matches.
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.models import AccessGrant, GrantResourceType, ResourceWorkspaceAccess, TeamMembership
from libs.models.access_control import AccessLevel, GrantedVia

# Ordering from least to most permissive -- used to compare "does the
# effective level satisfy the required level" (STANDARDS.md's D-2
# four-tier enum has a natural ordering even though the DB enum itself
# doesn't encode it).
_LEVEL_RANK = {
    AccessLevel.view: 0,
    AccessLevel.comment: 1,
    AccessLevel.edit: 2,
    AccessLevel.resource_admin: 3,
}


async def _user_team_ids(session: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    result = await session.scalars(
        select(TeamMembership.team_id).where(TeamMembership.user_id == user_id)
    )
    return list(result)


async def effective_access(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resource_type: GrantResourceType,
    resource_id: uuid.UUID,
) -> AccessLevel | None:
    """Resolve a user's effective access_level on a specific resource,
    via `resource_workspace_access` gated by an `access_grants` row on
    the resource's workspace (directly or through a team).

    Returns None if the user has no path to this resource at all.
    """
    workspace_bindings = await session.scalars(
        select(ResourceWorkspaceAccess).where(
            ResourceWorkspaceAccess.resource_type == resource_type,
            ResourceWorkspaceAccess.resource_id == resource_id,
        )
    )

    team_ids = set(await _user_team_ids(session, user_id))
    best: AccessLevel | None = None

    for binding in workspace_bindings:
        grant_exists = await session.scalar(
            select(AccessGrant.id).where(
                AccessGrant.resource_type == GrantResourceType.workspace,
                AccessGrant.resource_id == binding.workspace_id,
                or_(
                    and_(
                        AccessGrant.granted_via == GrantedVia.user,
                        AccessGrant.user_id == user_id,
                    ),
                    and_(
                        AccessGrant.granted_via == GrantedVia.team,
                        AccessGrant.team_id.in_(team_ids),
                    ),
                ),
            )
        )
        if grant_exists is None:
            continue
        if best is None or _LEVEL_RANK[binding.access_level] > _LEVEL_RANK[best]:
            best = binding.access_level

    return best


async def has_access(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resource_type: GrantResourceType,
    resource_id: uuid.UUID,
    required_level: AccessLevel,
) -> bool:
    """Convenience wrapper: does the user's effective access meet or
    exceed `required_level`?"""
    level = await effective_access(
        session, user_id=user_id, resource_type=resource_type, resource_id=resource_id
    )
    if level is None:
        return False
    return _LEVEL_RANK[level] >= _LEVEL_RANK[required_level]


async def is_approver(session: AsyncSession, *, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
    """D-17: is_approver is a resource-scoped grant (resource_id =
    workspace_id), resolved the same way as any other grant type --
    directly on the user, or via any team they belong to."""
    team_ids = set(await _user_team_ids(session, user_id))

    direct = await session.scalar(
        select(AccessGrant.id).where(
            AccessGrant.resource_type == GrantResourceType.is_approver,
            AccessGrant.resource_id == workspace_id,
            AccessGrant.granted_via == GrantedVia.user,
            AccessGrant.user_id == user_id,
        )
    )
    if direct is not None:
        return True

    if not team_ids:
        return False

    via_team = await session.scalar(
        select(AccessGrant.id).where(
            AccessGrant.resource_type == GrantResourceType.is_approver,
            AccessGrant.resource_id == workspace_id,
            AccessGrant.granted_via == GrantedVia.team,
            AccessGrant.team_id.in_(team_ids),
        )
    )
    return via_team is not None
