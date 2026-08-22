"""An application object — one row per (candidate, job), with a full audit trail."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class ApplicationStatus(str, Enum):
    """Pipeline stages. The first block is the pre-submit funnel; the second
    block is post-submit; the last block holds terminal states."""

    DISCOVERED = "discovered"
    MATCHED = "matched"
    PREPARING = "preparing"
    NEEDS_REVIEW = "needs_review"
    APPLIED = "applied"
    RECRUITER_SCREEN = "recruiter_screen"
    TECHNICAL_INTERVIEW = "technical_interview"
    ONSITE = "onsite"
    OFFER = "offer"
    # Terminal
    SKIPPED = "skipped"        # the *agent* decided not to apply (REJECT decision)
    REJECTED = "rejected"      # the *employer* rejected us (a real, post-submit outcome)
    WITHDRAWN = "withdrawn"
    GHOSTED = "ghosted"
    EXPIRED = "expired"


# Ordered funnel used by the dashboard and for "advance" transitions.
PIPELINE_ORDER: list[ApplicationStatus] = [
    ApplicationStatus.DISCOVERED,
    ApplicationStatus.MATCHED,
    ApplicationStatus.PREPARING,
    ApplicationStatus.NEEDS_REVIEW,
    ApplicationStatus.APPLIED,
    ApplicationStatus.RECRUITER_SCREEN,
    ApplicationStatus.TECHNICAL_INTERVIEW,
    ApplicationStatus.ONSITE,
    ApplicationStatus.OFFER,
]

TERMINAL_STATES: set[ApplicationStatus] = {
    ApplicationStatus.SKIPPED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
    ApplicationStatus.GHOSTED,
    ApplicationStatus.EXPIRED,
}

# Stages that only make sense to log *after* the human has actually submitted.
POST_SUBMIT_STATES: list[ApplicationStatus] = [
    ApplicationStatus.RECRUITER_SCREEN,
    ApplicationStatus.TECHNICAL_INTERVIEW,
    ApplicationStatus.ONSITE,
    ApplicationStatus.OFFER,
    ApplicationStatus.REJECTED,
    ApplicationStatus.GHOSTED,
    ApplicationStatus.WITHDRAWN,
]


class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", index=True)
    profile_id: int = Field(foreign_key="candidateprofile.id", index=True)

    status: ApplicationStatus = Field(default=ApplicationStatus.DISCOVERED)
    fit_score: Optional[float] = None
    decision: str = ""            # AUTO_APPLY | REVIEW | REJECT
    resume_version: str = ""
    applied_at: str = ""

    answers: dict = Field(default_factory=dict, sa_column=Column(JSON))
    actions: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: str = ""
