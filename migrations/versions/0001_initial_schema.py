"""Initial schema — Data stage.

Creates every table from the PRD's Data Model Additions section, with
the Data-stage decisions layered on top of the Architecture-stage shapes:
  - D-17: access_grants.resource_type includes 'is_approver', resource-
    scoped (resource_id = workspace_id).
  - D-18: tracker_cells.depends_on, derived dependency list + GIN index
    for reverse-dependency lookups during recalc propagation.
  - D-19: tracker_cells.tenant_id, denormalized for isolation.
  - D-20: tracker_cells.error_state, persisted circular-reference /
    invalid-formula state.

Written by hand rather than via `alembic revision --autogenerate`
because this sandbox has no database connection to introspect against
-- verify by running `alembic upgrade head` against a real Postgres
instance before treating this as confirmed-working.

Revision ID: 0001
Revises:
Create Date: 2026-09-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tenants / teams / users / team_memberships -----------------
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_teams_tenant_id", "teams", ["tenant_id"])

    tenant_role = postgresql.ENUM("admin", "developer", "viewer", name="tenant_role")
    tenant_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", tenant_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    # Email unique per tenant, not globally.
    op.create_unique_constraint("uq_users_tenant_id_email", "users", ["tenant_id", "email"])

    op.create_table(
        "team_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_team_memberships_user_id", "team_memberships", ["user_id"])
    op.create_index("ix_team_memberships_team_id", "team_memberships", ["team_id"])
    op.create_unique_constraint(
        "uq_team_memberships_user_team", "team_memberships", ["user_id", "team_id"]
    )

    # --- workspaces / datasets / documents ---------------------------
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("self_serve", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workspaces_tenant_id", "workspaces", ["tenant_id"])

    dataset_visibility = postgresql.ENUM("tenant_wide", "restricted", name="dataset_visibility")
    dataset_visibility.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("visibility", dataset_visibility, nullable=False),
        sa.Column("is_processed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("lineage_pointer", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_datasets_tenant_id", "datasets", ["tenant_id"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("storage_pointer", sa.String(1024), nullable=False),
        sa.Column("format", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])

    # --- trackers / tracker_cells (D-7, D-18, D-19, D-20) ------------
    op.create_table(
        "trackers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("schema_definition", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_trackers_tenant_id", "trackers", ["tenant_id"])

    cell_error_state = postgresql.ENUM(
        "none", "circular_reference", "invalid_formula", "upstream_error",
        name="cell_error_state",
    )
    cell_error_state.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tracker_cells",
        sa.Column("tracker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trackers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("row_idx", sa.Integer, primary_key=True),
        sa.Column("col_idx", sa.Integer, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_value", sa.Text, nullable=True),
        sa.Column("formula", sa.Text, nullable=True),
        sa.Column("computed_value", sa.Text, nullable=True),
        sa.Column("depends_on", postgresql.JSONB, nullable=True),
        sa.Column("error_state", cell_error_state, nullable=False, server_default="none"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tracker_cells_tenant_id", "tracker_cells", ["tenant_id"])
    # D-18: GIN index supports "which cells reference (tracker,row,col)?"
    # -- the reverse-dependency walk used during topological propagation.
    op.create_index(
        "ix_tracker_cells_depends_on_gin",
        "tracker_cells",
        ["depends_on"],
        postgresql_using="gin",
    )

    # --- access_grants / resource_workspace_access (D-2, D-17) -------
    grant_resource_type = postgresql.ENUM(
        "dataset", "workspace", "document", "tracker", "processing", "is_approver",
        name="grant_resource_type",
    )
    grant_resource_type.create(op.get_bind(), checkfirst=True)
    granted_via = postgresql.ENUM("team", "user", name="granted_via")
    granted_via.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "access_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", grant_resource_type, nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_via", granted_via, nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_access_grants_user_id", "access_grants", ["user_id"])
    # Hot path: effective_access(user) resolution (FR-6) filters by
    # (user_id, resource_type, resource_id) constantly -- e.g. is_approver
    # checks on every gated action per D-17.
    op.create_index(
        "ix_access_grants_lookup",
        "access_grants",
        ["user_id", "resource_type", "resource_id"],
    )

    access_level = postgresql.ENUM("view", "comment", "edit", "resource_admin", name="access_level")
    access_level.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "resource_workspace_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource_type", grant_resource_type, nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("access_level", access_level, nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resource_workspace_access_workspace_id", "resource_workspace_access", ["workspace_id"])
    op.create_index(
        "ix_resource_workspace_access_lookup",
        "resource_workspace_access",
        ["resource_type", "resource_id", "workspace_id"],
    )

    # --- transformation_jobs / tickets / tenant_requests -------------
    tj_status = postgresql.ENUM(
        "pending_approval", "approved", "running", "succeeded", "failed", "rejected",
        name="transformation_job_status",
    )
    tj_status.create(op.get_bind(), checkfirst=True)
    execution_target = postgresql.ENUM("cloud", "local", name="execution_target")
    execution_target.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "transformation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_version", sa.String(64), nullable=False),
        sa.Column("dataset_version", sa.Integer, nullable=False),
        sa.Column("sample_used", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("status", tj_status, nullable=False),
        sa.Column("approval_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("cache_key", sa.String(128), nullable=False),
        sa.Column("execution_target", execution_target, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_transformation_jobs_dataset_id", "transformation_jobs", ["dataset_id"])
    op.create_index("ix_transformation_jobs_cache_key", "transformation_jobs", ["cache_key"])
    # FR-15 memoization key.
    op.create_unique_constraint(
        "uq_transformation_jobs_code_dataset_version",
        "transformation_jobs",
        ["code_version", "dataset_version"],
    )

    ticket_status = postgresql.ENUM("open", "in_progress", "resolved", "closed", name="ticket_status")
    ticket_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", ticket_status, nullable=False, server_default="open"),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tickets_workspace_id", "tickets", ["workspace_id"])

    tenant_request_status = postgresql.ENUM("pending", "approved", "rejected", name="tenant_request_status")
    tenant_request_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tenant_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("contact_info", sa.String(255), nullable=False),
        sa.Column("status", tenant_request_status, nullable=False, server_default="pending"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tenant_requests")
    op.drop_table("tickets")
    op.execute("DROP TYPE IF EXISTS ticket_status")
    op.drop_table("transformation_jobs")
    op.execute("DROP TYPE IF EXISTS execution_target")
    op.execute("DROP TYPE IF EXISTS transformation_job_status")
    op.drop_table("resource_workspace_access")
    op.execute("DROP TYPE IF EXISTS access_level")
    op.drop_table("access_grants")
    op.execute("DROP TYPE IF EXISTS granted_via")
    op.execute("DROP TYPE IF EXISTS grant_resource_type")
    op.drop_table("tracker_cells")
    op.execute("DROP TYPE IF EXISTS cell_error_state")
    op.drop_table("trackers")
    op.drop_table("documents")
    op.drop_table("datasets")
    op.execute("DROP TYPE IF EXISTS dataset_visibility")
    op.drop_table("workspaces")
    op.drop_table("team_memberships")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS tenant_role")
    op.drop_table("teams")
    op.drop_table("tenants")
