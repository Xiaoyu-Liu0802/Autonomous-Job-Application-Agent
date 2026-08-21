"""Application settings, overridable via environment variables or a .env file."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOBPILOT_", env_file=".env", extra="ignore")

    # SQLite by default for zero-setup local dev; point at Postgres in prod, e.g.
    #   JOBPILOT_DATABASE_URL=postgresql+psycopg://user:pass@host/jobpilot
    database_url: str = "sqlite:///jobpilot.db"

    # Comma-free list is fine here; the frontend dev server default.
    cors_origins: list[str] = ["http://localhost:3000"]

    # Seed sample data on first startup if the DB is empty.
    seed_on_startup: bool = True


settings = Settings()
