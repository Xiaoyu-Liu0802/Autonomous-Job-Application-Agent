# JobPilot 🛫

**An autonomous, human-in-the-loop job-search agent** that discovers job
opportunities, scores them against your profile, decides whether to apply, and
tracks the entire pipeline — pausing to ask *you* whenever a decision is
ambiguous, sensitive, or high-risk.

> The agent's goal isn't to maximize applications submitted. It's to maximize
> **high-quality applications generated per hour of human attention** — and to
> **pause rather than guess**.

The core loop:

```
Discover → Match → Decide → Prepare → Verify → Apply → Track → Learn
```

---

## Why this project

Most job tools automate one slice (search, or autofill). JobPilot is built as a
**long-running autonomous workflow with memory, verification, and recovery** —
the interesting part is the agent architecture, not the UI:

- **Deterministic, explainable fit scoring** — no black-box LLM ranking; every
  score comes with a per-dimension breakdown and the reasons behind it.
- **A decision engine that escalates to a human** when confidence is low, a
  constraint is at stake, or required info is missing.
- **Hard safety rules** — never fabricate experience, misrepresent work
  authorization, submit duplicates, or bypass anti-bot protections.
- **A full audit trail** for every application.

## Status

| Milestone | Scope | State |
|-----------|-------|-------|
| **1 — Agentic core** | Domain models, fit-scoring engine, decision engine, FastAPI service, SQLite persistence, seed data, tests | ✅ **Done** |
| 2 — Dashboard | Next.js funnel + application table + timeline + human-in-the-loop review UI | ⏳ Planned |
| 3 — LLM layer | Resume tailoring & answer reasoning with "never fabricate" guardrails + confidence | ⏳ Planned |
| 4 — Application agent | Playwright form automation as a durable, resumable workflow | ⏳ Planned |

## Architecture (current)

```
                ┌──────────────┐
                │  FastAPI API │
                └──────┬───────┘
        profiles / jobs / matches / applications
                       │
        ┌──────────────┼───────────────┐
        ↓              ↓                ↓
  Matching Agent  Decision Engine   Application
  (fit scoring)   (AUTO/REVIEW/     tracking +
                   REJECT + HITL)    audit trail
        └──────────────┼───────────────┘
                       ↓
                  SQLite / Postgres
```

### Fit score (PRD §9)

`overall = 30% skills + 20% experience + 15% education + 15% role + 10% location + 10% preferences`

Every dimension returns 0–100 with explanation lines, so the dashboard can show
*why this matched* and *potential gaps*.

### Decision routing (PRD §10)

| Category | When |
|----------|------|
| **AUTO_APPLY** | Fit > 85, no blocking gaps, no violated constraints |
| **REVIEW** (human-in-the-loop) | Fit 70–85, **or** a gap needs confirmation |
| **REJECT** | Fit < 70, **or** an excluded company / below-salary-floor constraint is hit |

Hard constraints (excluded company, salary floor) override raw fit — a 90%-fit
role at an excluded company is still rejected.

## Quickstart (backend)

Requires [`uv`](https://docs.astral.sh/uv/).

```sh
cd backend
uv run pytest                              # run the test suite
uv run uvicorn app.main:app --reload       # start the API on :8000
```

On first start the DB is seeded with a sample profile + six jobs that exercise
every decision branch. Then:

- Interactive API docs: <http://localhost:8000/docs>
- `GET /matches/1` — score every job for the sample profile
- `POST /applications {"profile_id":1,"job_id":1}` — open a tracked application
- `GET /applications/funnel` — dashboard funnel counts

## Repo layout

```
backend/
  app/
    models/     # CandidateProfile, Job, Application, scoring types
    agents/     # matching.py (fit scoring), decision.py (routing)
    api/        # profiles, jobs, matches, applications routers
    seed.py     # sample data
    main.py     # FastAPI app
  tests/        # matching + decision unit tests
```

## Safety (hard rules)

The agent must never invent qualifications, employment history, or education;
misrepresent work authorization; submit duplicate applications; ignore explicit
user restrictions; or circumvent CAPTCHA / anti-bot protections. When uncertain,
it asks.

---

*Built as a portfolio project demonstrating agentic workflow engineering. See the
full product spec in the project PRD.*
