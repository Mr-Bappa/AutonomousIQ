"""Snowflake connector (D-3). Demo-level, uses the official
snowflake-connector-python (sync driver, run via asyncio.to_thread same
as sqlserver.py).
"""

from __future__ import annotations

import asyncio
from typing import Any

from libs.connectors.base import ConnectionTestResult, QueryResult


class SnowflakeConnector:
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    async def test_connection(self) -> ConnectionTestResult:
        return await asyncio.to_thread(self._test_connection_sync)

    def _test_connection_sync(self) -> ConnectionTestResult:
        try:
            import snowflake.connector
        except ImportError:
            return ConnectionTestResult(
                ok=False, message="snowflake-connector-python is not installed in this environment."
            )
        try:
            conn = snowflake.connector.connect(
                account=self._config["account"],
                user=self._config["user"],
                password=self._config["password"],
                warehouse=self._config.get("warehouse"),
                database=self._config.get("database"),
                schema=self._config.get("schema"),
                login_timeout=5,
            )
            conn.close()
            return ConnectionTestResult(ok=True, message="Connected successfully.")
        except Exception as exc:  # noqa: BLE001
            return ConnectionTestResult(ok=False, message=str(exc))

    async def run_query(self, sql: str, *, limit: int = 1000) -> QueryResult:
        return await asyncio.to_thread(self._run_query_sync, sql, limit)

    def _run_query_sync(self, sql: str, limit: int) -> QueryResult:
        import snowflake.connector

        conn = snowflake.connector.connect(
            account=self._config["account"],
            user=self._config["user"],
            password=self._config["password"],
            warehouse=self._config.get("warehouse"),
            database=self._config.get("database"),
            schema=self._config.get("schema"),
        )
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            rows = [list(r) for r in cursor.fetchmany(limit)]
        finally:
            conn.close()
        return QueryResult(columns=columns, rows=rows)
