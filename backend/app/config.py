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

    # ── LLM layer (Milestone 5) ───────────────────────────────────────────
    # Provider selection: "auto" uses Anthropic when a key + SDK are present,
    # otherwise the deterministic offline provider (grounded by construction).
    # Force one with "offline" or "anthropic".
    llm_provider: str = "auto"
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    # A drafted answer below this confidence is never auto-filled — it is routed
    # to the human as a suggestion instead.
    min_answer_confidence: float = 75.0


settings = Settings()
