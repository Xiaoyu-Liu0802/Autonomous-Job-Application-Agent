"""Answer reasoning (PRD §16) — draft a grounded answer to an application
question, or refuse and route to the human.

The pipeline is: classify sensitivity → generate (offline or Anthropic) →
verify grounding → gate on confidence. An answer is only ever marked
``auto_fillable`` when it is (a) not sensitive, (b) fully grounded in the
profile/posting, and (c) above the confidence floor. Everything else becomes a
*suggestion* the human reviews — the agent never guesses on the record.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from app.config import settings
from app.llm.facts import Fact, job_context, profile_facts
from app.llm.guardrails import verify_grounding
from app.llm.provider import LLMProvider, get_provider
from app.models import CandidateProfile, Job

# Questions we never answer autonomously — compensation & protected/demographic.
_SENSITIVE = re.compile(
    r"salary|compensation|expected pay|desired pay|gender|race|ethnicit|veteran|"
    r"disabilit|sexual orientation|date of birth|age\b",
    re.IGNORECASE,
)


class DraftedAnswer(BaseModel):
    question: str
    answer: str
    confidence: float
    grounded: bool
    auto_fillable: bool
    needs_human: bool
    reason: str
    used_facts: list[str] = []
    violations: list[str] = []
    provider: str = ""


def draft_answer(
    profile: CandidateProfile,
    job: Job,
    question: str,
    provider: LLMProvider | None = None,
) -> DraftedAnswer:
    provider = provider or get_provider()
    q = question.strip()

    if _SENSITIVE.search(q):
        return DraftedAnswer(
            question=q, answer="", confidence=0, grounded=False,
            auto_fillable=False, needs_human=True,
            reason="Compensation/demographic question — always your decision.",
            provider=provider.name,
        )

    facts = profile_facts(profile)
    job_ctx = job_context(job)
    result = provider.generate_answer(q, facts, job_ctx)

    if not result.text:
        return DraftedAnswer(
            question=q, answer="", confidence=result.confidence, grounded=False,
            auto_fillable=False, needs_human=True,
            reason="No grounded answer available from your profile.",
            provider=result.provider,
        )

    sources = [f.value for f in facts] + job_ctx
    report = verify_grounding(result.text, sources)
    known_ids = {f.id for f in facts}
    used = [fid for fid in result.used_fact_ids if fid in known_ids]

    confident = result.confidence >= settings.min_answer_confidence
    auto_fillable = report.grounded and confident
    needs_human = not auto_fillable

    if not report.grounded:
        reason = "Draft contains unverifiable claims — review before use: " + "; ".join(report.violations)
    elif not confident:
        reason = f"Confidence {result.confidence:.0f}% is below the {settings.min_answer_confidence:.0f}% bar — please confirm."
    else:
        reason = "Grounded in your profile; ready to fill."

    return DraftedAnswer(
        question=q,
        answer=result.text,
        confidence=result.confidence,
        grounded=report.grounded,
        auto_fillable=auto_fillable,
        needs_human=needs_human,
        reason=reason,
        used_facts=used,
        violations=report.violations,
        provider=result.provider,
    )
