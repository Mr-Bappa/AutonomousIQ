"""Model-agnostic planner adapter interface (Architecture Decision Log D-10).

Only a thin seam is defined for Phase 0 — a single provider is implemented
behind it. Adding or swapping a provider later means writing a new adapter
against this Protocol, not modifying the planner itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCallRequest:
    """A single tool call the planner wants to make (e.g. sql_query_tool)."""

    tool_name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Normalized response shape returned by any LLMProvider implementation.

    Args:
        text: Plain-text portion of the model's response, if any.
        tool_calls: Structured tool calls the model wants to make, if any.
        raw: The provider's raw response, kept for debugging/logging only —
            callers should not depend on its shape.
    """

    text: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    raw: Any = None


class LLMProvider(Protocol):
    """Adapter interface every LLM provider implementation must satisfy."""

    async def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        available_tools: list[dict[str, Any]],
    ) -> LLMResponse:
        """Request a completion from the underlying model.

        Args:
            system_prompt: The planner's system prompt.
            messages: Conversation history, each a {"role": ..., "content": ...} dict.
            available_tools: Tool schemas the model may call (sql_query_tool,
                tracker_query_tool, doc_search_tool, chart_tool).

        Returns:
            A normalized LLMResponse.
        """
        ...
