from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _connect_args(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


settings = get_settings()
engine = create_engine(settings.database_url, future=True, connect_args=_connect_args(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_engine(database_url: str) -> None:
    """Used by tests to point SQLAlchemy at an isolated database."""
    global engine, SessionLocal
    engine.dispose()
    engine = create_engine(database_url, future=True, connect_args=_connect_args(database_url))
    SessionLocal.configure(bind=engine)
