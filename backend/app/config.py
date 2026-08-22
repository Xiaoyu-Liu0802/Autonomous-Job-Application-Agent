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

    # ── Bright Data (LinkedIn discovery via the Dataset API) ──────────────
    # Opt-in, paid source. Set JOBPILOT_BRIGHTDATA_API_TOKEN to enable it; the
    # adapter errors clearly (surfaced per-source) when it's unset. The default
    # dataset id is Bright Data's "LinkedIn job listings" dataset, confirmed
    # against the brightdata-mcp server source (tool id: linkedin_job_listings).
    # Kept overridable via JOBPILOT_BRIGHTDATA_LINKEDIN_JOBS_DATASET in case it's
    # reissued. (Other LinkedIn datasets: company gd_l1vikfnt1wgvvqz95w,
    # people-profile gd_l1viktl72bvl7bjuj0.)
    brightdata_api_token: str = ""
    brightdata_base_url: str = "https://api.brightdata.com/datasets/v3"
    brightdata_linkedin_jobs_dataset: str = "gd_lpfll7v5hcqtkxl6l"
    # Default location used when discovering by keyword (matches the app's focus).
    brightdata_location: str = "San Francisco Bay Area"
    # Async discover polling: how long to wait for a snapshot, and the interval.
    brightdata_timeout: float = 120.0
    brightdata_poll_interval: float = 5.0


settings = Settings()
