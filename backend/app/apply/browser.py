"""Playwright application agent — fills a form, then PAUSES for human review.

Hard rules baked in (PRD §25):
  * Never clicks the final submit button — the human does that.
  * Never solves/bypasses CAPTCHA; if one is detected it stops and reports.
  * Only fills fields it has a value for; unknown fields are left blank.

Playwright is an optional dependency:
    uv sync --extra browser && uv run playwright install chromium

This module is imported lazily so the rest of the app runs without it.
"""
from __future__ import annotations

from app.apply.prepare import ApplicationPlan

# Heuristic label/name fragments -> our field keys.
_FIELD_HINTS: dict[str, list[str]] = {
    "first_name": ["first name", "firstname", "given name"],
    "last_name": ["last name", "lastname", "surname", "family name"],
    "full_name": ["full name", "your name", "name"],
    "email": ["email", "e-mail"],
    "phone": ["phone", "mobile", "telephone"],
    "location": ["location", "city", "where are you"],
    "linkedin": ["linkedin"],
    "github": ["github"],
    "portfolio": ["portfolio", "website", "personal site"],
    "years_experience": ["years of experience", "years experience"],
    "work_authorized": ["authorized to work", "work authorization"],
    "requires_sponsorship": ["require sponsorship", "need sponsorship", "visa sponsorship"],
}

_CAPTCHA_MARKERS = ["captcha", "recaptcha", "hcaptcha", "cf-challenge", "are you human"]


def _value_map(plan: ApplicationPlan) -> dict[str, str]:
    return {f.field: f.value for f in plan.known_fields}


def fill_and_pause(url: str, plan: ApplicationPlan, *, headless: bool = False) -> dict:
    """Open the application page, fill known fields, and STOP before submitting.

    Returns a report of what was filled / skipped. Leaves the browser open (when
    not headless) so the user can review, answer anything remaining, and submit.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover - optional dep
        raise RuntimeError(
            "Playwright is not installed. Run:\n"
            "  uv sync --extra browser && uv run playwright install chromium"
        ) from e

    values = _value_map(plan)
    filled: list[str] = []
    skipped: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded")

        # Safety: bail out on CAPTCHA / anti-bot challenges instead of defeating them.
        content = page.content().lower()
        if any(marker in content for marker in _CAPTCHA_MARKERS):
            browser.close()
            return {
                "status": "blocked",
                "reason": "CAPTCHA / anti-bot challenge detected — stopping. Please apply manually.",
                "filled": [], "skipped": [],
            }

        for field, value in values.items():
            if _try_fill(page, field, value):
                filled.append(field)
            else:
                skipped.append(field)

        report = {
            "status": "paused_for_review",
            "message": "Fields filled. Review, answer any remaining questions, and click Submit yourself.",
            "filled": filled,
            "skipped": skipped,
            "open_questions": [q.model_dump() for q in plan.open_questions],
        }

        if not headless:
            # Hold the browser open for the human. (In a headless/automated run we
            # skip the prompt and return immediately.)
            try:
                input("\n[JobPilot] Review the form in the browser, then press Enter to close… ")
            except EOFError:
                pass
        browser.close()
        return report


def _try_fill(page, field: str, value: str) -> bool:
    """Best-effort fill of an input matching this field's label hints."""
    hints = _FIELD_HINTS.get(field, [field.replace("_", " ")])
    for hint in hints:
        # Try label association first, then placeholder, then name/aria.
        for locator in (
            page.get_by_label(hint, exact=False),
            page.get_by_placeholder(hint),
        ):
            try:
                if locator.count() > 0:
                    locator.first.fill(value)
                    return True
            except Exception:
                continue
    return False
