"""Tests for the decision engine routing (AUTO_APPLY / REVIEW / REJECT)."""
from __future__ import annotations

from app.agents import decide, score_job
from app.models import DecisionCategory
from tests.conftest import make_job


def test_clean_strong_fit_auto_applies(profile):
    job = make_job()
    decision = decide(profile, job, score_job(profile, job))
    assert decision.category == DecisionCategory.AUTO_APPLY
    assert decision.requires_human is False


def test_strong_fit_with_gap_needs_review(profile):
    # Add a missing skill -> a gap -> must not auto-apply even if overall is high.
    job = make_job(skills=["Python", "Kubernetes", "AWS", "LLM", "Rust"])
    score = score_job(profile, job)
    decision = decide(profile, job, score)
    assert decision.category == DecisionCategory.REVIEW
    assert decision.requires_human is True


def test_excluded_company_is_rejected(profile):
    job = make_job(company="Evil Corp")
    decision = decide(profile, job, score_job(profile, job))
    assert decision.category == DecisionCategory.REJECT
    assert decision.confidence == 99.0


def test_below_salary_floor_is_rejected(profile):
    job = make_job(salary_min=90_000, salary_max=120_000)
    decision = decide(profile, job, score_job(profile, job))
    assert decision.category == DecisionCategory.REJECT


def test_weak_fit_is_rejected(profile):
    job = make_job(
        title="Registered Nurse",
        skills=["Nursing", "Patient Care"],
        min_years_experience=5,
        location="Austin, TX",
        company="Some Hospital",
    )
    decision = decide(profile, job, score_job(profile, job))
    assert decision.category == DecisionCategory.REJECT


def test_confidence_is_bounded(profile):
    job = make_job()
    decision = decide(profile, job, score_job(profile, job))
    assert 0.0 <= decision.confidence <= 99.0
