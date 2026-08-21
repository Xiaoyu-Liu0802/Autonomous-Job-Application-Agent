"""Greenhouse public job-board API adapter.

Docs: https://developers.greenhouse.io/job-board.html
Endpoint: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
"""
from __future__ import annotations

from app.models import Job
from app.sources.base import http_get_json
from app.sources.normalize import normalize_job, strip_html

API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"


class GreenhouseSource:
    name = "greenhouse"

    def __init__(self, token: str) -> None:
        self.token = token

    def fetch(self) -> list[Job]:
        data = http_get_json(API.format(token=self.token))
        jobs: list[Job] = []
        for j in data.get("jobs", []):
            jobs.append(
                normalize_job(
                    external_id=f"greenhouse:{self.token}:{j['id']}",
                    company=j.get("company_name") or self.token.replace("-", " ").title(),
                    title=j.get("title", ""),
                    location=(j.get("location") or {}).get("name", ""),
                    url=j.get("absolute_url", ""),
                    description=strip_html(j.get("content", "")),
                    source="greenhouse",
                    date_posted=(j.get("first_published") or "")[:10],
                )
            )
        return jobs
