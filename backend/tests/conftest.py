import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("SECRET_KEY", "test-secret")

from app.core.config import get_settings

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    get_settings.cache_clear()
    from app.core.config import get_settings as gs

    gs.cache_clear()
    from app.database.session import reset_engine
    from app.database.models import Base
    from app.database.seed import seed_if_empty

    url = f"sqlite:///{db_path}"
    reset_engine(url)
    from app.database import session as session_mod

    Base.metadata.create_all(bind=session_mod.engine)
    db = session_mod.SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    settings = get_settings()
    res = client.post("/api/auth/login", json={"email": settings.demo_email, "password": settings.demo_password})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
