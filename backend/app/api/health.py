from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.database import session as db_session

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    settings = get_settings()
    database = "ok"
    try:
        with db_session.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        database = f"error: {exc.__class__.__name__}"
    status = "ok" if database == "ok" else "degraded"
    return {
        "status": status,
        "app": settings.app_name,
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
        "database": database,
    }
