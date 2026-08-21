"""Shared fixtures for the matching + decision tests."""
from __future__ import annotations

import pytest

from app.models import CandidateProfile, Job


@pytest.fixture
def profile() -> CandidateProfile:
    return CandidateProfile(
        id=1,
        name="Test Candidate",
        email="test@example.com",
        skills=["Python", "Kubernetes", "AWS", "LLM"],
        experiences=[{"company": "A", "role": "SWE", "years": 2.0}],
        education=[{"degree": "MS Computer Science"}],
        target_roles=["Machine Learning Engineer", "Software Engineer"],
        preferred_locations=["San Francisco", "Remote"],
        min_salary=150_000,
        preferred_companies=["OpenAI"],
        excluded_companies=["Evil Corp"],
    )


def make_job(**overrides) -> Job:
    base = dict(
        id=1,
        company="OpenAI",
        title="Machine Learning Engineer",
        location="San Francisco, CA",
        remote=False,
        salary_min=200_000,
        salary_max=300_000,
        skills=["Python", "Kubernetes", "AWS", "LLM"],
        min_years_experience=2,
        education_required="Bachelor",
    )
    base.update(overrides)
    return Job(**base)
