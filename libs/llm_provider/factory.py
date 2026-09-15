"""Picks the active LLMProvider from env config -- the one place that
needs to change to swap providers, per D-10's adapter design."""

from __future__ import annotations

import os

from libs.llm_provider.base import LLMProvider
from libs.llm_provider.naive import NaiveKeywordProvider
from libs.llm_provider.vertex import VertexAIProvider


def get_llm_provider() -> LLMProvider:
    provider_name = os.environ.get("LLM_PROVIDER", "naive").lower()
    if provider_name == "vertex":
        return VertexAIProvider()
    return NaiveKeywordProvider()
