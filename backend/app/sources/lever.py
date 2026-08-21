"""Lever public postings API adapter.

Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
"""
from __future__ import annotations

from app.models import Job
from app.sources.base import http_get_json
from app.sources.normalize import normalize_job, strip_html

API = "https://api.lever.co/v0/postings/{company}?mode=json"


class LeverSource:
    name = "lever"

    def __init__(self, token: str) -> None:
        self.token = token

    def fetch(self) -> list[Job]:
        data = http_get_json(API.format(company=self.token))
        # Lever returns a list; an invalid board returns {"ok": false, ...}.
        if not isinstance(data, list):
            raise ValueError(f"Lever board '{self.token}' not found or returned no list")
        jobs: list[Job] = []
        for p in data:
            categories = p.get("categories") or {}
            description = p.get("descriptionPlain") or strip_html(p.get("description", ""))
            jobs.append(
                normalize_job(
                    external_id=f"lever:{self.token}:{p['id']}",
                    company=self.token.replace("-", " ").title(),
                    title=p.get("text", ""),
                    location=categories.get("location", ""),
                    url=p.get("hostedUrl", ""),
                    description=description,
                    source="lever",
                    date_posted="",
                )
            )
        return jobs
