"""Job endpoints. Creation deduplicates on external_id (the discovery agent's key)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[Job])
def list_jobs(session: Session = Depends(get_session)) -> list[Job]:
    return list(session.exec(select(Job)).all())


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: int, session: Session = Depends(get_session)) -> Job:
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("", response_model=Job, status_code=201)
def create_job(job: Job, session: Session = Depends(get_session)) -> Job:
    if job.external_id:
        dupe = session.exec(select(Job).where(Job.external_id == job.external_id)).first()
        if dupe:
            raise HTTPException(409, f"Job with external_id '{job.external_id}' already exists")
    job.id = None
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
