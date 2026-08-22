"""Anti-fabrication guardrail (PRD §16 — hard safety rule: *never invent*).

Given generated text and the set of source strings it was allowed to draw on,
flag anything that looks invented: a number, a proper noun (company/tech/
credential), or a percentage that can't be traced back to a source.

This is deliberately provider-agnostic — it runs on top of *any* generator,
including the real Anthropic API, as defence-in-depth. A model that is told
"only use these facts" and does so anyway will pass; one that hallucinates a
company or a metric will be caught here regardless of how fluent it sounds.

The check is intentionally conservative about false positives (it allows a
generous stoplist of ordinary English) but strict about the two things that
matter most in a job application: **named entities and numbers**.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

# Ordinary words that may appear capitalized (sentence starts, pronoun "I", days,
# common adjectives) without implying an invented entity. Kept lowercase.
_COMMON = {
    "i", "i'm", "i've", "a", "an", "the", "and", "or", "but", "so", "as", "at",
    "in", "on", "of", "to", "for", "with", "my", "me", "we", "our", "you", "your",
    "this", "that", "these", "those", "it", "its", "is", "am", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "should", "may", "might", "must", "if", "then", "when", "while",
    "because", "since", "about", "over", "after", "before", "during", "years", "year",
    "experience", "role", "team", "work", "working", "worked", "build", "building",
    "built", "develop", "developing", "developed", "engineer", "engineering", "software",
    "system", "systems", "product", "products", "project", "projects", "company",
    "companies", "opportunity", "excited", "passionate", "strong", "deep", "focused",
    "hands", "end", "scale", "impact", "mission", "value", "values", "culture", "growth",
    "great", "excellent", "proven", "track", "record", "well", "very", "highly", "across",
    "both", "also", "not", "no", "yes", "here", "there", "which", "who", "what", "how",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
}

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+.#'-]*")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _norm(token: str) -> str:
    """Drop trailing sentence punctuation while keeping meaningful suffixes
    like ``C++`` or ``C#`` intact."""
    return token.rstrip(".'-")


class GroundingReport(BaseModel):
    grounded: bool
    ungrounded_terms: list[str]   # proper nouns not traceable to a source
    ungrounded_numbers: list[str] # numbers/percentages not traceable to a source

    @property
    def violations(self) -> list[str]:
        out = []
        if self.ungrounded_terms:
            out.append(f"Unverified names/terms: {', '.join(self.ungrounded_terms)}")
        if self.ungrounded_numbers:
            out.append(f"Unverified numbers: {', '.join(self.ungrounded_numbers)}")
        return out


def _vocab(sources: list[str]) -> set[str]:
    vocab: set[str] = set()
    for s in sources:
        for m in _WORD.finditer(s or ""):
            vocab.add(_norm(m.group()).lower())
    return vocab


def _source_numbers(sources: list[str]) -> set[str]:
    nums: set[str] = set()
    for s in sources:
        for m in _NUMBER.finditer(s or ""):
            nums.add(m.group().replace(",", "").rstrip("%"))
    return nums


def verify_grounding(text: str, sources: list[str]) -> GroundingReport:
    """Check that every proper noun and number in ``text`` is traceable to
    ``sources`` (the profile facts + job posting)."""
    vocab = _vocab(sources)
    src_nums = _source_numbers(sources)

    bad_terms: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(text.strip()):
        tokens = list(_WORD.finditer(sentence))
        for idx, m in enumerate(tokens):
            word = _norm(m.group())
            if not word:
                continue
            # Only capitalized tokens are candidate proper nouns.
            if not word[0].isupper():
                continue
            # Ignore the first word of a sentence unless it's clearly an entity
            # (all-caps like "AWS" always checked; leading Capitalized common word
            # skipped to avoid false positives).
            low = word.lower()
            if low in _COMMON:
                continue
            if idx == 0 and not word.isupper() and low not in vocab:
                # Sentence-initial ordinary Capitalized word we can't verify:
                # skip to stay conservative (English capitalizes sentence starts).
                continue
            if low not in vocab and word not in bad_terms:
                bad_terms.append(word)

    bad_numbers: list[str] = []
    for m in _NUMBER.finditer(text):
        norm = m.group().replace(",", "").rstrip("%")
        if norm not in src_nums and m.group() not in bad_numbers:
            bad_numbers.append(m.group())

    grounded = not bad_terms and not bad_numbers
    return GroundingReport(
        grounded=grounded,
        ungrounded_terms=bad_terms,
        ungrounded_numbers=bad_numbers,
    )
