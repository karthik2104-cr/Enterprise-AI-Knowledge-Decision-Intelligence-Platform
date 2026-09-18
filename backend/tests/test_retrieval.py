from app.database.models import Document, DocumentChunk, QueryRecord, Report, ResponseRecord, Source
from app.database.session import SessionLocal
from app.retrieval.service import hybrid_search, keyword_search, rerank, semantic_search


def test_keyword_search():
    db = SessionLocal()
    try:
        hits = keyword_search(db, "annual leave policy")
        assert hits
        assert any("leave" in h.document_name.lower() or "leave" in h.content.lower() for h in hits)
    finally:
        db.close()


def test_semantic_search():
    db = SessionLocal()
    try:
        hits = semantic_search(db, "paid time off for employees")
        assert hits
    finally:
        db.close()


def test_hybrid_search():
    db = SessionLocal()
    try:
        hits = hybrid_search(db, "Q3 revenue")
        assert hits
        assert any("q3" in h.document_name.lower() or "revenue" in h.content.lower() for h in hits)
    finally:
        db.close()


def test_metadata_filter():
    db = SessionLocal()
    try:
        hits = keyword_search(db, "policy", filters={"department": "people"})
        assert hits
        assert all(h.department == "people" for h in hits)
    finally:
        db.close()


def test_reranking():
    db = SessionLocal()
    try:
        hits = hybrid_search(db, "compliance bribery gifts")
        ranked = rerank("compliance bribery gifts", hits)
        assert ranked
        assert ranked[0].score >= ranked[-1].score
    finally:
        db.close()


def test_document_relationships():
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.title == "Leave Policy").first()
        assert doc is not None
        assert doc.chunks
        assert all(c.document_id == doc.id for c in doc.chunks)
    finally:
        db.close()
