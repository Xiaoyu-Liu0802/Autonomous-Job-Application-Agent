"""Offline tests for the Bright Data LinkedIn adapter.

No network: the single HTTP choke point (``BrightDataSource._api``) is
monkeypatched, so we exercise mode selection, polling, tolerant field mapping,
and the config guard deterministically."""
from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.config import settings
from app.models import Job
from app.services.discovery import run_discovery
from app.sources import build_source
from app.sources.brightdata import (
    BrightDataError,
    BrightDataSource,
    _as_records,
    _normalize_linkedin_job,
)

JOB_RECORD = {
    "job_title": "Senior Software Engineer",
    "company_name": "Bright Data",
    "job_location": "San Francisco, CA",
    "job_summary": "Build scalable services with Python and Kubernetes. 3+ years required.",
    "url": "https://www.linkedin.com/jobs/view/123456",
    "job_posted_date": "2026-08-20T10:00:00",
    "job_employment_type": "FullTime",
    "job_posting_id": "123456",
}


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    # Give the adapter a token by default so _api isn't short-circuited; the
    # missing-token test overrides this back to "".
    monkeypatch.setattr(settings, "brightdata_api_token", "test-token")
    monkeypatch.setattr(settings, "brightdata_poll_interval", 0.0)


def test_build_source_registers_brightdata():
    src = build_source("brightdata", "software engineer")
    assert isinstance(src, BrightDataSource)
    assert src.name == "brightdata"


def test_missing_token_raises(monkeypatch):
    monkeypatch.setattr(settings, "brightdata_api_token", "")
    with pytest.raises(BrightDataError, match="not configured"):
        BrightDataSource("software engineer").fetch()


def test_normalize_maps_primary_fields():
    job = _normalize_linkedin_job(JOB_RECORD)
    assert job is not None
    assert job.title == "Senior Software Engineer"
    assert job.company == "Bright Data"
    assert job.location == "San Francisco, CA"
    assert job.url.endswith("/123456")
    assert job.source == "brightdata"
    assert job.employment_type == "full_time"
    assert job.min_years_experience == 3.0        # extracted from the summary
    assert "Python" in job.skills
    assert job.external_id == "brightdata:linkedin:123456"


def test_normalize_tolerant_fallback_keys():
    rec = {
        "title": "Backend Engineer",
        "company": "Acme",
        "location": "Palo Alto, CA",
        "description": "Go and gRPC services.",
        "job_posting_url": "https://www.linkedin.com/jobs/view/999",
    }
    job = _normalize_linkedin_job(rec)
    assert job is not None
    assert job.title == "Backend Engineer"
    assert job.company == "Acme"
    assert job.url.endswith("/999")


def test_normalize_skips_rows_without_title_or_url():
    assert _normalize_linkedin_job({"company_name": "Nope"}) is None


def test_as_records_handles_list_dict_and_wrapped():
    assert _as_records([{"a": 1}]) == [{"a": 1}]
    assert _as_records({"data": [{"a": 1}]}) == [{"a": 1}]
    assert _as_records({"a": 1}) == [{"a": 1}]
    assert _as_records(None) == []


def test_fetch_url_mode_hits_scrape(monkeypatch):
    calls = []

    def fake_api(method, path, *, params=None, json=None):
        calls.append((method, path, params, json))
        return [JOB_RECORD]

    src = BrightDataSource("https://www.linkedin.com/jobs/view/123456")
    monkeypatch.setattr(src, "_api", fake_api)
    jobs = src.fetch()

    assert len(jobs) == 1 and jobs[0].title == "Senior Software Engineer"
    method, path, params, body = calls[0]
    assert (method, path) == ("POST", "scrape")
    assert params["dataset_id"] == settings.brightdata_linkedin_jobs_dataset
    assert body["input"] == [{"url": "https://www.linkedin.com/jobs/view/123456"}]


def test_fetch_keyword_mode_triggers_polls_downloads(monkeypatch):
    seen_paths = []

    def fake_api(method, path, *, params=None, json=None):
        seen_paths.append(path)
        if path == "trigger":
            assert json == [{"keyword": "software engineer", "location": settings.brightdata_location}]
            return {"snapshot_id": "snap1"}
        if path == "progress/snap1":
            # First poll: still running; second poll: ready.
            return {"status": "running"} if seen_paths.count("progress/snap1") == 1 else {"status": "ready"}
        if path == "snapshot/snap1":
            return [JOB_RECORD]
        raise AssertionError(f"unexpected path {path}")

    src = BrightDataSource("software engineer")
    monkeypatch.setattr(src, "_api", fake_api)
    jobs = src.fetch()

    assert [j.title for j in jobs] == ["Senior Software Engineer"]
    assert seen_paths[0] == "trigger"
    assert seen_paths.count("progress/snap1") == 2   # polled until ready
    assert seen_paths[-1] == "snapshot/snap1"


def test_failed_snapshot_raises(monkeypatch):
    def fake_api(method, path, *, params=None, json=None):
        if path == "trigger":
            return {"snapshot_id": "snapX"}
        return {"status": "failed"}

    src = BrightDataSource("data scientist")
    monkeypatch.setattr(src, "_api", fake_api)
    with pytest.raises(BrightDataError, match="failed"):
        src.fetch()


def test_run_discovery_ingests_and_dedupes(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    src = BrightDataSource("https://www.linkedin.com/jobs/view/123456")
    monkeypatch.setattr(src, "_api", lambda *a, **k: [JOB_RECORD])

    result = run_discovery(session, [src])
    assert result["added"] == 1
    assert result["errors"] == []

    # Re-run: same external_id -> deduped, nothing added.
    src2 = BrightDataSource("https://www.linkedin.com/jobs/view/123456")
    monkeypatch.setattr(src2, "_api", lambda *a, **k: [JOB_RECORD])
    result2 = run_discovery(session, [src2])
    assert result2["added"] == 0 and result2["skipped_duplicates"] == 1

    assert len(session.exec(select(Job)).all()) == 1
