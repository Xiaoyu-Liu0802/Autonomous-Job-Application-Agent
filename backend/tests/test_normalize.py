"""Tests for the offline job-text normalizer."""
from __future__ import annotations

from app.sources.normalize import (
    extract_education,
    extract_min_years,
    extract_salary,
    extract_skills,
    is_remote,
    normalize_job,
    strip_html,
)

SAMPLE = """
<div><p>We're hiring a <b>Backend Engineer</b>. You'll work with Python, Go, and
Kubernetes on AWS. 5+ years of experience required. Master's degree preferred.
Compensation: $180,000 - $250,000. This role is fully remote.</p></div>
"""


def test_strip_html_removes_tags_and_entities():
    assert "<" not in strip_html("<p>hi &amp; bye</p>")
    assert "hi & bye" in strip_html("<p>hi &amp; bye</p>")


def test_extract_skills_finds_known_and_aliases():
    skills = extract_skills(strip_html(SAMPLE))
    assert "Python" in skills
    assert "Go" in skills
    assert "Kubernetes" in skills
    assert "AWS" in skills


def test_go_not_matched_inside_other_words():
    # "goals" should not trip the "Go" word-boundary matcher.
    assert "Go" not in extract_skills("We value goals and good communication.")


def test_extract_min_years():
    assert extract_min_years(SAMPLE) == 5.0
    assert extract_min_years("no requirement here") == 0.0


def test_extract_education():
    assert extract_education(SAMPLE) == "Master"
    assert extract_education("PhD in ML required") == "PhD"
    assert extract_education("Bachelor's degree") == "Bachelor"
    assert extract_education("no degree mentioned") == ""


def test_extract_salary():
    lo, hi = extract_salary(SAMPLE)
    assert lo == 180_000 and hi == 250_000


def test_is_remote():
    assert is_remote("Remote - US", "") is True
    assert is_remote("New York", SAMPLE) is True  # "fully remote" in text
    assert is_remote("New York", "onsite role") is False


def test_normalize_job_end_to_end():
    job = normalize_job(
        external_id="greenhouse:acme:1", company="Acme", title="Backend Engineer",
        location="Remote", url="https://x", description=strip_html(SAMPLE), source="greenhouse",
    )
    assert job.external_id == "greenhouse:acme:1"
    assert job.remote is True
    assert job.min_years_experience == 5.0
    assert job.education_required == "Master"
    assert "Python" in job.skills
