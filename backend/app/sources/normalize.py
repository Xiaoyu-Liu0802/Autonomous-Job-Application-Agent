"""Turn raw job text from any source into a structured ``Job``.

Extraction is heuristic and deterministic (no LLM): skills come from a curated
vocabulary, years/education/salary from regexes. Good enough to feed the
scoring engine; the LLM layer (Milestone 3) can refine later.
"""
from __future__ import annotations

import html
import re

from app.models import Job

# Canonical skill vocabulary. Order matters only for readability. Entries with
# non-word characters (C++, Node.js, C#) are matched as case-insensitive
# substrings; the rest use word boundaries to avoid false hits (e.g. "go" in
# "goal").
SKILL_VOCAB: list[str] = [
    "Python", "Java", "Kotlin", "Golang", "Go", "C++", "C#", "JavaScript", "TypeScript",
    "React", "Redux", "Node.js", "Next.js", "Vue", "Angular",
    "Spring Boot", "Spring", "gRPC", "GraphQL", "REST", "Protobuf",
    "Kafka", "Redis", "RabbitMQ", "Celery", "Temporal",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
    "PostgreSQL", "MySQL", "MongoDB", "HBase", "SQLite", "DynamoDB", "Cassandra",
    "PyTorch", "TensorFlow", "CUDA", "NCCL",
    "LLM", "RAG", "MCP", "NLP", "Machine Learning", "Deep Learning",
    "Microservices", "Distributed Systems", "Playwright", "Selenium",
    "Rust", "Ruby", "Scala", "PHP", "Swift", "R", "SQL",
]

_ALIASES = {"Golang": "Go", "Spring": "Spring Boot"}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_YEARS_RE = re.compile(r"(\d+)\s*\+?\s*(?:years|yrs)\b", re.IGNORECASE)
_SALARY_RE = re.compile(r"\$\s?(\d{2,3})(?:,(\d{3})|k)\b", re.IGNORECASE)


def strip_html(raw: str) -> str:
    """Unescape HTML entities and drop tags -> plain text."""
    if not raw:
        return ""
    text = html.unescape(raw)
    text = _TAG_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def extract_skills(text: str) -> list[str]:
    found: list[str] = []
    for skill in SKILL_VOCAB:
        if re.search(r"[^\w+#.]", skill) or any(c in skill for c in "+#."):
            hit = skill.lower() in text.lower()
        else:
            hit = re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE) is not None
        if hit:
            found.append(_ALIASES.get(skill, skill))
    # De-dupe while preserving order (aliases can collide).
    seen: set[str] = set()
    return [s for s in found if not (s in seen or seen.add(s))]


def extract_min_years(text: str) -> float:
    years = [int(m.group(1)) for m in _YEARS_RE.finditer(text)]
    # Use the smallest stated requirement (job posts often list a range/min).
    return float(min(years)) if years else 0.0


def extract_education(text: str) -> str:
    low = text.lower()
    if re.search(r"\bph\.?\s?d\b|doctorate", low):
        return "PhD"
    if re.search(r"master'?s|m\.?s\.?\b|msc\b", low):
        return "Master"
    if re.search(r"bachelor'?s|b\.?s\.?\b|bsc\b|undergraduate degree", low):
        return "Bachelor"
    return ""


def extract_salary(text: str) -> tuple[int | None, int | None]:
    vals: list[int] = []
    for m in _SALARY_RE.finditer(text):
        base = int(m.group(1))
        vals.append(base * 1000 if not m.group(2) else int(m.group(1) + m.group(2)))
    if not vals:
        return None, None
    return min(vals), max(vals)


def is_remote(location: str, text: str) -> bool:
    return "remote" in location.lower() or "fully remote" in text.lower()


def normalize_job(
    *,
    external_id: str,
    company: str,
    title: str,
    location: str,
    url: str,
    description: str,
    source: str,
    application_method: str = "ats",
    date_posted: str = "",
) -> Job:
    """Assemble a ``Job`` with skills/years/education/salary inferred from text."""
    haystack = f"{title}\n{description}"
    salary_min, salary_max = extract_salary(description)
    return Job(
        external_id=external_id,
        company=company,
        title=title,
        location=location,
        remote=is_remote(location, description),
        salary_min=salary_min,
        salary_max=salary_max,
        url=url,
        description=description[:4000],  # keep rows lean
        requirements=[],
        skills=extract_skills(haystack),
        min_years_experience=extract_min_years(haystack),
        education_required=extract_education(haystack),
        date_posted=date_posted,
        source=source,
        application_method=application_method,
    )
