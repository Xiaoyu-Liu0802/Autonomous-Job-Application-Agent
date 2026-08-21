"""Candidate profile — the structured source of truth for application answers."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel
from sqlmodel import JSON, Column, Field, SQLModel


class Experience(BaseModel):
    company: str
    role: str
    years: float = 0.0
    description: str = ""


class Education(BaseModel):
    degree: str          # e.g. "MS Electrical Engineering"
    school: str = ""
    field: str = ""


class WorkAuthorization(BaseModel):
    country: str = "United States"
    authorized: bool = True
    sponsorship_required: bool = False


class CandidateProfile(SQLModel, table=True):
    """Structured candidate profile derived from a resume + preferences.

    Nested/list fields are persisted as JSON columns to keep the MVP schema
    simple; they are validated through the Pydantic models above at the API
    and agent layers.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # Identity & contact
    name: str
    email: str
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""

    # Background
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    experiences: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    education: list[dict] = Field(default_factory=list, sa_column=Column(JSON))

    # Search preferences
    target_roles: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    preferred_locations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    experience_levels: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    min_salary: int = 0

    # Constraints
    work_authorization: dict = Field(default_factory=dict, sa_column=Column(JSON))
    preferred_companies: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    excluded_companies: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    @property
    def total_experience_years(self) -> float:
        return round(sum(float(e.get("years", 0) or 0) for e in self.experiences), 1)
