"""Connector adapter interface (D-3/D-13/D-14: Postgres, MySQL, SQL
Server, Snowflake). Kept deliberately simple/demo-level per this
session's brief: a connector is "can I connect, and can I run one
read-only query", nothing about pooling, retries, or query planning.

**Security flag:** real credentials belong in GCP Secret Manager per
PRD NFR-2 (`libs/gcp/secrets.py` has that client ready). Today,
`ConnectorConfig.config` (libs/models/chat_and_connectors.py) stores
connection parameters as plain JSONB -- wiring config to pull the actual
secret value from Secret Manager at connect-time, rather than storing
it directly, is the real follow-up, not done in this pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ConnectionTestResult:
    ok: bool
    message: str


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]


class Connector(Protocol):
    """Every connector adapter (postgres.py, mysql.py, sqlserver.py,
    snowflake.py) implements this against its own driver."""

    def __init__(self, config: dict[str, Any]) -> None: ...

    async def test_connection(self) -> ConnectionTestResult:
        """Attempt to open and immediately close a connection."""
        ...

    async def run_query(self, sql: str, *, limit: int = 1000) -> QueryResult:
        """Run a single read-only query and return up to `limit` rows.
        Callers (sql_query_tool) are responsible for ensuring the SQL is
        read-only and approval-gated -- this layer does not itself
        enforce that, it's a thin execution adapter only."""
        ...
