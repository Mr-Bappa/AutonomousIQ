"""Chat-planner endpoint -- the HTTP surface for apps/planner/planner.py.
One route: post a message in a session, get back the assistant's turn
(text + any tool results, including pending_approval indicators)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, CurrentUserDep
from apps.planner.planner import run_chat_turn
from libs.db import get_db_session
from libs.models import ChatMessage

router = APIRouter(prefix="/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: uuid.UUID | None = None
    message: str
    dataset_id: uuid.UUID | None = None
    tracker_id: uuid.UUID | None = None


class ChatTurnResponse(BaseModel):
    session_id: uuid.UUID
    message_id: str
    intent: str
    text: str
    tool_results: list[dict]


class ChatHistoryMessage(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    tool_calls: list | None

    model_config = {"from_attributes": True}


@router.post("", response_model=ChatTurnResponse)
async def send_message(
    body: ChatRequest,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> ChatTurnResponse:
    chat_session_id = body.session_id or uuid.uuid4()
    context = {}
    if body.dataset_id:
        context["dataset_id"] = str(body.dataset_id)
    if body.tracker_id:
        context["tracker_id"] = str(body.tracker_id)

    result = await run_chat_turn(
        session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        chat_session_id=chat_session_id,
        message=body.message,
        context=context,
    )
    return ChatTurnResponse(session_id=chat_session_id, **result)


@router.get("/{session_id}/history", response_model=list[ChatHistoryMessage])
async def get_history(
    session_id: uuid.UUID,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatMessage]:
    result = await session.scalars(
        select(ChatMessage)
        .where(
            ChatMessage.session_id == session_id,
            ChatMessage.tenant_id == current_user.tenant_id,
        )
        .order_by(ChatMessage.created_at)
    )
    return list(result)
