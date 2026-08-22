"""Profile facts — the *only* ground truth an LLM answer is allowed to draw on.

The anti-fabrication guardrail (PRD §16) works by grounding: we enumerate every
atomic fact from the verified profile as an ``(id, value)`` pair, hand that set
to the generator, and afterwards verify the generated text introduces no
company, technology, number, or credential that isn't traceable to one of these
facts (or to the job posting itself). Nothing outside this set is "known".
"""
from __future__ import annotations

from pydantic import BaseModel

from app.models import CandidateProfile, Job


class Fact(BaseModel):
    id: str      # stable handle, e.g. "skill:python" or "exp:0:company"
    kind: str    # skill | experience | education | identity | preference | authorization
    value: str   # the human-readable fact text


def profile_facts(profile: CandidateProfile) -> list[Fact]:
    """Flatten a profile into atomic, citable facts."""
    facts: list[Fact] = [
        Fact(id="identity:name", kind="identity", value=profile.name),
        Fact(id="identity:location", kind="identity", value=profile.location),
        Fact(id="experience:total_years", kind="experience",
             value=f"{profile.total_experience_years} years of experience"),
    ]

    for skill in profile.skills:
        facts.append(Fact(id=f"skill:{skill.lower()}", kind="skill", value=skill))

    for i, exp in enumerate(profile.experiences):
        company = str(exp.get("company", "")).strip()
        role = str(exp.get("role", "")).strip()
        years = exp.get("years")
        desc = str(exp.get("description", "")).strip()
        if company:
            facts.append(Fact(id=f"exp:{i}:company", kind="experience", value=company))
        if role:
            facts.append(Fact(id=f"exp:{i}:role", kind="experience", value=role))
        if role and company:
            tenure = f" for {years} years" if years else ""
            facts.append(Fact(id=f"exp:{i}:summary", kind="experience",
                              value=f"{role} at {company}{tenure}"))
        if desc:
            facts.append(Fact(id=f"exp:{i}:description", kind="experience", value=desc))

    for i, edu in enumerate(profile.education):
        degree = str(edu.get("degree", "")).strip()
        school = str(edu.get("school", "")).strip()
        if degree:
            facts.append(Fact(id=f"edu:{i}:degree", kind="education", value=degree))
        if school:
            facts.append(Fact(id=f"edu:{i}:school", kind="education", value=school))

    for role in profile.target_roles:
        facts.append(Fact(id=f"target:{role.lower()}", kind="preference", value=role))

    auth = profile.work_authorization or {}
    if "authorized" in auth:
        facts.append(Fact(id="auth:authorized", kind="authorization",
                          value="authorized to work" if auth["authorized"] else "not authorized to work"))
    if "sponsorship_required" in auth:
        facts.append(Fact(id="auth:sponsorship", kind="authorization",
                          value="requires sponsorship" if auth["sponsorship_required"] else "does not require sponsorship"))

    return [f for f in facts if f.value]


def job_context(job: Job) -> list[str]:
    """Facts about the *posting* — legitimately citable in a tailored answer
    (the company name, the role, its stated skills) without being fabrication."""
    ctx = [job.company, job.title, job.location, *job.skills, *job.requirements]
    return [c for c in ctx if c]


def matched_skills(profile: CandidateProfile, job: Job) -> list[str]:
    """Profile skills that also appear in the job — the honest overlap to lead with."""
    job_skills = {s.lower() for s in job.skills}
    return [s for s in profile.skills if s.lower() in job_skills]
