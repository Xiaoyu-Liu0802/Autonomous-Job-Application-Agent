"""A discovered job opportunity."""
from __future__ import annotations

from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # Dedup key: stable identifier from the source (URL slug, ATS id, ...).
    external_id: str = Field(default="", index=True)

    company: str
    title: str
    location: str = ""
    remote: bool = False

    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    url: str = ""
    description: str = ""
    requirements: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    min_years_experience: float = 0.0
    education_required: str = ""   # "", "Bachelor", "Master", "PhD"

    date_posted: str = ""
    source: str = ""               # "greenhouse", "lever", "user", ...
    application_method: str = ""   # "external", "ats", "email"
