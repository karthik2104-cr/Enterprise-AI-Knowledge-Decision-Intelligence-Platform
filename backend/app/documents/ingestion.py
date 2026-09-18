from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import Document, DocumentChunk
from app.documents.chunking import chunk_pages
from app.documents.extractors import SUPPORTED, extract_text
from app.providers.embeddings import get_embedding_provider


def _safe_filename(name: str) -> str:
    keep = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
    return keep[:180] or "document"


def ingest_upload(db: Session, file: UploadFile, department: str | None, doc_type: str | None, year: int | None) -> Document:
    settings = get_settings()
    original = file.filename or "untitled.txt"
    suffix = Path(original).suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(SUPPORTED)}")

    payload = file.file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(payload) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_mb} MB limit.")
    if not payload:
        raise HTTPException(status_code=400, detail="Empty file.")

    checksum = hashlib.sha256(payload).hexdigest()
    existing = db.query(Document).filter(Document.checksum == checksum).first()
    if existing:
        raise HTTPException(status_code=409, detail="Duplicate document already exists.")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{checksum[:12]}_{_safe_filename(original)}"
    dest = upload_dir / stored
    dest.write_bytes(payload)

    doc = Document(
        title=Path(original).stem.replace("_", " "),
        original_name=original,
        stored_name=stored,
        content_type=SUPPORTED[suffix],
        status="processing",
        department=department,
        doc_type=doc_type,
        year=year,
        checksum=checksum,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    started = time.perf_counter()
    try:
        pages = extract_text(dest)
        chunks = chunk_pages(pages)
        if not chunks:
            raise HTTPException(status_code=400, detail="No text chunks could be produced from this file.")
        embedder = get_embedding_provider()
        for chunk in chunks:
            vector = embedder.embed(chunk["content"])
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    page=chunk["page"],
                    section=chunk["section"],
                    embedding_json=json.dumps(vector),
                    token_count=chunk["token_count"],
                    metadata_json=json.dumps(
                        {
                            "document_name": doc.title,
                            "department": department,
                            "doc_type": doc_type,
                            "year": year,
                        }
                    ),
                )
            )
        doc.chunk_count = len(chunks)
        doc.status = "indexed"
        doc.ingested_ms = int((time.perf_counter() - started) * 1000)
        db.commit()
        db.refresh(doc)
        return doc
    except HTTPException as exc:
        doc.status = "failed"
        doc.error_message = str(exc.detail)
        db.commit()
        raise
    except Exception as exc:
        doc.status = "failed"
        doc.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=400, detail=f"Ingestion failed: {exc}") from exc


def ingest_text_document(
    db: Session,
    title: str,
    text: str,
    original_name: str,
    department: str | None,
    doc_type: str | None,
    year: int | None,
) -> Document:
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    existing = db.query(Document).filter(Document.checksum == checksum).first()
    if existing:
        return existing
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{checksum[:12]}_{_safe_filename(original_name)}"
    dest = upload_dir / stored
    dest.write_text(text, encoding="utf-8")
    doc = Document(
        title=title,
        original_name=original_name,
        stored_name=stored,
        content_type="text/markdown",
        status="processing",
        department=department,
        doc_type=doc_type,
        year=year,
        checksum=checksum,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    started = time.perf_counter()
    chunks = chunk_pages([(1, text, title)])
    embedder = get_embedding_provider()
    for chunk in chunks:
        db.add(
            DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                page=chunk["page"],
                section=chunk["section"],
                embedding_json=json.dumps(embedder.embed(chunk["content"])),
                token_count=chunk["token_count"],
                metadata_json=json.dumps({"document_name": title, "department": department, "doc_type": doc_type, "year": year}),
            )
        )
    doc.chunk_count = len(chunks)
    doc.status = "indexed"
    doc.ingested_ms = int((time.perf_counter() - started) * 1000)
    db.commit()
    db.refresh(doc)
    return doc
