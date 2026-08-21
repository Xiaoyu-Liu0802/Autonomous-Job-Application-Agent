"""Ashby public job-board API adapter.

Endpoint: https://api.ashbyhq.com/posting-api/job-board/{company}
"""
from __future__ import annotations

from app.models import Job
from app.sources.base import http_get_json
from app.sources.normalize import normalize_job, strip_html

API = "https://api.ashbyhq.com/posting-api/job-board/{company}?includeCompensation=true"


class AshbySource:
    name = "ashby"

    def __init__(self, token: str) -> None:
        self.token = token

    def fetch(self) -> list[Job]:
        data = http_get_json(API.format(company=self.token))
        jobs: list[Job] = []
        for j in data.get("jobs", []):
            if j.get("isListed") is False:
                continue
            description = j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", ""))
            job = normalize_job(
                external_id=f"ashby:{self.token}:{j['id']}",
                company=self.token.replace("-", " ").title(),
                title=j.get("title", ""),
                location=j.get("location", ""),
                url=j.get("jobUrl") or j.get("applyUrl", ""),
                description=description,
                source="ashby",
                date_posted=(j.get("publishedAt") or "")[:10],
            )
            # Ashby exposes an explicit remote flag; trust it when present.
            if j.get("isRemote"):
                job.remote = True
            jobs.append(job)
        return jobs
