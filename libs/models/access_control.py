"""access_grants and resource_workspace_access.

access_grants (FR-4/FR-6): team-baseline or user-level grants, add-only,
resolved via effective_access(user) = team_baseline_grants UNION
user_level_grants, independently per resource type.

D-17 (this stage): `is_approver` is resource-scoped like every other
grant type -- resource_id points at a workspace_id, not left null/global.
A user's approval authority for a gated action on workspace W is
resolved the same way as any other resource_type: does an is_approver
grant with resource_id = W exist in their effective_access set.
"""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from libs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GrantResourceType(str, enum.Enum):
    dataset = "dataset"
    workspace = "workspace"
    document = "document"
    tracker = "tracker"
    processing = "processing"
    is_approver = "is_approver"  # D-17: resource_id = workspace_id, resource-scoped


class GrantedVia(str, enum.Enum):
    team = "team"
    user = "user"


class AccessGrant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single add-only grant. FR-5: when granted_via='team', deleting
    the underlying team_membership auto-retracts this grant (handled in
    libs/access_control resolution logic, not via a DB trigger -- keeps
    the retraction auditable and testable in application code)."""

    __tablename__ = "access_grants"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[GrantResourceType] = mapped_column(
        Enum(GrantResourceType, name="grant_resource_type"), nullable=False
    )
    # Polymorphic target id: a dataset/workspace/document/tracker id for
    # those resource_types; a workspace_id for 'processing' and
    # 'is_approver' (D-17) since those are workspace-scoped capabilities
    # rather than grants on a single named resource.
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    granted_via: Mapped[GrantedVia] = mapped_column(
        Enum(GrantedVia, name="granted_via"), nullable=False
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=True
    )


class AccessLevel(str, enum.Enum):
    """D-2: renamed 'admin' -> 'resource_admin' to avoid collision with
    the tenant-level Admin role."""

    view = "view"
    comment = "comment"
    edit = "edit"
    resource_admin = "resource_admin"


class ResourceWorkspaceAccess(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Generalized resource<->workspace access binding (replaces the
    earlier reserved dataset_workspace_access, per PRD Data Model
    Additions)."""

    __tablename__ = "resource_workspace_access"

    resource_type: Mapped[GrantResourceType] = mapped_column(
        Enum(GrantResourceType, name="grant_resource_type"), nullable=False
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_level: Mapped[AccessLevel] = mapped_column(
        Enum(AccessLevel, name="access_level"), nullable=False
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
