import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database.models import Document, DocumentChunk, User
from app.database.session import get_db
from app.documents.ingestion import ingest_upload
from app.schemas.common import DocumentOut

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentOut)
def upload_document(
    file: UploadFile = File(...),
    department: Optional[str] = Form(None),
    doc_type: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    doc = ingest_upload(db, file, department, doc_type, year)
    return _out(doc)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    q: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Document).order_by(Document.created_at.desc())
    if status:
        query = query.filter(Document.status == status)
    docs = query.all()
    if q:
        needle = q.lower()
        docs = [d for d in docs if needle in d.title.lower() or needle in d.original_name.lower()]
    return [_out(d) for d in docs]


@router.get("/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    return {
        **_out(doc).model_dump(),
        "chunks": [
            {"id": c.id, "index": c.chunk_index, "page": c.page, "section": c.section, "content": c.content[:500], "token_count": c.token_count}
            for c in chunks
        ],
        "metadata": json.loads(doc.metadata_json or "{}"),
    }


@router.delete("/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    from pathlib import Path

    from app.core.config import get_settings

    stored = Path(get_settings().upload_dir) / doc.stored_name
    db.delete(doc)
    db.commit()
    if stored.exists() and stored.is_file():
        stored.unlink()
    return {"ok": True}


def _out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        title=doc.title,
        original_name=doc.original_name,
        status=doc.status,
        department=doc.department,
        doc_type=doc.doc_type,
        year=doc.year,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        ingested_ms=doc.ingested_ms,
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )
