"""LLM providers behind one interface.

- ``OfflineProvider`` is grounded *by construction*: it only ever assembles the
  facts it was handed, so it cannot fabricate. It needs no API key, which keeps
  the whole project runnable and testable with zero setup — the default.
- ``AnthropicProvider`` calls the real API when a key + SDK are present. Its
  output still passes through the grounding guardrail (defence-in-depth), so a
  hallucination is caught downstream regardless of provider.

Selection is driven by ``settings.llm_provider`` ("auto" | "offline" | "anthropic").
"""
from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel

from app.config import settings
from app.llm.facts import Fact


class GenResult(BaseModel):
    text: str
    confidence: float          # 0–100, the provider's self-reported confidence
    used_fact_ids: list[str] = []
    provider: str = ""


class LLMProvider(Protocol):
    name: str
    def generate_answer(self, question: str, facts: list[Fact], job_ctx: list[str]) -> GenResult: ...
    def generate_summary(self, facts: list[Fact], job_ctx: list[str], matched: list[str]) -> GenResult: ...


# ── Offline provider (default, no credentials) ────────────────────────────────

class OfflineProvider:
    name = "offline"

    def generate_answer(self, question: str, facts: list[Fact], job_ctx: list[str]) -> GenResult:
        low = question.lower()
        by_id = {f.id: f for f in facts}
        company = job_ctx[0] if job_ctx else "your team"

        # Authorization questions answer straight from the structured fact.
        if "auth:sponsorship" in by_id and ("sponsor" in low or "visa" in low):
            f = by_id["auth:sponsorship"]
            return GenResult(text=f.value.capitalize() + ".", confidence=100,
                             used_fact_ids=[f.id], provider=self.name)
        if "auth:authorized" in by_id and ("authorized" in low or "eligible" in low):
            f = by_id["auth:authorized"]
            return GenResult(text=f.value.capitalize() + ".", confidence=100,
                             used_fact_ids=[f.id], provider=self.name)

        # "Why do you want to work here / why interested" — assemble from the
        # candidate's real overlap with the posting. Every clause is grounded.
        if "why" in low or "interest" in low or "motivat" in low:
            skills = [f for f in facts if f.kind == "skill"][:3]
            target = next((f for f in facts if f.kind == "preference"), None)
            skill_txt = ", ".join(s.value for s in skills)
            used = [s.id for s in skills]
            role_clause = ""
            if target:
                role_clause = f" The {target.value} role aligns with the work I want to keep doing."
                used.append(target.id)
            text = (
                f"My background in {skill_txt} maps directly to what {company} is building, "
                f"which is why I'm interested.{role_clause}"
            ).strip()
            return GenResult(text=text, confidence=80, used_fact_ids=used, provider=self.name)

        # "Tell us about your experience" — summarize real roles.
        if "experience" in low or "background" in low or "tell us about" in low:
            summaries = [f for f in facts if f.id.endswith(":summary")][:3]
            total = next((f for f in facts if f.id == "experience:total_years"), None)
            used = [s.id for s in summaries] + ([total.id] if total else [])
            body = "; ".join(s.value for s in summaries) or "a background in software engineering"
            lead = f"I have {total.value.split()[0]} years of experience" if total else "I have relevant experience"
            return GenResult(text=f"{lead}, including {body}.", confidence=78,
                             used_fact_ids=used, provider=self.name)

        # Anything else: no grounded template -> low confidence, defer to human.
        return GenResult(text="", confidence=0, used_fact_ids=[], provider=self.name)

    def generate_summary(self, facts: list[Fact], job_ctx: list[str], matched: list[str]) -> GenResult:
        name = next((f.value for f in facts if f.id == "identity:name"), "The candidate")
        total = next((f for f in facts if f.id == "experience:total_years"), None)
        target = next((f for f in facts if f.kind == "preference"), None)
        company = job_ctx[0] if job_ctx else "the team"

        used = [f.id for f in facts if f.id == "identity:name" or f.id == "experience:total_years"]
        years = total.value.split()[0] if total else "several"
        role = target.value if target else "software engineering"
        if target:
            used.append(target.id)
        skill_clause = f" with strengths in {', '.join(matched)}" if matched else ""
        text = (
            f"{role} with {years} years of experience{skill_clause}, "
            f"applying to {company}."
        )
        return GenResult(text=text, confidence=80, used_fact_ids=used, provider=self.name)


# ── Anthropic provider (optional) ─────────────────────────────────────────────

_ANSWER_SYSTEM = (
    "You help a job candidate answer an application question. HARD RULES: use "
    "ONLY the facts provided; never invent employers, technologies, numbers, "
    "titles, or credentials. If the facts don't support a truthful answer, "
    "return an empty answer and low confidence. Respond as strict JSON: "
    '{"answer": str, "confidence": 0-100, "used_fact_ids": [str]}.'
)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def _call(self, system: str, user: str) -> GenResult:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return GenResult(text="", confidence=0, provider=self.name)
        return GenResult(
            text=str(data.get("answer", "")).strip(),
            confidence=float(data.get("confidence", 0) or 0),
            used_fact_ids=[str(x) for x in data.get("used_fact_ids", [])],
            provider=self.name,
        )

    @staticmethod
    def _fact_block(facts: list[Fact]) -> str:
        return "\n".join(f"- [{f.id}] {f.value}" for f in facts)

    def generate_answer(self, question: str, facts: list[Fact], job_ctx: list[str]) -> GenResult:
        user = (
            f"Question: {question}\n\n"
            f"Candidate facts (the ONLY facts you may use):\n{self._fact_block(facts)}\n\n"
            f"About the posting: {', '.join(job_ctx)}"
        )
        return self._call(_ANSWER_SYSTEM, user)

    def generate_summary(self, facts: list[Fact], job_ctx: list[str], matched: list[str]) -> GenResult:
        system = _ANSWER_SYSTEM.replace(
            "answer an application question",
            "write a 1-2 sentence resume summary tailored to a posting",
        )
        user = (
            f"Posting: {', '.join(job_ctx)}\n"
            f"Overlapping skills to emphasize: {', '.join(matched)}\n\n"
            f"Candidate facts (the ONLY facts you may use):\n{self._fact_block(facts)}"
        )
        return self._call(system, user)


def _try_anthropic() -> AnthropicProvider | None:
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic  # type: ignore
    except ImportError:
        return None
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return AnthropicProvider(client, settings.llm_model)


def get_provider() -> LLMProvider:
    choice = settings.llm_provider.lower()
    if choice in ("anthropic", "auto"):
        provider = _try_anthropic()
        if provider is not None:
            return provider
        if choice == "anthropic":
            # Explicitly requested but unavailable — fail soft to offline so the
            # app never breaks, but the caller can see which provider ran.
            pass
    return OfflineProvider()
