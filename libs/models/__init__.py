"""AutonomousIQ ORM models.

Import this module to register all tables on Base.metadata, which is
required by Alembic autogenerate and test-time metadata creation.
"""

from libs.models.access_control import (
    AccessGrant,
    AccessLevel,
    GrantedVia,
    GrantResourceType,
    ResourceWorkspaceAccess,
)
from libs.models.base import Base
from libs.models.chat_and_connectors import (
    ChatMessage,
    ChatRole,
    ConnectorConfig,
    ConnectorType,
)
from libs.models.jobs import (
    ExecutionTarget,
    TenantRequest,
    TenantRequestStatus,
    Ticket,
    TicketStatus,
    TransformationJob,
    TransformationJobStatus,
)
from libs.models.tenant import (
    OAuthIdentity,
    OAuthProvider,
    Team,
    TeamMembership,
    Tenant,
    TenantRole,
    User,
)
from libs.models.tracker import CellErrorState, Tracker, TrackerCell
from libs.models.workspace import (
    Dataset,
    DatasetVisibility,
    Document,
    Workspace,
)

__all__ = [
    "Base",
    "Tenant",
    "TenantRole",
    "Team",
    "User",
    "TeamMembership",
    "OAuthIdentity",
    "OAuthProvider",
    "Workspace",
    "Dataset",
    "DatasetVisibility",
    "Document",
    "Tracker",
    "TrackerCell",
    "CellErrorState",
    "AccessGrant",
    "AccessLevel",
    "GrantedVia",
    "GrantResourceType",
    "ResourceWorkspaceAccess",
    "TransformationJob",
    "TransformationJobStatus",
    "ExecutionTarget",
    "Ticket",
    "TicketStatus",
    "TenantRequest",
    "TenantRequestStatus",
    "ConnectorConfig",
    "ConnectorType",
    "ChatMessage",
    "ChatRole",
]