"""A dependency-free LLMProvider implementation used as the default so
the whole chat-planner feature works out of the box with zero GCP setup
-- D-10's model-agnostic adapter design means swapping this for
VertexAIProvider (or any other provider) later is a one-line config
change, not a rewrite.

This is intentionally dumb: a few keyword rules decide which tool (if
any) to call, and canned text otherwise. It exists to make the rest of
the planner/tool-routing/approval-gate plumbing exercisable end-to-end
without needing real Vertex AI credentials -- not a stand-in for actual
model quality.
"""

from __future__ import annotations

from typing import Any

from libs.llm_provider.base import LLMResponse, ToolCallRequest


class NaiveKeywordProvider:
    """Satisfies the LLMProvider Protocol with simple keyword rules."""

    async def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        available_tools: list[dict[str, Any]],
    ) -> LLMResponse:
        last_user_message = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        lowered = last_user_message.lower()
        available_names = {t["name"] for t in available_tools}

        if "chart" in lowered or "graph" in lowered or "plot" in lowered:
            if "chart_tool" in available_names:
                return LLMResponse(
                    text="I'll put together a chart for that -- it needs approval before it runs.",
                    tool_calls=[ToolCallRequest(tool_name="chart_tool", arguments={"prompt": last_user_message})],
                )

        if any(kw in lowered for kw in ("tracker", "cell", "formula", "spreadsheet")):
            if "tracker_query_tool" in available_names:
                return LLMResponse(
                    text="Let me check the Tracker for that.",
                    tool_calls=[ToolCallRequest(tool_name="tracker_query_tool", arguments={"prompt": last_user_message})],
                )

        if any(kw in lowered for kw in ("select", "sql", "query", "database", "rows", "table")):
            if "sql_query_tool" in available_names:
                return LLMResponse(
                    text="That looks like a data query -- I'll draft it, but it needs approval before running.",
                    tool_calls=[ToolCallRequest(tool_name="sql_query_tool", arguments={"prompt": last_user_message})],
                )

        if any(kw in lowered for kw in ("doc", "policy", "sop", "procedure", "find")):
            if "doc_search_tool" in available_names:
                return LLMResponse(
                    text="Searching your uploaded documents for that.",
                    tool_calls=[ToolCallRequest(tool_name="doc_search_tool", arguments={"prompt": last_user_message})],
                )

        return LLMResponse(
            text=(
                "I'm running in demo mode (no Vertex AI configured), so I can only route obvious "
                "keywords to a tool. Try mentioning \"chart\", \"tracker\", \"query\"/\"sql\", or "
                "\"document\" to see a tool call, or configure LLM_PROVIDER=vertex for real "
                "reasoning."
            ),
            tool_calls=[],
        )
