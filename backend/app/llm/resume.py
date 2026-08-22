"""Resume tailoring (PRD §16) — emphasize, never embellish.

Tailoring here means *selection and ordering* of facts the candidate already
has, plus a grounded summary line. It surfaces the real overlap between the
profile and the posting and reorders experience to lead with the most relevant
role. It never adds a skill, employer, or metric that isn't in the profile —
the output is run through the same grounding guardrail to prove it.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.llm.facts import job_context, matched_skills, profile_facts
from app.llm.guardrails import verify_grounding
from app.llm.provider import LLMProvider, get_provider
from app.models import CandidateProfile, Job


class ResumeBullet(BaseModel):
    text: str
    relevance: int   # count of job skills this experience touches
    source: str      # the profile fact this is drawn from


class TailoredResume(BaseModel):
    summary: str
    highlighted_skills: list[str]   # profile skills that overlap the posting
    missing_skills: list[str]       # job skills the candidate does NOT have (honesty)
    emphasis: list[ResumeBullet]    # experiences reordered by relevance
    grounded: bool
    violations: list[str]
    provider: str = ""


def _experience_relevance(exp: dict, job: Job) -> tuple[int, list[str]]:
    """How many job skills this experience's text mentions."""
    text = f"{exp.get('role', '')} {exp.get('description', '')}".lower()
    hits = [s for s in job.skills if s.lower() in text]
    return len(hits), hits


def tailor_resume(
    profile: CandidateProfile,
    job: Job,
    provider: LLMProvider | None = None,
) -> TailoredResume:
    provider = provider or get_provider()
    facts = profile_facts(profile)
    job_ctx = job_context(job)
    matched = matched_skills(profile, job)
    missing = [s for s in job.skills if s.lower() not in {m.lower() for m in profile.skills}]

    # Summary line via the provider (grounded), verified below.
    gen = provider.generate_summary(facts, job_ctx, matched)
    summary = gen.text

    # Rank real experiences by overlap with the posting; emphasize, never invent.
    ranked = []
    for i, exp in enumerate(profile.experiences):
        score, hits = _experience_relevance(exp, job)
        role = str(exp.get("role", "")).strip()
        company = str(exp.get("company", "")).strip()
        if not (role or company):
            continue
        label = " at ".join(x for x in [role, company] if x)
        detail = f" — relevant to {', '.join(hits)}" if hits else ""
        ranked.append(ResumeBullet(text=f"{label}{detail}", relevance=score, source=f"exp:{i}"))
    ranked.sort(key=lambda b: b.relevance, reverse=True)

    # Guardrail: the summary must be fully grounded in profile + posting.
    sources = [f.value for f in facts] + job_ctx
    report = verify_grounding(summary, sources)

    return TailoredResume(
        summary=summary,
        highlighted_skills=matched,
        missing_skills=missing,
        emphasis=ranked,
        grounded=report.grounded,
        violations=report.violations,
        provider=gen.provider,
    )
