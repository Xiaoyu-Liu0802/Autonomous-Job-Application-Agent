"""Job source interface. Every adapter returns normalized ``Job`` objects so the
discovery service and scoring engine stay source-agnostic."""
from __future__ import annotations

from typing import Protocol

import httpx

from app.models import Job

HTTP_TIMEOUT = 20.0
USER_AGENT = "JobPilot/0.2 (+https://github.com/Xiaoyu-Liu0802/Autonomous-Job-Application-Agent)"


def http_get_json(url: str) -> dict | list:
    resp = httpx.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()


class JobSource(Protocol):
    name: str

    def fetch(self) -> list[Job]:
        """Fetch and normalize current postings. May raise on network errors."""
        ...
