"""LLM layer — grounded answer reasoning + resume tailoring with a hard
anti-fabrication guardrail (PRD §16). Runs with zero credentials via the
deterministic offline provider; upgrades to the Anthropic API when configured."""
from app.llm.answers import DraftedAnswer, draft_answer
from app.llm.facts import Fact, job_context, matched_skills, profile_facts
from app.llm.guardrails import GroundingReport, verify_grounding
from app.llm.provider import GenResult, LLMProvider, get_provider
from app.llm.resume import ResumeBullet, TailoredResume, tailor_resume

__all__ = [
    "DraftedAnswer",
    "draft_answer",
    "Fact",
    "profile_facts",
    "job_context",
    "matched_skills",
    "GroundingReport",
    "verify_grounding",
    "GenResult",
    "LLMProvider",
    "get_provider",
    "ResumeBullet",
    "TailoredResume",
    "tailor_resume",
]
