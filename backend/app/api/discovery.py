"""Discovery endpoints: pull from ATS boards, or import a single pasted URL."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Job
from app.sources import DEFAULT_SOURCES, build_source
from app.sources.url_import import ImportError_, import_from_url
from app.services.discovery import run_discovery

router = APIRouter(prefix="/discovery", tags=["discovery"])


class SourceSpec(BaseModel):
    type: str   # greenhouse | lever | ashby
    token: str  # board token / company slug


class RunRequest(BaseModel):
    sources: list[SourceSpec] | None = None


class ImportUrlRequest(BaseModel):
    url: str


@router.post("/run")
def run(body: RunRequest | None = None, session: Session = Depends(get_session)) -> dict:
    """Fetch from the given ATS boards (or the default set), dedupe, and store."""
    specs = (body.sources if body and body.sources else None) or [SourceSpec(**s) for s in DEFAULT_SOURCES]
    try:
        sources = [build_source(s.type, s.token) for s in specs]
    except ValueError as e:
        raise HTTPException(400, str(e))
    return run_discovery(session, sources)


@router.post("/import-url", response_model=Job)
def import_url(body: ImportUrlRequest, session: Session = Depends(get_session)) -> Job:
    """Import one posting from a pasted URL (ATS API when recognized, else best-effort)."""
    try:
        job = import_from_url(body.url)
    except ImportError_ as e:
        raise HTTPException(422, str(e))

    if job.external_id:
        dupe = session.exec(select(Job).where(Job.external_id == job.external_id)).first()
        if dupe:
            return dupe  # idempotent: return the existing row
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
