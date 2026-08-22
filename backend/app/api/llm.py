"""LLM endpoints (Milestone 5): grounded answer drafting + resume tailoring.

Both are read-only reasoning helpers — they never mutate an application or
submit anything. Every response carries its grounding status and confidence so
the UI can show *why* a draft is safe (or why it's being handed back to you)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.llm import DraftedAnswer, TailoredResume, draft_answer, get_provider, tailor_resume
from app.models import Application, CandidateProfile, Job

router = APIRouter(prefix="/llm", tags=["llm"])


class DraftAnswerRequest(BaseModel):
    profile_id: int
    job_id: int
    question: str


class TailorResumeRequest(BaseModel):
    profile_id: int
    job_id: int


def _load(session: Session, profile_id: int, job_id: int) -> tuple[CandidateProfile, Job]:
    profile = session.get(CandidateProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return profile, job


@router.get("/status")
def status() -> dict[str, object]:
    """Which provider is active and the guardrail settings — handy for the UI."""
    return {
        "provider": get_provider().name,
        "configured": settings.llm_provider,
        "model": settings.llm_model,
        "min_answer_confidence": settings.min_answer_confidence,
    }


@router.post("/draft-answer", response_model=DraftedAnswer)
def draft(body: DraftAnswerRequest, session: Session = Depends(get_session)) -> DraftedAnswer:
    profile, job = _load(session, body.profile_id, body.job_id)
    return draft_answer(profile, job, body.question)


@router.post("/tailor-resume", response_model=TailoredResume)
def tailor(body: TailorResumeRequest, session: Session = Depends(get_session)) -> TailoredResume:
    profile, job = _load(session, body.profile_id, body.job_id)
    return tailor_resume(profile, job)


class ApplicationDraftRequest(BaseModel):
    question: str


@router.post("/applications/{application_id}/draft-answer", response_model=DraftedAnswer)
def draft_for_application(
    application_id: int,
    body: ApplicationDraftRequest,
    session: Session = Depends(get_session),
) -> DraftedAnswer:
    """Draft a grounded answer in the context of a tracked application."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    profile, job = _load(session, app.profile_id, app.job_id)
    return draft_answer(profile, job, body.question)
