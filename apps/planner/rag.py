"""Demo RAG: naive keyword search over Document.content_text.

PRD's AI layer routes doc_search_tool through RAG restricted to
Documents (not Datasets/Trackers). A real implementation would chunk
each document, embed the chunks (e.g. via Vertex AI's text-embedding
models) into a vector store, and retrieve by cosine similarity. This is
explicitly the simple/demo version requested for this pass: score by
overlapping words between the query and each document's full text, no
chunking, no embeddings, no vector index at all.

Swapping this for real embeddings later means changing `search()`'s
body, not any of its callers (apps/planner/tools.py's doc_search_tool).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.models import Document

_WORD_RE = re.compile(r"[a-zA-Z0-9]+")


@dataclass
class RagHit:
    document_id: uuid.UUID
    document_name: str
    score: float
    snippet: str


def _words(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text)}


def _snippet(content: str, query_words: set[str], *, window: int = 160) -> str:
    lowered = content.lower()
    for word in query_words:
        idx = lowered.find(word)
        if idx != -1:
            start = max(0, idx - window // 2)
            return content[start : start + window].strip()
    return content[:window].strip()


async def search(session: AsyncSession, *, tenant_id: uuid.UUID, query: str, top_k: int = 3) -> list[RagHit]:
    query_words = _words(query)
    if not query_words:
        return []

    result = await session.scalars(
        select(Document).where(Document.tenant_id == tenant_id, Document.content_text.isnot(None))
    )

    scored: list[RagHit] = []
    for doc in result:
        doc_words = _words(doc.content_text or "")
        overlap = query_words & doc_words
        if not overlap:
            continue
        score = len(overlap) / len(query_words)
        scored.append(
            RagHit(
                document_id=doc.id,
                document_name=doc.name,
                score=score,
                snippet=_snippet(doc.content_text or "", query_words),
            )
        )

    scored.sort(key=lambda h: h.score, reverse=True)
    return scored[:top_k]
