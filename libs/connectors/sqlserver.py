"""SQL Server connector (D-3). Demo-level, uses pyodbc (sync driver --
run in a thread via asyncio.to_thread since there's no mature async ODBC
driver). Requires the Microsoft ODBC Driver for SQL Server to be
installed on the host/container running this, which is an infra concern
not handled here.
"""

from __future__ import annotations

import asyncio
from typing import Any

from libs.connectors.base import ConnectionTestResult, QueryResult


class SQLServerConnector:
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    def _connection_string(self) -> str:
        c = self._config
        return (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={c['host']},{c.get('port', 1433)};"
            f"DATABASE={c['database']};UID={c['user']};PWD={c['password']};"
            "Encrypt=yes;TrustServerCertificate=yes;"
        )

    async def test_connection(self) -> ConnectionTestResult:
        return await asyncio.to_thread(self._test_connection_sync)

    def _test_connection_sync(self) -> ConnectionTestResult:
        try:
            import pyodbc
        except ImportError:
            return ConnectionTestResult(ok=False, message="pyodbc is not installed in this environment.")
        try:
            conn = pyodbc.connect(self._connection_string(), timeout=5)
            conn.close()
            return ConnectionTestResult(ok=True, message="Connected successfully.")
        except Exception as exc:  # noqa: BLE001
            return ConnectionTestResult(ok=False, message=str(exc))

    async def run_query(self, sql: str, *, limit: int = 1000) -> QueryResult:
        return await asyncio.to_thread(self._run_query_sync, sql, limit)

    def _run_query_sync(self, sql: str, limit: int) -> QueryResult:
        import pyodbc

        conn = pyodbc.connect(self._connection_string())
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            rows = [list(r) for r in cursor.fetchmany(limit)]
        finally:
            conn.close()
        return QueryResult(columns=columns, rows=rows)
