"""Tenant / Team / User / TeamMembership models.

Covers FR-1 (tenant provisioning), FR-2 (team management), FR-3 (user
management). Tenant-level roles are Admin / Developer / User(Viewer) per
the PRD's role table -- this is distinct from `resource_workspace_access
.access_level` (D-2), which governs per-resource granularity within a
workspace, not tenant-wide role.
"""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from libs.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TenantRole(str, enum.Enum):
    """Tenant-wide role. Lowercase to match Postgres ENUM convention."""

    admin = "admin"
    developer = "developer"
    viewer = "viewer"


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A customer organization. Created manually by an internal operator
    on tenant_request approval (FR-1) -- no self-serve provisioning in
    Phase 0."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    teams: Mapped[list["Team"]] = relationship(back_populates="tenant")
    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class Team(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A grouping of users within a tenant. Admin-only create/rename/
    archive (FR-2)."""

    __tablename__ = "teams"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    archived: Mapped[bool] = mapped_column(default=False, nullable=False)

    tenant: Mapped["Tenant"] = relationship(back_populates="teams")
    memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="team")


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A user within a tenant. FR-3: Admin can invite/add/remove at any
    role tenant-wide; Developers only within their own team, and never
    to Admin."""

    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[TenantRole] = mapped_column(
        Enum(TenantRole, name="tenant_role"), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")
    team_memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="user")

    __table_args__ = ({"comment": "email is unique per tenant, not globally -- enforced via a"
                        " composite unique index in the migration, not here."},)


class TeamMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Join table between User and Team. Removing a membership row is
    what triggers FR-5's grant-retraction side effect (handled in
    libs/access_control, not here -- this model only records the fact of
    membership)."""

    __tablename__ = "team_memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )

    user: Mapped["User"] = relationship(back_populates="team_memberships")
    team: Mapped["Team"] = relationship(back_populates="memberships")
