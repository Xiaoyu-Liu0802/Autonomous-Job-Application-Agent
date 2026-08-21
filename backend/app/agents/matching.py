"""Matching agent — a deterministic, explainable fit-scoring engine.

Deliberately LLM-free: fit scoring must be reproducible and auditable. The
overall score is a weighted blend of six dimensions (see PRD §9):

    30% skills · 20% experience · 15% education · 15% role · 10% location · 10% preferences

Each dimension returns a 0–100 score plus human-readable explanation lines,
so the dashboard can show *why* a job matched and where the gaps are.
"""
from __future__ import annotations

import re

from app.models import CandidateProfile, Job, MatchScore

WEIGHTS = {
    "skills": 0.30,
    "experience": 0.20,
    "education": 0.15,
    "role": 0.15,
    "location": 0.10,
    "preferences": 0.10,
}

# Degree keyword -> rank. Higher rank satisfies lower requirements.
_DEGREE_RANK = {
    "phd": 5, "doctor": 5,
    "master": 4, "ms": 4, "msc": 4, "meng": 4, "mba": 4,
    "bachelor": 3, "bs": 3, "bsc": 3, "beng": 3, "ba": 3,
    "associate": 2,
    "high school": 1, "diploma": 1,
}

_STOPWORDS = {"a", "an", "the", "of", "and", "or", "for", "in", "to", "with", "senior", "junior", "staff", "sr", "jr"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9+#. ]", " ", s.lower()).strip()


def _tokens(s: str) -> set[str]:
    return {t for t in _norm(s).split() if t and t not in _STOPWORDS}


def _degree_rank(text: str) -> int:
    t = text.lower()
    best = 0
    for kw, rank in _DEGREE_RANK.items():
        if kw in t:
            best = max(best, rank)
    return best


def _score_skills(profile: CandidateProfile, job: Job) -> tuple[float, list[str], list[str], list[str]]:
    job_skills = {_norm(s): s for s in job.skills if s.strip()}
    if not job_skills:
        return 100.0, [], [], ["No specific skills listed for this role."]
    have = {_norm(s) for s in profile.skills}
    matched = [orig for key, orig in job_skills.items() if key in have]
    missing = [orig for key, orig in job_skills.items() if key not in have]
    score = round(len(matched) / len(job_skills) * 100, 1)
    expl = [f"✓ {s}" for s in matched] + [f"⚠ {s} not found in profile" for s in missing]
    return score, matched, missing, expl


def _score_experience(profile: CandidateProfile, job: Job) -> tuple[float, list[str]]:
    req = float(job.min_years_experience or 0)
    have = profile.total_experience_years
    if req <= 0:
        return 100.0, [f"{have} yrs experience; no minimum specified."]
    if have >= req:
        return 100.0, [f"{have} yrs meets the {req}+ yr requirement."]
    score = round(max(0.0, have / req) * 100, 1)
    return score, [f"⚠ {have} yrs vs {req}+ yrs requested."]


def _score_education(profile: CandidateProfile, job: Job) -> tuple[float, list[str]]:
    required = _degree_rank(job.education_required)
    if required == 0:
        return 100.0, []
    candidate = max((_degree_rank(e.get("degree", "")) for e in profile.education), default=0)
    if candidate >= required:
        return 100.0, [f"Education meets requirement ({job.education_required})."]
    score = round(candidate / required * 100, 1) if required else 100.0
    return score, [f"⚠ Requires {job.education_required}."]


def _score_role(profile: CandidateProfile, job: Job) -> tuple[float, list[str]]:
    if not profile.target_roles:
        return 100.0, []
    title_tokens = _tokens(job.title)
    if not title_tokens:
        return 100.0, []
    best = 0.0
    best_role = ""
    for role in profile.target_roles:
        rt = _tokens(role)
        if not rt:
            continue
        overlap = len(title_tokens & rt) / len(title_tokens | rt)
        if overlap > best:
            best, best_role = overlap, role
    score = round(best * 100, 1)
    note = [f'Title aligns with target role "{best_role}".'] if score >= 50 else \
           [f'⚠ "{job.title}" is a loose match for your target roles.']
    return score, note


def _score_location(profile: CandidateProfile, job: Job) -> tuple[float, list[str]]:
    prefs = [p.lower() for p in profile.preferred_locations]
    if not prefs:
        return 100.0, []
    if job.remote and any("remote" in p for p in prefs):
        return 100.0, ["Remote role matches your location preferences."]
    loc = job.location.lower()
    if any(p != "remote" and p in loc for p in prefs):
        return 100.0, [f"Location ({job.location}) matches your preferences."]
    if job.remote:
        return 80.0, ["Role is remote."]
    return 30.0, [f"⚠ {job.location} is outside your preferred locations."]


def _score_preferences(profile: CandidateProfile, job: Job) -> tuple[float, list[str]]:
    company = job.company.lower()
    reasons: list[str] = []
    if any(company == c.lower() for c in profile.excluded_companies):
        return 0.0, [f"✗ {job.company} is on your excluded list."]
    score = 80.0
    if any(company == c.lower() or c.lower() in company for c in profile.preferred_companies):
        score = 100.0
        reasons.append(f"★ {job.company} is a preferred company.")
    if profile.min_salary and job.salary_max and job.salary_max < profile.min_salary:
        score = min(score, 40.0)
        reasons.append(f"⚠ Max salary ${job.salary_max:,} is below your ${profile.min_salary:,} minimum.")
    return score, reasons


def score_job(profile: CandidateProfile, job: Job) -> MatchScore:
    """Compute the full, explainable fit breakdown for one job."""
    s_skills, matched, missing, e_skills = _score_skills(profile, job)
    s_exp, e_exp = _score_experience(profile, job)
    s_edu, e_edu = _score_education(profile, job)
    s_role, e_role = _score_role(profile, job)
    s_loc, e_loc = _score_location(profile, job)
    s_pref, e_pref = _score_preferences(profile, job)

    overall = round(
        s_skills * WEIGHTS["skills"]
        + s_exp * WEIGHTS["experience"]
        + s_edu * WEIGHTS["education"]
        + s_role * WEIGHTS["role"]
        + s_loc * WEIGHTS["location"]
        + s_pref * WEIGHTS["preferences"],
        1,
    )

    gaps = [line for line in (*e_skills, *e_exp, *e_edu, *e_role, *e_loc, *e_pref) if line.startswith(("⚠", "✗"))]
    explanation = [line for line in (*e_skills, *e_exp, *e_edu, *e_role, *e_loc, *e_pref) if not line.startswith(("⚠", "✗"))]

    return MatchScore(
        overall=overall,
        skills=s_skills,
        experience=s_exp,
        education=s_edu,
        role=s_role,
        location=s_loc,
        preferences=s_pref,
        matched_skills=matched,
        missing_skills=missing,
        gaps=gaps,
        explanation=explanation,
    )
