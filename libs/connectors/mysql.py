"""MySQL connector (D-3). Demo-level, mirrors postgres.py's shape using
aiomysql. Same caveats: no pooling, credentials assumed already secured
by IP allowlisting/SSH tunnel at the infra layer.
"""

from __future__ import annotations

from typing import Any

from libs.connectors.base import ConnectionTestResult, QueryResult


class MySQLConnector:
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    async def test_connection(self) -> ConnectionTestResult:
        try:
            import aiomysql
        except ImportError:
            return ConnectionTestResult(ok=False, message="aiomysql is not installed in this environment.")

        try:
            conn = await aiomysql.connect(
                host=self._config["host"],
                port=self._config.get("port", 3306),
                db=self._config["database"],
                user=self._config["user"],
                password=self._config["password"],
                connect_timeout=5,
            )
            conn.close()
            return ConnectionTestResult(ok=True, message="Connected successfully.")
        except Exception as exc:  # noqa: BLE001
            return ConnectionTestResult(ok=False, message=str(exc))

    async def run_query(self, sql: str, *, limit: int = 1000) -> QueryResult:
        import aiomysql

        conn = await aiomysql.connect(
            host=self._config["host"],
            port=self._config.get("port", 3306),
            db=self._config["database"],
            user=self._config["user"],
            password=self._config["password"],
        )
        try:
            async with conn.cursor() as cur:
                await cur.execute(sql)
                rows = list(await cur.fetchmany(limit))
                columns = [d[0] for d in cur.description] if cur.description else []
        finally:
            conn.close()
        return QueryResult(columns=columns, rows=[list(r) for r in rows])
