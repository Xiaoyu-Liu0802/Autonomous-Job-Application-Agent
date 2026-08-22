"""Seed the DB with a sample candidate profile + a spread of jobs.

The sample profile is Xiaoyu Liu's real background, and the jobs are crafted to
exercise every decision branch: clear AUTO_APPLY, borderline REVIEW, salary /
excluded-company REJECT, and a location mismatch.
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.models import CandidateProfile, Job


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


def _sample_jobs() -> list[Job]:
    # Real companies link to their live careers pages. The fictional demo
    # companies (DataCorp / Acme / Seedling) have no real posting, so they carry
    # no URL — the dashboard simply omits the "View posting" link for them.
    return [
        Job(  # Strong, clean fit -> AUTO_APPLY
            external_id="openai-mle-001", company="OpenAI", title="Machine Learning Engineer",
            location="San Francisco, CA", remote=False, salary_min=200_000, salary_max=320_000,
            url="https://openai.com/careers/", source="greenhouse", application_method="ats",
            description="Build and scale ML infrastructure for frontier models.",
            requirements=["Distributed systems", "ML infrastructure", "Production experience"],
            skills=["Python", "LLM", "Kubernetes", "AWS", "RAG"],
            min_years_experience=2, education_required="Bachelor", date_posted="2026-08-18",
        ),
        Job(  # Great fit but a missing skill -> REVIEW (gap needs confirmation)
            external_id="anthropic-swe-002", company="Anthropic", title="Software Engineer, Backend",
            location="San Francisco, CA", remote=True, salary_min=210_000, salary_max=340_000,
            url="https://www.anthropic.com/careers", source="greenhouse", application_method="ats",
            description="Backend systems for Claude products.",
            requirements=["Distributed systems", "Go or Python", "Terraform"],
            skills=["Go", "Python", "Kubernetes", "gRPC", "Terraform"],
            min_years_experience=3, education_required="Bachelor", date_posted="2026-08-19",
        ),
        Job(  # Solid -> AUTO_APPLY / high
            external_id="google-swe-003", company="Google", title="Software Engineer",
            location="Mountain View, CA", remote=False, salary_min=180_000, salary_max=280_000,
            url="https://www.google.com/about/careers/applications/", source="google", application_method="ats",
            description="Backend services at scale.",
            requirements=["Java or C++", "Distributed systems"],
            skills=["Java", "C++", "Kubernetes", "PostgreSQL"],
            min_years_experience=2, education_required="Bachelor", date_posted="2026-08-18",
        ),
        Job(  # Borderline title + location mismatch -> REVIEW/REJECT
            external_id="datacorp-ds-004", company="DataCorp", title="Senior Data Scientist",
            location="Austin, TX", remote=False, salary_min=160_000, salary_max=210_000,
            url="", source="lever", application_method="external",
            description="Statistical modeling and experimentation.",
            requirements=["Statistics", "R or Python", "5+ years"],
            skills=["Python", "R", "Statistics", "SQL"],
            min_years_experience=5, education_required="Master", date_posted="2026-08-15",
        ),
        Job(  # Excluded company -> REJECT
            external_id="acme-swe-005", company="Acme Defense Systems", title="Software Engineer",
            location="Remote", remote=True, salary_min=170_000, salary_max=230_000,
            url="", source="user", application_method="external",
            description="Mission systems software.",
            requirements=["C++", "Security clearance"],
            skills=["C++", "Python"],
            min_years_experience=2, education_required="Bachelor", date_posted="2026-08-14",
        ),
        Job(  # Below salary floor -> REJECT
            external_id="startup-swe-006", company="Seedling AI", title="Founding Software Engineer",
            location="Remote", remote=True, salary_min=110_000, salary_max=140_000,
            url="", source="user", application_method="email",
            description="Early-stage AI startup, wear many hats.",
            requirements=["Full-stack", "LLM apps"],
            skills=["Python", "React", "LLM", "RAG", "MCP"],
            min_years_experience=1, education_required="", date_posted="2026-08-20",
        ),
    ]


def seed_if_empty(session: Session) -> bool:
    """Insert sample data only if there's no profile yet. Returns True if seeded."""
    existing = session.exec(select(CandidateProfile)).first()
    if existing:
        return False
    session.add(_sample_profile())
    for job in _sample_jobs():
        session.add(job)
    session.commit()
    return True
