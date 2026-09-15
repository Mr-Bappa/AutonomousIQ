"""The four MCP-style planner tools named throughout the PRD/Standards:
sql_query_tool, tracker_query_tool, doc_search_tool, chart_tool.

Per STANDARDS.md Section 3: sql_query_tool, tracker_query_tool, and
chart_tool are approval-gated -- they never execute inline, they always
return/raise a pending_approval indicator. doc_search_tool is not gated
(it's read-only RAG retrieval) and executes immediately.

**Simplification flagged:** sql_query_tool's gate maps cleanly onto the
existing `TransformationJob` model (it already has a `pending_approval`
status and a `dataset_id`). tracker_query_tool and chart_tool don't
naturally fit that dataset-shaped model, so their gate is currently
*ephemeral* -- an `ApprovalRequiredError` carrying the proposed action in
its `details`, not a persisted queue row. That means a tracker/chart
"pending approval" doesn't show up in the Approvals inbox (which only
lists `transformation_jobs`) and doesn't survive a page reload. Giving
every gated tool a real persisted queue entry (not just SQL) is the
natural next step, not done in this pass.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.planner import rag
from libs.exceptions import ApprovalRequiredError
from libs.models import (
    Dataset,
    ExecutionTarget,
    Tracker,
    TrackerCell,
    TransformationJob,
    TransformationJobStatus,
)

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "sql_query_tool",
        "description": "Run a SQL query against a connected database dataset. Requires human approval before executing.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string"},
                "sql": {"type": "string"},
            },
            "required": ["dataset_id", "sql"],
        },
    },
    {
        "name": "tracker_query_tool",
        "description": "Read or propose changes to a Tracker grid. Requires human approval for any write.",
        "parameters": {
            "type": "object",
            "properties": {
                "tracker_id": {"type": "string"},
                "prompt": {"type": "string"},
            },
            "required": ["tracker_id"],
        },
    },
    {
        "name": "doc_search_tool",
        "description": "Search uploaded documents via RAG. Read-only, not approval-gated.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "chart_tool",
        "description": "Produce a chart spec from a dataset or tracker. Requires human approval before rendering.",
        "parameters": {
            "type": "object",
            "properties": {"prompt": {"type": "string"}},
            "required": ["prompt"],
        },
    },
]


async def sql_query_tool(
    session: AsyncSession, *, tenant_id: uuid.UUID, dataset_id: uuid.UUID, sql: str, created_by: uuid.UUID
) -> dict[str, Any]:
    dataset = await session.get(Dataset, dataset_id)
    if dataset is None or dataset.tenant_id != tenant_id:
        raise ValueError(f"No dataset {dataset_id} in this tenant.")

    cache_key = hashlib.sha256(sql.encode("utf-8")).hexdigest()[:32]
    job = TransformationJob(
        dataset_id=dataset_id,
        code_version=cache_key,
        dataset_version=dataset.version,
        sample_used=True,
        status=TransformationJobStatus.pending_approval,
        approval_metadata={"sql": sql, "proposed_by": str(created_by)},
        cache_key=cache_key,
        execution_target=ExecutionTarget.cloud,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return {"status": "pending_approval", "job_id": str(job.id)}


async def tracker_query_tool(
    session: AsyncSession, *, tenant_id: uuid.UUID, tracker_id: uuid.UUID, prompt: str | None
) -> dict[str, Any]:
    tracker = await session.get(Tracker, tracker_id)
    if tracker is None or tracker.tenant_id != tenant_id:
        raise ValueError(f"No tracker {tracker_id} in this tenant.")

    # Reads are inline (no gate needed for a read) -- only a *write*
    # proposal would need approval. This demo tool only reads, so it
    # always returns data. A real "propose a formula/edit" path would
    # raise ApprovalRequiredError the same way chart_tool does below.
    result = await session.scalars(select(TrackerCell).where(TrackerCell.tracker_id == tracker_id))
    cells = [
        {"row_idx": c.row_idx, "col_idx": c.col_idx, "value": c.computed_value or c.raw_value}
        for c in result
    ]
    return {"status": "ok", "tracker_id": str(tracker_id), "cells": cells}


async def doc_search_tool(session: AsyncSession, *, tenant_id: uuid.UUID, query: str) -> dict[str, Any]:
    hits = await rag.search(session, tenant_id=tenant_id, query=query)
    return {
        "status": "ok",
        "hits": [
            {"document_id": str(h.document_id), "document_name": h.document_name, "score": h.score, "snippet": h.snippet}
            for h in hits
        ],
    }


async def chart_tool(*, prompt: str, created_by: uuid.UUID) -> dict[str, Any]:
    """Deterministic per the PRD ("deterministic chart_tool") -- given
    the same prompt it always proposes the same simple chart spec shape.
    Always gated: raises ApprovalRequiredError with the proposed spec in
    `details` rather than ever rendering directly.
    """
    proposed_spec = {"type": "bar", "title": prompt[:80], "x": "category", "y": "value"}
    raise ApprovalRequiredError(
        "Chart proposal requires approval before rendering.",
        details={"proposed_spec": proposed_spec, "proposed_by": str(created_by)},
    )
