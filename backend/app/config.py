"""Application settings, loaded from environment variables (see .env.example)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ROPPO_", extra="ignore")

    app_name: str = "Roppo"
    environment: str = "development"

    # Database: SQLite for zero-setup local development, PostgreSQL in Docker/production.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'roppo.db'}"

    # Auth
    jwt_secret: str = "dev-only-insecure-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 12

    # Uploads are stored privately on disk and are never served as static files.
    storage_dir: Path = BACKEND_DIR / "storage"
    max_upload_mb: int = 5

    # CORS origins for the React dev server / frontend container.
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:8080"])

    # LLM (optional). The API key is read by the Anthropic SDK from ANTHROPIC_API_KEY.
    llm_enabled: bool = True
    llm_model: str = "claude-opus-5-5"
    llm_effort: str = "medium"

    # One-click demo accounts pre-filled with a fictional resume (useful for presentations).
    demo_mode: bool = True

    # Built React app to serve at "/" (single-service deployment). Ignored if the folder doesn't exist.
    frontend_dist: Path = BACKEND_DIR.parent / "frontend" / "dist"

    # Seed illustrative sample jobs on first start (clearly labelled in the UI).
    seed_sample_jobs: bool = True

    # Live job sources: comma-separated public board tokens for official ATS job-board APIs.
    greenhouse_boards: str = ""
    lever_companies: str = ""

    # Jobs not re-checked within this window are flagged as stale.
    freshness_days: int = 14


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.database_url.strip():  # blank env var → local SQLite
        settings.database_url = Settings.model_fields["database_url"].default
    url = settings.database_url
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            settings.database_url = "postgresql+psycopg://" + url[len(prefix):]
    return settings
