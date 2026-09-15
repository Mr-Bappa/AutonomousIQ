"""Ingestion API -- saved live-DB connectors (D-3/D-13/D-14). See
libs/models/chat_and_connectors.py's flag: `config` is plain JSONB, not
yet backed by Secret Manager. Also see libs/connectors/*.py: each
adapter needs its actual DB driver installed to really connect (asyncpg,
aiomysql, pyodbc, snowflake-connector-python) -- none of those are
required as core dependencies, so /test will report a clear "driver not
installed" message rather than crashing if they're absent.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, CurrentUserDep
from libs.connectors.registry import get_connector
from libs.db import get_db_session
from libs.exceptions import NotFoundError
from libs.models import ConnectorConfig, ConnectorType

router = APIRouter(prefix="/v1/ingestion/connectors", tags=["ingestion"])


class CreateConnectorRequest(BaseModel):
    connector_type: ConnectorType
    name: str
    config: dict


class ConnectorResponse(BaseModel):
    id: uuid.UUID
    connector_type: str
    name: str

    model_config = {"from_attributes": True}


class TestConnectionResponse(BaseModel):
    ok: bool
    message: str


@router.post("", response_model=ConnectorResponse)
async def create_connector(
    body: CreateConnectorRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> ConnectorConfig:
    connector = ConnectorConfig(
        tenant_id=current_user.tenant_id,
        connector_type=body.connector_type,
        name=body.name,
        config=body.config,
        created_by=current_user.user_id,
    )
    session.add(connector)
    await session.commit()
    await session.refresh(connector)
    return connector


@router.get("", response_model=list[ConnectorResponse])
async def list_connectors(
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[ConnectorConfig]:
    result = await session.scalars(
        select(ConnectorConfig).where(ConnectorConfig.tenant_id == current_user.tenant_id)
    )
    return list(result)


@router.post("/{connector_id}/test", response_model=TestConnectionResponse)
async def test_connector(
    connector_id: uuid.UUID,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> TestConnectionResponse:
    connector_config = await session.get(ConnectorConfig, connector_id)
    if connector_config is None or connector_config.tenant_id != current_user.tenant_id:
        raise NotFoundError(f"No connector {connector_id} in this tenant.")

    connector = get_connector(connector_config.connector_type, connector_config.config)
    result = await connector.test_connection()
    return TestConnectionResponse(ok=result.ok, message=result.message)
