"""Tests for the fit-scoring engine."""
from __future__ import annotations

from app.agents import score_job
from tests.conftest import make_job


def test_perfect_fit_scores_high(profile):
    score = score_job(profile, make_job())
    assert score.overall >= 95
    assert score.skills == 100.0
    assert set(score.matched_skills) == {"Python", "Kubernetes", "AWS", "LLM"}
    assert score.missing_skills == []
    assert score.gaps == []


def test_missing_skill_lowers_skill_score_and_records_gap(profile):
    job = make_job(skills=["Python", "Kubernetes", "AWS", "LLM", "Rust"])
    score = score_job(profile, job)
    assert score.skills == 80.0  # 4 of 5
    assert "Rust" in score.missing_skills
    assert any("Rust" in g for g in score.gaps)


def test_no_listed_skills_is_neutral_not_zero(profile):
    score = score_job(profile, make_job(skills=[]))
    assert score.skills == 100.0


def test_experience_shortfall_is_partial(profile):
    # profile has 2 yrs; require 8 -> 25%
    score = score_job(profile, make_job(min_years_experience=8))
    assert score.experience == 25.0
    assert any("yrs" in g for g in score.gaps)


def test_location_mismatch_penalized(profile):
    score = score_job(profile, make_job(location="Austin, TX", remote=False))
    assert score.location == 30.0


def test_remote_job_matches_remote_preference(profile):
    score = score_job(profile, make_job(location="Anywhere", remote=True))
    assert score.location == 100.0


def test_excluded_company_zeros_preferences(profile):
    score = score_job(profile, make_job(company="Evil Corp"))
    assert score.preferences == 0.0


def test_below_salary_floor_flags_preference_gap(profile):
    score = score_job(profile, make_job(salary_min=90_000, salary_max=120_000))
    assert score.preferences <= 40.0
    assert any("below" in g for g in score.gaps)


def test_scores_are_bounded(profile):
    score = score_job(profile, make_job(company="Evil Corp", min_years_experience=20, location="Mars"))
    for dim in (score.skills, score.experience, score.education, score.role, score.location, score.preferences, score.overall):
        assert 0.0 <= dim <= 100.0
