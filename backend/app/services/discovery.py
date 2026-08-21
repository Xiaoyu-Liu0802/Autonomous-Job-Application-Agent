"""Discovery service — fetch from sources, deduplicate, persist.

This is the Discovery Agent (PRD §8) minus the scheduler: given a set of
sources, it fetches current postings, drops anything we've already stored
(dedupe on ``external_id``), and inserts the rest.
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.models import Job
from app.sources import JobSource


def run_discovery(session: Session, sources: list[JobSource]) -> dict:
    added = 0
    skipped = 0
    per_source: dict[str, int] = {}
    errors: list[str] = []

    existing_ids = {row for row in session.exec(select(Job.external_id)).all()}

    for src in sources:
        label = getattr(src, "name", src.__class__.__name__)
        token = getattr(src, "token", "")
        key = f"{label}:{token}" if token else label
        try:
            fetched = src.fetch()
        except Exception as e:  # network / bad token / shape change
            errors.append(f"{key}: {e}")
            continue

        source_added = 0
        for job in fetched:
            if not job.external_id or job.external_id in existing_ids:
                skipped += 1
                continue
            session.add(job)
            existing_ids.add(job.external_id)
            added += 1
            source_added += 1
        per_source[key] = source_added

    session.commit()
    return {
        "added": added,
        "skipped_duplicates": skipped,
        "per_source": per_source,
        "errors": errors,
    }
