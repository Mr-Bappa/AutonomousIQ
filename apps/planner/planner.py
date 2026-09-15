"""Planner orchestrator -- ties together intent_classifier, the active
LLMProvider (libs/llm_provider), the four tools (tools.py), and the
ChatMessage transcript. This is what apps/api/chat.py calls per turn.

PRD: "AI layer: intent classifier -> planner agent -> RAG (docs only) ->
sql_query_tool, doc_search_tool, tracker_query_tool (MCP-style) ->
deterministic chart_tool". This module is that whole pipeline for one
chat turn, kept single-agent (no sub-agent orchestration, per the PRD's
explicit Phase 0 scope line) and single-provider (D-10).

**Context, not invention:** `tracker_id`/`dataset_id` args come from
`context` (explicitly selected by the person in the chat UI), not from
the LLM inventing a UUID -- the naive provider in particular has no way
to know real ids, and even a real model shouldn't be trusted to
hallucinate a resource id for a gated action.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.planner import tools
from apps.planner.intent_classifier import Intent, classify
from libs.exceptions import ApprovalRequiredError
from libs.llm_provider import get_llm_provider
from libs.llm_provider.base import ToolCallRequest
from libs.models import ChatMessage, ChatRole

_SYSTEM_PROMPT = (
    "You are AutonomousIQ's data assistant. You can search documents, "
    "read Trackers, propose SQL queries, and propose charts. SQL "
    "queries, Tracker writes, and charts all require human approval "
    "before they take effect -- always say so when proposing one."
)

# Only offer the tool schemas relevant to the classified intent -- a
# small, cheap narrowing so the LLM (especially the naive keyword
# provider) isn't choosing between four tools every turn. doc_search_tool
# is always offered since general questions may still benefit from RAG.
_INTENT_TOOLS = {
    Intent.sql: {"sql_query_tool", "doc_search_tool"},
    Intent.tracker: {"tracker_query_tool", "doc_search_tool"},
    Intent.chart: {"chart_tool", "doc_search_tool"},
    Intent.document: {"doc_search_tool"},
    Intent.general: {"doc_search_tool"},
}


async def run_chat_turn(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    chat_session_id: uuid.UUID,
    message: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}

    user_message = ChatMessage(
        tenant_id=tenant_id, user_id=user_id, session_id=chat_session_id, role=ChatRole.user, content=message
    )
    session.add(user_message)
    await session.flush()

    history_result = await session.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == chat_session_id)
        .order_by(ChatMessage.created_at)
    )
    history = [{"role": m.role.value, "content": m.content} for m in history_result]

    intent = classify(message)
    allowed_names = _INTENT_TOOLS[intent]
    available_tools = [t for t in tools.TOOL_SCHEMAS if t["name"] in allowed_names]

    provider = get_llm_provider()
    completion = await provider.complete(
        system_prompt=_SYSTEM_PROMPT, messages=history, available_tools=available_tools
    )

    tool_results: list[dict[str, Any]] = []
    response_text = completion.text or ""

    for call in completion.tool_calls:
        result = await _dispatch(call, session=session, tenant_id=tenant_id, user_id=user_id, context=context)
        tool_results.append({"tool_name": call.tool_name, **result})
        if result.get("status") == "pending_approval":
            response_text += f"\n\n[{call.tool_name} proposed -- awaiting approval]"

    assistant_message = ChatMessage(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=chat_session_id,
        role=ChatRole.assistant,
        content=response_text or "(no response)",
        tool_calls=[{"tool_name": r["tool_name"]} for r in tool_results] or None,
    )
    session.add(assistant_message)
    await session.commit()
    await session.refresh(assistant_message)

    return {
        "message_id": str(assistant_message.id),
        "intent": intent.value,
        "text": assistant_message.content,
        "tool_results": tool_results,
    }


async def _dispatch(
    call: ToolCallRequest,
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    context: dict[str, Any],
) -> dict[str, Any]:
    try:
        if call.tool_name == "sql_query_tool":
            dataset_id = context.get("dataset_id") or call.arguments.get("dataset_id")
            sql = call.arguments.get("sql", call.arguments.get("prompt", ""))
            if not dataset_id:
                return {"status": "error", "message": "No dataset selected for this query."}
            return await tools.sql_query_tool(
                session, tenant_id=tenant_id, dataset_id=uuid.UUID(str(dataset_id)), sql=sql, created_by=user_id
            )

        if call.tool_name == "tracker_query_tool":
            tracker_id = context.get("tracker_id") or call.arguments.get("tracker_id")
            if not tracker_id:
                return {"status": "error", "message": "No tracker selected."}
            return await tools.tracker_query_tool(
                session,
                tenant_id=tenant_id,
                tracker_id=uuid.UUID(str(tracker_id)),
                prompt=call.arguments.get("prompt"),
            )

        if call.tool_name == "doc_search_tool":
            query = call.arguments.get("query", "")
            return await tools.doc_search_tool(session, tenant_id=tenant_id, query=query)

        if call.tool_name == "chart_tool":
            await tools.chart_tool(prompt=call.arguments.get("prompt", ""), created_by=user_id)

        return {"status": "error", "message": f"Unknown tool: {call.tool_name}"}

    except ApprovalRequiredError as exc:
        return {"status": "pending_approval", "message": exc.message, "details": exc.details}
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}
