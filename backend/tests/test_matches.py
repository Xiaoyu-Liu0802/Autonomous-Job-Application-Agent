"""Tests for the hard filters on the /matches endpoint (experience range,
location, employment type). Exercises the pure filter predicate directly so no
DB or network is needed."""
from __future__ import annotations

from app.api.matches import _in_bay_area, _passes_filters, _wants_bay_area
from tests.conftest import make_job

# Sensible defaults matching the UI: 2–5 yrs, SF Bay Area, full-time, no remote.
DEFAULTS = dict(
    min_years=2.0, max_years=5.0, location="San Francisco Bay Area",
    employment_type="full_time", include_remote=False,
)


def _passes(job, **over):
    return _passes_filters(job, **{**DEFAULTS, **over})


def test_wants_bay_area_recognizes_phrasing():
    assert _wants_bay_area("San Francisco Bay Area")
    assert _wants_bay_area("sf")
    assert not _wants_bay_area("Austin, TX")


def test_in_bay_area_matches_cities_but_not_other_ca():
    assert _in_bay_area("Palo Alto, CA")
    assert _in_bay_area("San Francisco, CA")
    assert not _in_bay_area("Los Angeles, CA")


def test_bay_area_job_full_time_mid_level_passes():
    job = make_job(location="San Francisco, CA", employment_type="full_time", min_years_experience=3)
    assert _passes(job)


def test_experience_below_range_filtered():
    # A job requiring 8 yrs is above the 2–5 window.
    job = make_job(location="San Francisco, CA", employment_type="full_time", min_years_experience=8)
    assert not _passes(job)


def test_zero_min_years_still_passes_lower_bound():
    # "No minimum stated" (0) shouldn't be excluded by a lower bound of 2.
    job = make_job(location="San Francisco, CA", employment_type="full_time", min_years_experience=0)
    assert _passes(job)


def test_non_bay_area_location_filtered():
    job = make_job(location="Austin, TX", employment_type="full_time", min_years_experience=3)
    assert not _passes(job)


def test_internship_filtered_when_full_time_requested():
    job = make_job(location="San Francisco, CA", employment_type="internship", min_years_experience=0)
    assert not _passes(job)


def test_remote_excluded_by_default_but_included_with_flag():
    job = make_job(location="Remote", remote=True, employment_type="full_time", min_years_experience=3)
    assert not _passes(job)
    assert _passes(job, include_remote=True)


def test_no_filters_passes_everything():
    job = make_job(location="Austin, TX", employment_type="internship", min_years_experience=10)
    assert _passes_filters(
        job, min_years=None, max_years=None, location=None,
        employment_type=None, include_remote=False,
    )
