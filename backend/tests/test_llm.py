"""Tests for the LLM layer (Milestone 5): grounding guardrail, grounded answer
reasoning, resume tailoring, and the prepare-flow integration. All run against
the deterministic offline provider — no API key, no network."""
from __future__ import annotations

from app.apply import prepare_application
from app.llm import (
    draft_answer,
    get_provider,
    matched_skills,
    profile_facts,
    tailor_resume,
    verify_grounding,
)
from app.llm.provider import GenResult, OfflineProvider

from tests.conftest import make_job


# ── Guardrail ────────────────────────────────────────────────────────────────

def test_guardrail_passes_grounded_text():
    sources = ["Python", "Kubernetes", "OpenAI", "5 years of experience"]
    report = verify_grounding("I have 5 years with Python and Kubernetes at OpenAI.", sources)
    assert report.grounded
    assert report.violations == []


def test_guardrail_flags_invented_company_and_number():
    sources = ["Python", "OpenAI"]
    report = verify_grounding("I led a team of 12 at Google using Rust.", sources)
    assert not report.grounded
    assert "Google" in report.ungrounded_terms
    assert "Rust" in report.ungrounded_terms
    assert "12" in report.ungrounded_numbers


def test_guardrail_flags_invented_percentage():
    report = verify_grounding("I improved latency by 40%.", ["improved latency"])
    assert not report.grounded
    assert "40%" in report.ungrounded_numbers


def test_guardrail_allows_sentence_initial_capitalization():
    # "My" starts a sentence; must not be flagged as an invented entity.
    report = verify_grounding("My work used Python.", ["Python"])
    assert report.grounded


# ── Offline provider defaults ──────────────────────────────────────────────────

def test_default_provider_is_offline_without_key():
    assert get_provider().name == "offline"


# ── Answer reasoning ────────────────────────────────────────────────────────

def test_sponsorship_answered_from_profile(profile):
    profile.work_authorization = {"authorized": True, "sponsorship_required": False}
    d = draft_answer(profile, make_job(), "Will you require visa sponsorship?")
    assert d.auto_fillable
    assert d.grounded
    assert "does not require sponsorship" in d.answer.lower()


def test_salary_question_always_routed_to_human(profile):
    d = draft_answer(profile, make_job(), "What is your expected salary?")
    assert d.needs_human
    assert not d.auto_fillable
    assert d.answer == ""


def test_why_question_is_grounded_and_fillable(profile):
    d = draft_answer(profile, make_job(company="OpenAI"), "Why do you want to work here?")
    assert d.grounded
    assert d.auto_fillable
    assert "OpenAI" in d.answer


def test_unknown_question_defers_to_human(profile):
    d = draft_answer(profile, make_job(), "Describe a conflict with a coworker.")
    assert d.needs_human
    assert d.answer == ""


def test_fabricated_draft_is_caught_and_not_fillable(profile):
    class Fabricator(OfflineProvider):
        name = "test-fabricator"
        def generate_answer(self, question, facts, job_ctx):
            return GenResult(text="I led 30 engineers at Google.", confidence=99,
                             provider=self.name)

    d = draft_answer(profile, make_job(), "Tell me about your leadership.", provider=Fabricator())
    assert not d.grounded
    assert d.needs_human
    assert not d.auto_fillable
    assert d.violations  # guardrail explained why


def test_low_confidence_draft_routed_to_human(profile):
    class Unsure(OfflineProvider):
        name = "test-unsure"
        def generate_answer(self, question, facts, job_ctx):
            # Fully grounded but low confidence -> human confirms.
            return GenResult(text="I use Python.", confidence=10, provider=self.name)

    d = draft_answer(profile, make_job(), "What languages do you use?", provider=Unsure())
    assert d.grounded
    assert d.needs_human
    assert not d.auto_fillable


# ── Resume tailoring ──────────────────────────────────────────────────────────

def test_tailor_resume_highlights_overlap_and_stays_grounded(profile):
    job = make_job(skills=["Python", "Kubernetes", "Go"])
    resume = tailor_resume(profile, job)
    assert resume.grounded
    assert set(resume.highlighted_skills) == {"Python", "Kubernetes"}
    assert "Go" in resume.missing_skills  # honest about the gap
    assert resume.violations == []


def test_matched_skills_helper(profile):
    assert set(matched_skills(profile, make_job(skills=["Python", "Ruby"]))) == {"Python"}


def test_profile_facts_are_enumerated(profile):
    ids = {f.id for f in profile_facts(profile)}
    assert "identity:name" in ids
    assert "skill:python" in ids


# ── Prepare-flow integration ───────────────────────────────────────────────────

def test_prepare_promotes_grounded_answer_to_field(profile):
    job = make_job(company="OpenAI")
    plan = prepare_application(profile, custom_questions=["Why do you want to work here?"], job=job)
    fields = {f.field for f in plan.known_fields}
    assert "Why do you want to work here?" in fields  # grounded -> auto-filled


def test_prepare_without_job_leaves_question_open(profile):
    plan = prepare_application(profile, custom_questions=["Why do you want to work here?"])
    open_qs = {q.question for q in plan.open_questions}
    assert "Why do you want to work here?" in open_qs  # no LLM without a job


def test_prepare_keeps_salary_open_even_with_job(profile):
    plan = prepare_application(profile, custom_questions=["Expected salary?"], job=make_job())
    assert any("salary" in q.question.lower() for q in plan.open_questions)
