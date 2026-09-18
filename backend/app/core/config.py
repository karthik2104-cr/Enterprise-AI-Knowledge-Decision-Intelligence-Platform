from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_DIR / ".env"), extra="ignore")

    app_name: str = "Enterprise AI Knowledge Platform"
    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 480

    database_url: str = f"sqlite:///{BACKEND_DIR / 'platform.db'}"

    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 45

    embedding_provider: str = "mock"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 256

    retrieval_top_k: int = 8
    rerank_top_k: int = 5

    max_upload_mb: int = 15
    upload_dir: str = str(BACKEND_DIR / "uploads")

    demo_email: str = "analyst@northwind-demo.com"
    demo_password: str = "DemoPass123!"
    demo_name: str = "Avery Chen"


@lru_cache
def get_settings() -> Settings:
    return Settings()
