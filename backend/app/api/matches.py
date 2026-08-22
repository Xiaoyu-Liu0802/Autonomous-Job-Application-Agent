"""Matching endpoint — scores every job for a profile and routes each decision.

Beyond the fit score, the endpoint supports hard filters (experience range,
location, employment type) so the dashboard can narrow to, say, mid-level
full-time roles in the SF Bay Area. Filters are applied *before* scoring so the
returned count reflects only jobs the user actually wants to see."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.agents import decide, score_job
from app.db import get_session
from app.models import CandidateProfile, Job, ScoredJob

router = APIRouter(prefix="/matches", tags=["matches"])

# Cities/regions we count as the San Francisco Bay Area. Kept explicit (rather
# than a fuzzy "CA" match) so a Los Angeles or San Diego role doesn't slip in.
BAY_AREA_CITIES: set[str] = {
    "san francisco", "sf", "bay area", "south san francisco", "redwood city",
    "palo alto", "east palo alto", "mountain view", "menlo park", "sunnyvale",
    "santa clara", "san jose", "oakland", "berkeley", "emeryville", "cupertino",
    "fremont", "san mateo", "foster city", "burlingame", "belmont", "millbrae",
    "daly city", "hayward", "alameda", "brisbane", "san bruno", "los altos",
    "campbell", "milpitas", "newark", "union city", "pleasanton", "walnut creek",
}


def _wants_bay_area(location_filter: str) -> bool:
    lf = location_filter.lower()
    return "bay area" in lf or "san francisco" in lf or lf == "sf"


def _in_bay_area(job_location: str) -> bool:
    loc = job_location.lower()
    return any(city in loc for city in BAY_AREA_CITIES)


def _passes_filters(
    job: Job,
    *,
    min_years: float | None,
    max_years: float | None,
    location: str | None,
    employment_type: str | None,
    include_remote: bool,
) -> bool:
    # Experience range is on the job's stated *minimum* years. A job that lists
    # no minimum (0) still passes a lower bound — it's open to any level.
    req = float(job.min_years_experience or 0)
    if min_years is not None and req and req < min_years:
        return False
    if max_years is not None and req > max_years:
        return False

    if employment_type and job.employment_type and job.employment_type != employment_type:
        return False

    if location:
        if _wants_bay_area(location):
            if not (_in_bay_area(job.location) or (include_remote and job.remote)):
                return False
        else:
            if location.lower() not in job.location.lower() and not (include_remote and job.remote):
                return False

    return True


@router.get("/{profile_id}", response_model=list[ScoredJob])
def match_profile(
    profile_id: int,
    min_score: float = Query(0, ge=0, le=100),
    category: str | None = Query(None, description="Filter: AUTO_APPLY | REVIEW | REJECT"),
    min_years: float | None = Query(None, ge=0, description="Min stated experience (years)"),
    max_years: float | None = Query(None, ge=0, description="Max stated experience (years)"),
    location: str | None = Query(None, description="City/region; 'San Francisco Bay Area' expands to Bay Area cities"),
    employment_type: str | None = Query(None, description="e.g. full_time | part_time | contract | internship"),
    include_remote: bool = Query(False, description="Also include fully-remote roles when a location filter is set"),
    session: Session = Depends(get_session),
) -> list[ScoredJob]:
    profile = session.get(CandidateProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    results: list[ScoredJob] = []
    for job in session.exec(select(Job)).all():
        if not _passes_filters(
            job,
            min_years=min_years,
            max_years=max_years,
            location=location,
            employment_type=employment_type,
            include_remote=include_remote,
        ):
            continue
        score = score_job(profile, job)
        decision = decide(profile, job, score)
        if score.overall < min_score:
            continue
        if category and decision.category.value != category:
            continue
        results.append(
            ScoredJob(
                job_id=job.id,
                company=job.company,
                title=job.title,
                location=job.location,
                remote=job.remote,
                employment_type=job.employment_type,
                min_years_experience=job.min_years_experience,
                url=job.url,
                score=score,
                decision=decision,
            )
        )

    results.sort(key=lambda r: r.score.overall, reverse=True)
    return results
