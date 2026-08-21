"""Tests for application preparation + human-in-the-loop question routing."""
from __future__ import annotations

from app.apply import prepare_application
from app.apply.prepare import OpenQuestion, PlannedField, classify_question


def test_known_fields_from_profile(profile):
    profile.work_authorization = {"authorized": True, "sponsorship_required": False}
    plan = prepare_application(profile)
    fields = {f.field: f.value for f in plan.known_fields}
    assert fields["email"] == profile.email
    assert fields["work_authorized"] == "Yes"
    assert fields["requires_sponsorship"] == "No"


def test_sponsorship_question_answered_from_profile(profile):
    profile.work_authorization = {"authorized": True, "sponsorship_required": False}
    result = classify_question("Will you now or in the future require sponsorship?", profile, {})
    assert isinstance(result, PlannedField)
    assert result.value == "No"


def test_salary_question_goes_to_human(profile):
    result = classify_question("What is your expected salary?", profile, {})
    assert isinstance(result, OpenQuestion)


def test_demographic_question_goes_to_human(profile):
    result = classify_question("What is your gender?", profile, {})
    assert isinstance(result, OpenQuestion)


def test_saved_answer_is_reused(profile):
    saved = {"What is your expected salary?": "$180,000"}
    result = classify_question("What is your expected salary?", profile, saved)
    assert isinstance(result, PlannedField)
    assert result.value == "$180,000"


def test_plan_not_ready_when_open_questions(profile):
    plan = prepare_application(profile, custom_questions=["Why do you want to work here?"])
    assert plan.ready_to_submit is False
    assert len(plan.open_questions) == 1
