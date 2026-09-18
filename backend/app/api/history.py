import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database.models import Document, EvaluationRun, QueryRecord, Report, SearchEvent, User
from app.database.session import get_db
from app.schemas.common import DashboardMetrics, HistoryItem

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history", response_model=list[HistoryItem])
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(QueryRecord)
        .filter(QueryRecord.user_id == user.id)
        .order_by(QueryRecord.created_at.desc())
        .limit(100)
        .all()
    )
    items: list[HistoryItem] = []
    for q in rows:
        resp = q.response
        tools = json.loads(resp.tools_used_json) if resp else []
        sources = [s.document_name for s in (resp.sources if resp else [])]
        items.append(
            HistoryItem(
                id=q.id,
                question=q.question,
                query_type=q.query_type,
                created_at=q.created_at.isoformat() if q.created_at else None,
                answer_summary=(resp.answer[:240] if resp else None),
                tools_used=tools,
                sources=list(dict.fromkeys(sources)),
                confidence=resp.confidence if resp else None,
            )
        )
    return items


@router.get("/history/{query_id}")
def history_detail(query_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(QueryRecord).filter(QueryRecord.id == query_id, QueryRecord.user_id == user.id).first()
    if not q:
        raise HTTPException(status_code=404, detail="History item not found")
    resp = q.response
    return {
        "id": q.id,
        "question": q.question,
        "query_type": q.query_type,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "answer": resp.answer if resp else None,
        "confidence": resp.confidence if resp else None,
        "claims": json.loads(resp.claims_json) if resp else [],
        "uncertainty": json.loads(resp.uncertainty_json) if resp else [],
        "tools_used": json.loads(resp.tools_used_json) if resp else [],
        "latency": json.loads(resp.latency_json) if resp else {},
        "verification": json.loads(resp.verification_json) if resp else {},
        "sources": [
            {
                "citation_index": s.citation_index,
                "document": s.document_name,
                "page": s.page,
                "section": s.section,
                "snippet": s.snippet,
                "score": s.score,
                "retrieval_method": s.retrieval_method,
                "chunk_id": s.chunk_id,
            }
            for s in (resp.sources if resp else [])
        ],
    }


@router.get("/dashboard", response_model=DashboardMetrics)
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    docs = db.query(Document).count()
    indexed = db.query(Document).filter(Document.status == "indexed").count()
    questions = db.query(QueryRecord).count()
    reports = db.query(Report).count()
    searches = db.query(SearchEvent).count()
    evals = db.query(EvaluationRun).count()
    recent = (
        db.query(QueryRecord)
        .order_by(QueryRecord.created_at.desc())
        .limit(8)
        .all()
    )
    return DashboardMetrics(
        documents=docs,
        indexed_documents=indexed,
        questions=questions,
        reports=reports,
        searches=searches,
        evaluation_runs=evals,
        recent_activity=[
            {
                "id": q.id,
                "question": q.question,
                "type": q.query_type,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in recent
        ],
    )
