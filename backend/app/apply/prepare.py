"""Application preparation — decide what the agent can fill confidently vs. what
must be routed to the human (PRD §12–14).

Pure logic, no browser. Produces an ``ApplicationPlan``: the field values we can
fill from the verified profile + saved answers, plus the open questions that
need the user. This is the human-in-the-loop gate before any browser work.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.models import CandidateProfile

if TYPE_CHECKING:
    from app.models import Job

# Questions the agent must never answer on its own without a saved/user answer.
_SENSITIVE = [
    "gender", "race", "ethnicity", "veteran", "disability", "sexual orientation",
    "salary", "compensation", "expected pay", "desired salary",
]
_SPONSORSHIP = re.compile(r"sponsor|visa|work authorization|authorized to work", re.IGNORECASE)


class PlannedField(BaseModel):
    field: str
    value: str
    confidence: float  # 0–100


class OpenQuestion(BaseModel):
    question: str
    reason: str
    suggestion: str = ""


class ApplicationPlan(BaseModel):
    known_fields: list[PlannedField]
    open_questions: list[OpenQuestion]

    @property
    def ready_to_submit(self) -> bool:
        return not self.open_questions


def _split_name(full: str) -> tuple[str, str]:
    parts = full.strip().split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:])


def build_known_fields(profile: CandidateProfile) -> list[PlannedField]:
    """High-confidence fields sourced directly from the verified profile."""
    first, last = _split_name(profile.name)
    auth = profile.work_authorization or {}
    fields = [
        PlannedField(field="first_name", value=first, confidence=100),
        PlannedField(field="last_name", value=last, confidence=100),
        PlannedField(field="full_name", value=profile.name, confidence=100),
        PlannedField(field="email", value=profile.email, confidence=100),
        PlannedField(field="phone", value=profile.phone, confidence=95 if profile.phone else 0),
        PlannedField(field="location", value=profile.location, confidence=90 if profile.location else 0),
        PlannedField(field="linkedin", value=profile.linkedin, confidence=100 if profile.linkedin else 0),
        PlannedField(field="github", value=profile.github, confidence=100 if profile.github else 0),
        PlannedField(field="portfolio", value=profile.portfolio, confidence=100 if profile.portfolio else 0),
        PlannedField(field="years_experience", value=str(profile.total_experience_years), confidence=90),
    ]
    if "authorized" in auth:
        fields.append(PlannedField(
            field="work_authorized",
            value="Yes" if auth.get("authorized") else "No",
            confidence=100,
        ))
    if "sponsorship_required" in auth:
        fields.append(PlannedField(
            field="requires_sponsorship",
            value="Yes" if auth.get("sponsorship_required") else "No",
            confidence=100,
        ))
    # Drop empties.
    return [f for f in fields if f.value]


def classify_question(question: str, profile: CandidateProfile, saved_answers: dict[str, str]) -> OpenQuestion | PlannedField:
    """Return a PlannedField if we can answer confidently, else an OpenQuestion."""
    q = question.strip()
    low = q.lower()

    # 1) Previously saved / verified answer wins.
    for known_q, ans in saved_answers.items():
        if known_q.strip().lower() == low:
            return PlannedField(field=q, value=ans, confidence=100)

    # 2) Work-authorization questions map to the structured profile.
    if _SPONSORSHIP.search(low):
        auth = profile.work_authorization or {}
        if "sponsor" in low and "sponsorship_required" in auth:
            return PlannedField(field=q, value="Yes" if auth["sponsorship_required"] else "No", confidence=100)
        if "authorized" in auth:
            return PlannedField(field=q, value="Yes" if auth["authorized"] else "No", confidence=100)

    # 3) Sensitive / salary / demographic -> always ask the human.
    if any(kw in low for kw in _SENSITIVE):
        return OpenQuestion(question=q, reason="Sensitive/compensation question — requires your decision.")

    # 4) Anything else the agent can't ground -> ask.
    return OpenQuestion(question=q, reason="No verified answer available.")


def prepare_application(
    profile: CandidateProfile,
    custom_questions: list[str] | None = None,
    saved_answers: dict[str, str] | None = None,
    job: "Job | None" = None,
) -> ApplicationPlan:
    """Build the fill plan. When a ``job`` is supplied, the LLM layer drafts a
    *grounded* answer for questions we can't answer structurally: a fully
    grounded, high-confidence draft is promoted to a fillable field; anything
    weaker is attached to the open question as a reviewable suggestion. The
    anti-fabrication guardrail runs inside ``draft_answer`` — nothing ungrounded
    is ever promoted."""
    saved_answers = saved_answers or {}
    known = build_known_fields(profile)
    open_qs: list[OpenQuestion] = []

    for question in custom_questions or []:
        result = classify_question(question, profile, saved_answers)
        if isinstance(result, PlannedField):
            known.append(result)
            continue

        if job is not None:
            # Lazy import keeps the LLM layer optional for pure field mapping.
            from app.llm import draft_answer

            draft = draft_answer(profile, job, question)
            if draft.auto_fillable:
                known.append(PlannedField(field=question, value=draft.answer, confidence=draft.confidence))
                continue
            if draft.answer:
                result = OpenQuestion(question=result.question, reason=result.reason, suggestion=draft.answer)

        open_qs.append(result)

    return ApplicationPlan(known_fields=known, open_questions=open_qs)
