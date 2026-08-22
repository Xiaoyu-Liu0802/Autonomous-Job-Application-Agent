"""Application endpoints: create (score + decide + track), advance the pipeline,
answer human-in-the-loop questions, and read the dashboard funnel."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, func, select

from app.agents import decide, score_job
from app.apply import ApplicationPlan, prepare_application
from app.db import get_session
from app.models import (
    PIPELINE_ORDER,
    TERMINAL_STATES,
    Application,
    ApplicationStatus,
    CandidateProfile,
    DecisionCategory,
    Job,
)
from app.models.application import POST_SUBMIT_STATES

# Pre-submit funnel states: the application exists but hasn't been sent yet.
_PRE_SUBMIT = {ApplicationStatus.PREPARING, ApplicationStatus.NEEDS_REVIEW}

# Friendly log icons for real, human-logged pipeline events.
_EVENT_ICON = {
    ApplicationStatus.RECRUITER_SCREEN: "📞",
    ApplicationStatus.TECHNICAL_INTERVIEW: "💻",
    ApplicationStatus.ONSITE: "🏢",
    ApplicationStatus.OFFER: "🎉",
    ApplicationStatus.REJECTED: "❌",
    ApplicationStatus.GHOSTED: "👻",
    ApplicationStatus.WITHDRAWN: "🚪",
}

router = APIRouter(prefix="/applications", tags=["applications"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(app: Application, icon: str, event: str) -> None:
    # SQLModel JSON columns register as dirty only when reassigned a new list.
    app.actions = [*app.actions, {"at": _now(), "icon": icon, "event": event}]


class CreateApplication(BaseModel):
    profile_id: int
    job_id: int


class StatusUpdate(BaseModel):
    status: ApplicationStatus


class AnswerQuestion(BaseModel):
    question: str
    answer: str
    remember: bool = False


class PrepareRequest(BaseModel):
    # The application form's custom questions (from the ATS page), if known.
    questions: list[str] = []


@router.get("", response_model=list[Application])
def list_applications(session: Session = Depends(get_session)) -> list[Application]:
    return list(session.exec(select(Application)).all())


@router.get("/funnel")
def funnel(session: Session = Depends(get_session)) -> dict[str, int]:
    """Counts per status for the dashboard funnel."""
    rows = session.exec(
        select(Application.status, func.count()).group_by(Application.status)
    ).all()
    counts = {status.value: 0 for status in ApplicationStatus}
    for status, n in rows:
        counts[status.value if hasattr(status, "value") else status] = n
    return counts


@router.get("/{application_id}", response_model=Application)
def get_application(application_id: int, session: Session = Depends(get_session)) -> Application:
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app


@router.post("", response_model=Application, status_code=201)
def create_application(body: CreateApplication, session: Session = Depends(get_session)) -> Application:
    """Score the job, run the decision engine, and open a tracked application
    with a seeded audit trail. The decision sets the initial pipeline status:
    AUTO_APPLY -> preparing, REVIEW -> needs_review, REJECT -> rejected."""
    profile = session.get(CandidateProfile, body.profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    job = session.get(Job, body.job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    existing = session.exec(
        select(Application).where(
            Application.profile_id == body.profile_id, Application.job_id == body.job_id
        )
    ).first()
    if existing:
        raise HTTPException(409, "Application already exists for this job (no duplicates)")

    score = score_job(profile, job)
    decision = decide(profile, job, score)

    status_map = {
        DecisionCategory.AUTO_APPLY: ApplicationStatus.PREPARING,
        DecisionCategory.REVIEW: ApplicationStatus.NEEDS_REVIEW,
        # A REJECT is the *agent* choosing not to apply — a "skipped", NOT an
        # employer rejection. Those are different things and get different states.
        DecisionCategory.REJECT: ApplicationStatus.SKIPPED,
    }

    app = Application(
        job_id=job.id,
        profile_id=profile.id,
        status=status_map[decision.category],
        fit_score=score.overall,
        decision=decision.category.value,
        created_at=_now(),
    )
    _log(app, "🔍", f"Job discovered at {job.company}")
    _log(app, "🤖", f"Fit score calculated: {score.overall}%")
    _log(app, "🧭", f"Decision: {decision.category.value} — {decision.reasons[0] if decision.reasons else ''}")
    if decision.category == DecisionCategory.REVIEW:
        _log(app, "⚠️", "User review requested")

    session.add(app)
    session.commit()
    session.refresh(app)
    return app


@router.post("/{application_id}/advance", response_model=Application)
def advance(application_id: int, session: Session = Depends(get_session)) -> Application:
    """Move an application to the next stage in the pipeline funnel."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if app.status in TERMINAL_STATES:
        raise HTTPException(409, f"Application is in terminal state '{app.status.value}'")
    if app.status not in PIPELINE_ORDER:
        raise HTTPException(409, f"Cannot advance from '{app.status.value}'")

    idx = PIPELINE_ORDER.index(app.status)
    if idx + 1 >= len(PIPELINE_ORDER):
        raise HTTPException(409, "Already at the final pipeline stage (offer)")

    app.status = PIPELINE_ORDER[idx + 1]
    if app.status == ApplicationStatus.APPLIED:
        app.applied_at = _now()
        _log(app, "✓", "Application submitted")
    else:
        _log(app, "→", f"Advanced to {app.status.value}")
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


