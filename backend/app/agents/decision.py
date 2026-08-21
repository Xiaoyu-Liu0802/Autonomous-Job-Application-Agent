"""Decision engine — routes a scored job into AUTO_APPLY / REVIEW / REJECT.

Encodes the policy from PRD §10, plus the safety bias from §14/§25: when in
doubt, escalate to a human rather than guess. The agent never optimizes purely
for completion rate.
"""
from __future__ import annotations

from app.models import CandidateProfile, Decision, DecisionCategory, Job, MatchScore

AUTO_APPLY_THRESHOLD = 85.0
REVIEW_THRESHOLD = 70.0


def _violates_constraints(profile: CandidateProfile, job: Job) -> list[str]:
    """Hard constraints that force a REJECT regardless of fit."""
    violations: list[str] = []
    company = job.company.lower()
    if any(company == c.lower() for c in profile.excluded_companies):
        violations.append(f"{job.company} is on your excluded list.")
    if profile.min_salary and job.salary_max and job.salary_max < profile.min_salary:
        violations.append(
            f"Max salary ${job.salary_max:,} is below your ${profile.min_salary:,} minimum."
        )
    return violations


def _confidence(overall: float) -> float:
    """Confidence that the *category* is correct — highest far from a threshold,
    lowest right at one."""
    dist = min(abs(overall - AUTO_APPLY_THRESHOLD), abs(overall - REVIEW_THRESHOLD))
    return round(min(99.0, 60.0 + dist * 2.6), 1)


def decide(profile: CandidateProfile, job: Job, score: MatchScore) -> Decision:
    reasons: list[str] = []

    violations = _violates_constraints(profile, job)
    if violations:
        return Decision(
            category=DecisionCategory.REJECT,
            confidence=99.0,
            requires_human=False,
            reasons=violations,
        )

    if score.overall < REVIEW_THRESHOLD:
        return Decision(
            category=DecisionCategory.REJECT,
            confidence=_confidence(score.overall),
            requires_human=False,
            reasons=[f"Fit score {score.overall} is below the {REVIEW_THRESHOLD} threshold.", *score.gaps],
        )

    if score.overall <= AUTO_APPLY_THRESHOLD:
        return Decision(
            category=DecisionCategory.REVIEW,
            confidence=_confidence(score.overall),
            requires_human=True,
            reasons=[f"Borderline fit ({score.overall}). Your review recommended.", *score.gaps],
        )

    # Strong fit. Auto-apply only if nothing needs a human judgement call.
    if score.gaps:
        return Decision(
            category=DecisionCategory.REVIEW,
            confidence=_confidence(score.overall),
            requires_human=True,
            reasons=[f"Strong fit ({score.overall}), but some items need your confirmation.", *score.gaps],
        )

    return Decision(
        category=DecisionCategory.AUTO_APPLY,
        confidence=_confidence(score.overall),
        requires_human=False,
        reasons=[f"High-confidence fit ({score.overall}) with no blocking gaps."],
    )
