"""Vertex AI implementation of the LLMProvider Protocol (libs/llm_provider/base.py).

D-10 locked a model-agnostic adapter *interface* with a single provider
implementation for Phase 0. This is that implementation, using Google
Cloud's Vertex AI (Gemini) rather than calling Anthropic/OpenAI directly
-- since the user wants everything running through GCP/Vertex.

Demo-level tool-calling: Vertex's Gemini function-calling API is used
directly (native tool-call support, not a hand-rolled JSON-parsing
scheme), but there's no retry/backoff policy, no streaming, and no
token-budget management -- a single non-streaming `generate_content`
call per turn.
"""

from __future__ import annotations

from typing import Any

from libs.gcp.config import GCP_PROJECT_ID, GCP_REGION, VERTEX_MODEL
from libs.llm_provider.base import LLMResponse, ToolCallRequest


class VertexAIProvider:
    """Satisfies the LLMProvider Protocol via `vertexai.generative_models`."""

    def __init__(self, *, project: str | None = None, region: str | None = None, model: str | None = None) -> None:
        self._project = project or GCP_PROJECT_ID
        self._region = region or GCP_REGION
        self._model_name = model or VERTEX_MODEL
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        import vertexai  # local import: optional dependency, only needed if Vertex is actually used

        vertexai.init(project=self._project, location=self._region)
        self._initialized = True

    async def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        available_tools: list[dict[str, Any]],
    ) -> LLMResponse:
        self._ensure_initialized()

        from vertexai.generative_models import (
            Content,
            FunctionDeclaration,
            GenerativeModel,
            Part,
            Tool,
        )

        tools = None
        if available_tools:
            declarations = [
                FunctionDeclaration(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    parameters=tool.get("parameters", {"type": "object", "properties": {}}),
                )
                for tool in available_tools
            ]
            tools = [Tool(function_declarations=declarations)]

        model = GenerativeModel(self._model_name, system_instruction=system_prompt, tools=tools)

        history = [
            Content(role="user" if m["role"] == "user" else "model", parts=[Part.from_text(m["content"])])
            for m in messages
        ]

        response = await model.generate_content_async(history)

        text: str | None = None
        tool_calls: list[ToolCallRequest] = []
        for part in response.candidates[0].content.parts:
            if getattr(part, "text", None):
                text = (text or "") + part.text
            function_call = getattr(part, "function_call", None)
            if function_call is not None:
                tool_calls.append(
                    ToolCallRequest(
                        tool_name=function_call.name,
                        arguments=dict(function_call.args),
                    )
                )

        return LLMResponse(text=text, tool_calls=tool_calls, raw=response)
