"""Postgres connector (D-3). Demo-level: uses asyncpg directly, no
connection pooling or prepared-statement caching -- one connection per
call, opened and closed immediately. Fine for Phase 0's occasional
ingestion/profiling queries, not for high-frequency use.
"""

from __future__ import annotations

from typing import Any

from libs.connectors.base import ConnectionTestResult, QueryResult


class PostgresConnector:
    def __init__(self, config: dict[str, Any]) -> None:
        # Expected config keys: host, port, database, user, password.
        # IP allowlisting / SSH tunnel (D-3's security model) is an
        # infra-level concern -- assumed already in place by the time a
        # ConnectorConfig row exists, not re-implemented here.
        self._config = config

    async def test_connection(self) -> ConnectionTestResult:
        try:
            import asyncpg  # local import: optional dependency, not needed unless a Postgres connector is actually used
        except ImportError:
            return ConnectionTestResult(ok=False, message="asyncpg is not installed in this environment.")

        try:
            conn = await asyncpg.connect(
                host=self._config["host"],
                port=self._config.get("port", 5432),
                database=self._config["database"],
                user=self._config["user"],
                password=self._config["password"],
                timeout=5,
            )
            await conn.close()
            return ConnectionTestResult(ok=True, message="Connected successfully.")
        except Exception as exc:  # noqa: BLE001 -- surfacing the driver's own message is the point
            return ConnectionTestResult(ok=False, message=str(exc))

    async def run_query(self, sql: str, *, limit: int = 1000) -> QueryResult:
        import asyncpg

        conn = await asyncpg.connect(
            host=self._config["host"],
            port=self._config.get("port", 5432),
            database=self._config["database"],
            user=self._config["user"],
            password=self._config["password"],
        )
        try:
            records = await conn.fetch(sql)
        finally:
            await conn.close()

        rows = [list(r.values()) for r in records[:limit]]
        columns = list(records[0].keys()) if records else []
        return QueryResult(columns=columns, rows=rows)
