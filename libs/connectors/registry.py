"""Maps ConnectorType -> connector adapter class. The one place that
needs updating if a new connector type is added."""

from __future__ import annotations

from typing import Any

from libs.connectors.base import Connector
from libs.connectors.mysql import MySQLConnector
from libs.connectors.postgres import PostgresConnector
from libs.connectors.snowflake import SnowflakeConnector
from libs.connectors.sqlserver import SQLServerConnector
from libs.models import ConnectorType

_REGISTRY: dict[ConnectorType, type] = {
    ConnectorType.postgres: PostgresConnector,
    ConnectorType.mysql: MySQLConnector,
    ConnectorType.sqlserver: SQLServerConnector,
    ConnectorType.snowflake: SnowflakeConnector,
}


def get_connector(connector_type: ConnectorType, config: dict[str, Any]) -> Connector:
    connector_class = _REGISTRY[connector_type]
    return connector_class(config)