@router.post("/{application_id}/submit", response_model=Application)
def submit(application_id: int, session: Session = Depends(get_session)) -> Application:
    """Record that *you* submitted the application on the real ATS (fill-and-pause
    means the human clicks Submit). This is the single gate from the pre-submit
    funnel into the live, post-submit pipeline — you can't log interview stages
    before it."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if app.status not in _PRE_SUBMIT:
        raise HTTPException(
            409,
            f"Can only submit from 'preparing' or 'needs_review' (currently '{app.status.value}').",
        )
    app.status = ApplicationStatus.APPLIED
    app.applied_at = _now()
    _log(app, "✅", "You marked this as submitted")
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


@router.post("/{application_id}/log-event", response_model=Application)
def log_event(application_id: int, body: StatusUpdate, session: Session = Depends(get_session)) -> Application:
    """Manually log a *real-world* pipeline event you observed (recruiter screen,
    interview, offer, rejection, …). Only valid after the application has been
    submitted — JobPilot has no email/ATS integration, so these are entered by you."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if body.status not in POST_SUBMIT_STATES:
        raise HTTPException(422, f"'{body.status.value}' is not a loggable post-submit event.")
    already_submitted = app.status == ApplicationStatus.APPLIED or app.status in POST_SUBMIT_STATES
    if not already_submitted:
        raise HTTPException(409, "Mark the application as submitted before logging real events.")

    app.status = body.status
    _log(app, _EVENT_ICON.get(body.status, "•"), f"Logged: {body.status.value.replace('_', ' ')}")
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


@router.post("/{application_id}/status", response_model=Application)
def set_status(application_id: int, body: StatusUpdate, session: Session = Depends(get_session)) -> Application:
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    app.status = body.status
    if body.status == ApplicationStatus.APPLIED and not app.applied_at:
        app.applied_at = _now()
    _log(app, "•", f"Status set to {body.status.value}")
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


@router.post("/{application_id}/prepare", response_model=ApplicationPlan)
def prepare(application_id: int, body: PrepareRequest, session: Session = Depends(get_session)) -> ApplicationPlan:
    """Build the fill plan: which fields the agent can complete from the verified
    profile + saved answers, and which questions still need the human. Nothing is
    submitted here — this is the human-in-the-loop gate before browser work."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")
    profile = session.get(CandidateProfile, app.profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    job = session.get(Job, app.job_id)

    plan = prepare_application(
        profile, custom_questions=body.questions, saved_answers=app.answers, job=job
    )
    _log(app, "📝", f"Prepared application ({len(plan.known_fields)} fields ready, "
                    f"{len(plan.open_questions)} need review)")
    if plan.open_questions and app.status == ApplicationStatus.PREPARING:
        app.status = ApplicationStatus.NEEDS_REVIEW
    session.add(app)
    session.commit()
    return plan


@router.post("/{application_id}/answer", response_model=Application)
def answer_question(application_id: int, body: AnswerQuestion, session: Session = Depends(get_session)) -> Application:
    """Human-in-the-loop: record a user's answer to an ambiguous question and,
    if the fit allows, clear the application out of NEEDS_REVIEW into preparing."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(404, "Application not found")

    app.answers = {**app.answers, body.question: body.answer}
    _log(app, "👤", f"User answered: {body.question}")
    if body.remember:
        _log(app, "💾", "Saved answer for future applications")
    if app.status == ApplicationStatus.NEEDS_REVIEW:
        app.status = ApplicationStatus.PREPARING
        _log(app, "✓", "Cleared review — continuing application")

    session.add(app)
    session.commit()
    session.refresh(app)
    return app
