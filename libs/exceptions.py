"""Project-wide exception hierarchy.

All domain-specific errors should subclass AutonomousIQError so that a single
FastAPI exception handler can translate any of them into the standard API
error envelope (see STANDARDS.md, Section 3).
"""

from __future__ import annotations


class AutonomousIQError(Exception):
    """Base class for all domain errors in AutonomousIQ.

    Args:
        message: Human-readable error message.
        code: Machine-readable error code, used as the "code" field in the
            API error envelope (e.g. "APPROVAL_REQUIRED").
        details: Optional structured details for the error envelope's
            "details" field.
    """

    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AccessDeniedError(AutonomousIQError):
    """Raised when a user lacks the required access_grant or
    resource_workspace_access entry for the requested action."""

    code = "ACCESS_DENIED"


class ApprovalRequiredError(AutonomousIQError):
    """Raised when an action requires human approval before it can proceed
    (e.g. sql_query_tool, tracker_query_tool, chart_tool per the PRD's
    approval-gate requirements)."""

    code = "APPROVAL_REQUIRED"


class ConnectorAuthError(AutonomousIQError):
    """Raised when a live database connector fails to authenticate
    (Postgres, MySQL, SQL Server, or Snowflake — see Architecture Decision
    Log D-3, D-13, D-14)."""

    code = "CONNECTOR_AUTH_FAILED"


class TenantIsolationError(AutonomousIQError):
    """Raised when an operation would cross tenant isolation boundaries.
    This should never be caught and suppressed — it indicates either a bug
    or an active attempt to breach isolation, and must always be logged
    and surfaced."""

    code = "TENANT_ISOLATION_VIOLATION"


class RecalcEngineError(AutonomousIQError):
    """Raised by the Tracker recalculation engine (see D-1/D-7) on
    circular references or invalid formula syntax."""

    code = "RECALC_ERROR"
