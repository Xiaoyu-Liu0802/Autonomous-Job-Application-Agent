"""Matching endpoint — scores every job for a profile and routes each decision."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.agents import decide, score_job
from app.db import get_session
from app.models import CandidateProfile, Job, ScoredJob

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/{profile_id}", response_model=list[ScoredJob])
def match_profile(
    profile_id: int,
    min_score: float = Query(0, ge=0, le=100),
    category: str | None = Query(None, description="Filter: AUTO_APPLY | REVIEW | REJECT"),
    session: Session = Depends(get_session),
) -> list[ScoredJob]:
    profile = session.get(CandidateProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    results: list[ScoredJob] = []
    for job in session.exec(select(Job)).all():
        score = score_job(profile, job)
        decision = decide(profile, job, score)
        if score.overall < min_score:
            continue
        if category and decision.category.value != category:
            continue
        results.append(
            ScoredJob(job_id=job.id, company=job.company, title=job.title, score=score, decision=decision)
        )

    results.sort(key=lambda r: r.score.overall, reverse=True)
    return results
