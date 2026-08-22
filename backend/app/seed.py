"""Seed the DB with the candidate profile only.

The profile is Xiaoyu Liu's real background and drives all fit scoring. Jobs are
intentionally *not* seeded — they come exclusively from real ATS discovery
(/discovery/run), so the dashboard never shows fabricated demo postings.
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.models import CandidateProfile


def _sample_profile() -> CandidateProfile:
    return CandidateProfile(
        name="Xiaoyu Liu",
        email="xl3129@columbia.edu",
        phone="646-226-5805",
        location="Redwood City, CA",
        linkedin="https://www.linkedin.com/in/xiaoyu-l/",
        github="https://github.com/Xiaoyu-Liu0802",
        skills=[
            "Java", "Python", "Go", "Kotlin", "C++", "JavaScript",
            "Spring Boot", "gRPC", "GraphQL", "Kafka", "Redis", "Microservices",
            "AWS", "GCP", "Docker", "Kubernetes",
            "PostgreSQL", "MongoDB", "HBase",
            "React", "Node.js", "LLM", "RAG", "MCP", "Agentic Workflows",
        ],
        experiences=[
            {"company": "Salesforce", "role": "Software Engineer", "years": 1.5,
             "description": "Distributed Revenue Cloud CPQ services; multi-tenant K8s architecture; agentic testing framework."},
            {"company": "Veeva Systems", "role": "Software Engineer", "years": 2.2,
             "description": "Java/Spring Boot on AWS; Kafka data-migration pipelines; ElastiCache + S3 content distribution."},
            {"company": "Meta", "role": "Software Engineer (Intern)", "years": 0.3,
             "description": "Messenger Media Gallery on Android (Kotlin/SQLite); E2E-encrypted media pipeline."},
        ],
        education=[
            {"degree": "MS Electrical Engineering", "school": "Columbia University", "field": "EE"},
            {"degree": "BEng Electronics and Information Engineering", "school": "HK PolyU", "field": "EIE"},
        ],
        target_roles=["Software Engineer", "Machine Learning Engineer", "AI Engineer", "Backend Engineer"],
        preferred_locations=["San Francisco Bay Area", "San Francisco", "Redwood City", "Remote"],
        experience_levels=["Entry Level", "Mid Level"],
        min_salary=150_000,
        work_authorization={"country": "United States", "authorized": True, "sponsorship_required": False},
        preferred_companies=["OpenAI", "Anthropic", "Google", "AI startups"],
        excluded_companies=["Acme Defense Systems"],
    )


def seed_if_empty(session: Session) -> bool:
    """Insert the candidate profile only if there's none yet. Returns True if
    seeded. Jobs are never seeded — they come from real ATS discovery."""
    existing = session.exec(select(CandidateProfile)).first()
    if existing:
        return False
    session.add(_sample_profile())
    session.commit()
    return True
