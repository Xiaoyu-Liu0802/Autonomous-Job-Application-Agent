"""Computed (non-persisted) types produced by the matching + decision agents."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class DecisionCategory(str, Enum):
    AUTO_APPLY = "AUTO_APPLY"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class MatchScore(BaseModel):
    """A per-dimension fit breakdown. All dimension scores are 0–100."""

    overall: float
    skills: float
    experience: float
    education: float
    role: float
    location: float
    preferences: float

    matched_skills: list[str] = []
    missing_skills: list[str] = []
    gaps: list[str] = []
    explanation: list[str] = []


class Decision(BaseModel):
    category: DecisionCategory
    confidence: float           # 0–100
    requires_human: bool
    reasons: list[str] = []


class ScoredJob(BaseModel):
    """A job paired with its match score and decision — the matcher's output."""

    job_id: int
    company: str
    title: str
    score: MatchScore
    decision: Decision
