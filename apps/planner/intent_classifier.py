"""Intent classifier -- PRD's AI layer is "intent classifier -> planner
agent -> RAG -> tool_call". This is the first step: a cheap, keyword-
based pre-filter deciding which tool schemas are even worth offering the
LLM for a given message, before the (also demo-level, see
libs/llm_provider/naive.py) planner reasons about the actual call.

Real intent classification would itself be a small trained/prompted
classifier; this is intentionally simple per this pass's brief.
"""

from __future__ import annotations

import enum
import re


class Intent(str, enum.Enum):
    sql = "sql"
    tracker = "tracker"
    document = "document"
    chart = "chart"
    general = "general"


_PATTERNS: dict[Intent, re.Pattern[str]] = {
    Intent.chart: re.compile(r"\b(chart|graph|plot|visuali[sz]e)\b", re.IGNORECASE),
    Intent.tracker: re.compile(r"\b(tracker|cell|formula|spreadsheet|grid)\b", re.IGNORECASE),
    Intent.sql: re.compile(r"\b(sql|select|query|database|table|rows?)\b", re.IGNORECASE),
    Intent.document: re.compile(r"\b(doc(ument)?s?|policy|sop|procedure)\b", re.IGNORECASE),
}


def classify(message: str) -> Intent:
    for intent, pattern in _PATTERNS.items():
        if pattern.search(message):
            return intent
    return Intent.general
