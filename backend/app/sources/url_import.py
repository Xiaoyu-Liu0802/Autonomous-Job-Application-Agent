"""Import a single job from a pasted URL.

If the URL is a known ATS posting (Greenhouse / Lever / Ashby) we call that
platform's official API for clean structured data. Otherwise — including
LinkedIn / Indeed / Jobright links — we do a best-effort fetch of the public
page and parse what we can, flagging the result as low-confidence.

We never log in, bypass anti-bot protection, or scrape behind auth. If a page
blocks anonymous access, the import fails loudly and asks the user to paste the
job details manually.
"""
from __future__ import annotations

import re

import httpx

from app.models import Job
from app.sources.base import HTTP_TIMEOUT, USER_AGENT, http_get_json
from app.sources.normalize import normalize_job, strip_html

_GREENHOUSE = re.compile(r"greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+).*?jobs?/(\d+)", re.IGNORECASE)
_GREENHOUSE2 = re.compile(r"boards\.greenhouse\.io/([\w-]+)/jobs/(\d+)", re.IGNORECASE)
_LEVER = re.compile(r"jobs\.lever\.co/([\w-]+)/([\w-]+)", re.IGNORECASE)
_ASHBY = re.compile(r"jobs\.ashbyhq\.com/([\w-]+)/([\w-]+)", re.IGNORECASE)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class ImportError_(Exception):
    """Raised when a URL can't be imported (blocked, unparseable, unsupported)."""


def import_from_url(url: str) -> Job:
    for pat in (_GREENHOUSE2, _GREENHOUSE):
        m = pat.search(url)
        if m:
            return _greenhouse_one(m.group(1), m.group(2))
    if m := _LEVER.search(url):
        return _lever_one(m.group(1), m.group(2))
    if m := _ASHBY.search(url):
        return _ashby_one(m.group(1), m.group(2))
    return _generic(url)


def _greenhouse_one(token: str, job_id: str) -> Job:
    j = http_get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}")
    return normalize_job(
        external_id=f"greenhouse:{token}:{j['id']}",
        company=j.get("company_name") or token.title(),
        title=j.get("title", ""),
        location=(j.get("location") or {}).get("name", ""),
        url=j.get("absolute_url", ""),
        description=strip_html(j.get("content", "")),
        source="greenhouse",
    )


def _lever_one(company: str, job_id: str) -> Job:
    j = http_get_json(f"https://api.lever.co/v0/postings/{company}/{job_id}?mode=json")
    categories = j.get("categories") or {}
    return normalize_job(
        external_id=f"lever:{company}:{j['id']}",
        company=company.title(),
        title=j.get("text", ""),
        location=categories.get("location", ""),
        url=j.get("hostedUrl", ""),
        description=j.get("descriptionPlain") or strip_html(j.get("description", "")),
        source="lever",
    )


def _ashby_one(company: str, job_id: str) -> Job:
    data = http_get_json(f"https://api.ashbyhq.com/posting-api/job-board/{company}?includeCompensation=true")
    for j in data.get("jobs", []):
        if str(j.get("id")) == job_id:
            return normalize_job(
                external_id=f"ashby:{company}:{j['id']}",
                company=company.title(),
                title=j.get("title", ""),
                location=j.get("location", ""),
                url=j.get("jobUrl") or j.get("applyUrl", ""),
                description=j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", "")),
                source="ashby",
            )
    raise ImportError_(f"Ashby job {job_id} not found on board '{company}'")


def _generic(url: str) -> Job:
    """Best-effort parse for non-ATS URLs (LinkedIn/Indeed/Jobright/etc.).

    These sites usually block anonymous scraping; when they do, we surface a
    clear error rather than pretending to have data.
    """
    try:
        resp = httpx.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise ImportError_(
            f"Couldn't fetch this URL ({e}). Sites like LinkedIn/Indeed often block "
            "automated access — paste the job title, company, and description manually instead."
        ) from e

    text = strip_html(resp.text)
    title_match = _TITLE_RE.search(resp.text)
    title = strip_html(title_match.group(1)) if title_match else "Imported job"
    slug = re.sub(r"[^\w-]", "-", url)[-40:]
    return normalize_job(
        external_id=f"url:{slug}",
        company="(unknown — please edit)",
        title=title[:120],
        location="",
        url=url,
        description=text[:4000],
        source="url",
        application_method="external",
    )
