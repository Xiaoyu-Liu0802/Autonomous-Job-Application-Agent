"""Discovery dedupe tests using an offline fake source (no network)."""
from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

from app.models import Job
from app.services.discovery import run_discovery


class FakeSource:
    name = "fake"

    def __init__(self, token, jobs):
        self.token = token
        self._jobs = jobs

    def fetch(self):
        return self._jobs


class BrokenSource:
    name = "broken"
    token = "x"

    def fetch(self):
        raise RuntimeError("board not found")


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _job(ext_id: str) -> Job:
    return Job(external_id=ext_id, company="Acme", title="SWE", skills=["Python"])


def test_adds_new_and_skips_duplicates():
    session = _session()
    src = FakeSource("acme", [_job("greenhouse:acme:1"), _job("greenhouse:acme:2")])
    result = run_discovery(session, [src])
    assert result["added"] == 2
    assert result["skipped_duplicates"] == 0

    # Re-run with an overlapping id -> only the new one is added.
    src2 = FakeSource("acme", [_job("greenhouse:acme:2"), _job("greenhouse:acme:3")])
    result2 = run_discovery(session, [src2])
    assert result2["added"] == 1
    assert result2["skipped_duplicates"] == 1

    total = len(session.exec(__import__("sqlmodel").select(Job)).all())
    assert total == 3


def test_broken_source_is_reported_not_fatal():
    session = _session()
    good = FakeSource("acme", [_job("greenhouse:acme:1")])
    result = run_discovery(session, [BrokenSource(), good])
    assert result["added"] == 1
    assert any("broken" in e for e in result["errors"])
