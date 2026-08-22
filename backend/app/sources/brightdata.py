"""Bright Data LinkedIn adapter (Dataset API v3).

Unlike the ATS adapters, LinkedIn has no public jobs API — so this goes through
Bright Data, a commercial provider that runs the collection on their own
compliant infrastructure (we never hit LinkedIn directly). It is an *opt-in*,
paid source: it does nothing until ``JOBPILOT_BRIGHTDATA_API_TOKEN`` is set, and
is deliberately kept out of ``DEFAULT_SOURCES``.

Two modes, chosen by what you pass as the source token:
  • one or more ``https://…linkedin.com/…`` URLs (comma-separated)
      → synchronous "scrape" of those exact postings (the /scrape endpoint,
        matching Bright Data's own quick-start curl).
  • anything else, treated as a search keyword
      → asynchronous "discover_new by keyword" (trigger → poll → download),
        scoped to ``settings.brightdata_location``.

Field mapping is intentionally tolerant (several fallback keys per field)
because Bright Data's LinkedIn schema keys vary a little across datasets.
"""
from __future__ import annotations

import time

import httpx

from app.config import settings
from app.models import Job
from app.sources.base import USER_AGENT
from app.sources.normalize import normalize_employment_type, normalize_job, strip_html


def _first(record: dict, *keys: str, default: str = "") -> str:
    """Return the first present, non-empty value among ``keys``."""
    for k in keys:
        v = record.get(k)
        if v:
            return v if isinstance(v, str) else str(v)
    return default


class BrightDataError(RuntimeError):
    """Raised on configuration/collection failure; surfaced per-source by discovery."""


class BrightDataSource:
    name = "brightdata"

    def __init__(self, token: str, *, dataset_id: str | None = None) -> None:
        # ``token`` is the source *input* (URLs or a keyword), not the API key.
        self.token = token
        self.dataset_id = dataset_id or settings.brightdata_linkedin_jobs_dataset

    # ── HTTP (single choke point so tests can monkeypatch it) ─────────────
    def _api(self, method: str, path: str, *, params: dict | None = None, json=None):
        api_key = settings.brightdata_api_token
        if not api_key:
            raise BrightDataError(
                "Bright Data is not configured — set JOBPILOT_BRIGHTDATA_API_TOKEN "
                "to enable the LinkedIn source."
            )
        resp = httpx.request(
            method,
            f"{settings.brightdata_base_url}/{path.lstrip('/')}",
            params=params,
            json=json,
            timeout=settings.brightdata_timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        resp.raise_for_status()
        return resp.json()

    # ── Collection modes ──────────────────────────────────────────────────
    def _scrape_urls(self, urls: list[str]) -> list[dict]:
        """Synchronous scrape of specific LinkedIn URLs."""
        data = self._api(
            "POST",
            "scrape",
            params={"dataset_id": self.dataset_id, "notify": "false", "include_errors": "true"},
            json={"input": [{"url": u} for u in urls], "limit_per_input": None},
        )
        return _as_records(data)

    def _discover_keyword(self, keyword: str) -> list[dict]:
        """Asynchronous discover-by-keyword: trigger, poll, then download."""
        trigger = self._api(
            "POST",
            "trigger",
            params={
                "dataset_id": self.dataset_id,
                "type": "discover_new",
                "discover_by": "keyword",
                "include_errors": "true",
            },
            json=[{"keyword": keyword, "location": settings.brightdata_location}],
        )
        snapshot_id = trigger.get("snapshot_id") if isinstance(trigger, dict) else None
        if not snapshot_id:
            raise BrightDataError(f"No snapshot_id in trigger response: {trigger!r}")

        deadline = time.monotonic() + settings.brightdata_timeout
        while time.monotonic() < deadline:
            progress = self._api("GET", f"progress/{snapshot_id}")
            status = (progress or {}).get("status", "")
            if status == "ready":
                return _as_records(self._api("GET", f"snapshot/{snapshot_id}", params={"format": "json"}))
            if status in {"failed", "error"}:
                raise BrightDataError(f"Snapshot {snapshot_id} {status}: {progress!r}")
            time.sleep(settings.brightdata_poll_interval)
        raise BrightDataError(f"Snapshot {snapshot_id} not ready within {settings.brightdata_timeout}s")

    # ── Public API ──────────────────────────────────────────────────────────
    def fetch(self) -> list[Job]:
        raw = self.token.strip()
        if not raw:
            raise BrightDataError("Bright Data source needs a keyword or LinkedIn URL(s).")

        if "linkedin.com" in raw.lower() or raw.lower().startswith("http"):
            urls = [u.strip() for u in raw.split(",") if u.strip()]
            records = self._scrape_urls(urls)
        else:
            records = self._discover_keyword(raw)

        jobs: list[Job] = []
        for rec in records:
            if not isinstance(rec, dict) or rec.get("error"):
                continue
            job = _normalize_linkedin_job(rec)
            if job is not None:
                jobs.append(job)
        return jobs


def _as_records(data) -> list[dict]:
    """The scrape/snapshot endpoints return a JSON array (or a single object)."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Some responses wrap rows under a key; otherwise treat the dict as one row.
        for key in ("data", "results", "records"):
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    return []


def _normalize_linkedin_job(rec: dict) -> Job | None:
    """Map one Bright Data LinkedIn job record onto our ``Job`` model."""
    title = _first(rec, "job_title", "title")
    url = _first(rec, "url", "job_posting_url", "job_url", "link")
    if not title and not url:
        return None  # not a usable job row

    company = _first(rec, "company_name", "company", "employer_name", "organization")
    location = _first(rec, "job_location", "location", "formatted_location")
    description = _first(rec, "job_summary", "job_description", "description")
    description = strip_html(description) if "<" in description else description
    posted = _first(rec, "job_posted_date", "job_posted_time", "posted_date", "date_posted")[:10]
    employment = normalize_employment_type(_first(rec, "job_employment_type", "employment_type"))

    posting_id = _first(rec, "job_posting_id", "id", "linkedin_job_id") or url or title
    return normalize_job(
        external_id=f"brightdata:linkedin:{posting_id}",
        company=company or "Unknown (LinkedIn)",
        title=title or "Untitled role",
        location=location,
        url=url,
        description=description,
        source="brightdata",
        application_method="external",
        date_posted=posted,
        employment_type=employment,
    )
