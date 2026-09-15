"""Documents API -- upload (tenant-global per PRD) + list. Feeds
apps/planner/rag.py's demo keyword search via `content_text`.

**Simplification flagged:** real text extraction (PDF/DOCX parsing,
OCR for scans) is out of scope for this pass -- `content_text` is
populated directly from the uploaded bytes decoded as UTF-8 text, so
only plain-text uploads produce searchable content today. A PDF/DOCX
upload will still store successfully (storage_pointer + format are
always set) but `content_text` will be null and it won't surface in RAG
search until real extraction is added.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import CurrentUser, CurrentUserDep
from libs.db import get_db_session
from libs.gcp.storage import upload_bytes
from libs.models import Document

router = APIRouter(prefix="/v1/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: uuid.UUID
    name: str
    format: str
    has_extracted_text: bool

    model_config = {"from_attributes": True}


@router.post("", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile,
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    content = await file.read()
    storage_pointer = upload_bytes(
        content, filename=file.filename or "upload", tenant_id=str(current_user.tenant_id)
    )

    format_ = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "unknown"
    content_text: str | None = None
    if format_ in ("txt", "md", "csv", "json"):
        try:
            content_text = content.decode("utf-8")
        except UnicodeDecodeError:
            content_text = None

    doc = Document(
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.user_id,
        storage_pointer=storage_pointer,
        format=format_,
        name=file.filename or "untitled",
        content_text=content_text,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return DocumentResponse(
        id=doc.id, name=doc.name, format=doc.format, has_extracted_text=doc.content_text is not None
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_db_session),
) -> list[DocumentResponse]:
    result = await session.scalars(select(Document).where(Document.tenant_id == current_user.tenant_id))
    return [
        DocumentResponse(id=d.id, name=d.name, format=d.format, has_extracted_text=d.content_text is not None)
        for d in result
    ]
