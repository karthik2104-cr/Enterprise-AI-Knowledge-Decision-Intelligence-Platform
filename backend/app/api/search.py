from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database.models import SearchEvent, User
from app.database.session import get_db
from app.retrieval.service import retrieve, score_explanation
from app.schemas.common import SearchHit, SearchRequest

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=list[SearchHit])
def search(payload: SearchRequest, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    filters = {
        "document_type": payload.document_type,
        "department": payload.department,
        "year": payload.year,
        "section": payload.section,
    }
    filters = {k: v for k, v in filters.items() if v not in (None, "")}
    hits = retrieve(db, payload.query, filters)[: payload.top_k]
    db.add(SearchEvent(query_text=payload.query, result_count=len(hits)))
    db.commit()
    return [
        SearchHit(
            document_id=h.document_id,
            document_name=h.document_name,
            chunk_id=h.chunk_id,
            page=h.page,
            section=h.section,
            snippet=h.snippet(),
            score=h.score,
            retrieval_method=h.retrieval_method,
            score_explanation=score_explanation(h.retrieval_method, h.score),
        )
        for h in hits
    ]
