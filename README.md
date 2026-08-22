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
| **2 — Real job discovery** | Pluggable sources + Greenhouse / Lever / Ashby ATS-API adapters, offline text normalizer (skills/years/education/salary), dedupe, paste-a-URL import | ✅ **Done** |
| **3 — Application agent** | Human-in-the-loop preparation (field mapping + question routing) + Playwright "fill-and-pause" runner (never submits, never bypasses CAPTCHA) | ✅ **Done** |
| **4 — Dashboard** | Next.js UI: pipeline funnel, ranked matches with score breakdowns, application table, per-application timeline + human-in-the-loop review, discovery controls | ✅ **Done** |
| **5 — LLM layer** | Grounded answer reasoning + resume tailoring behind a hard anti-fabrication guardrail; runs offline with zero credentials, upgrades to the Anthropic API when configured | ✅ **Done** |

> Verified live: a discovery run against the Anthropic (Greenhouse) and OpenAI
> (Ashby) boards pulls **~1,200 real open roles**, auto-scores them, and routes
> each into AUTO_APPLY / REVIEW / REJECT.

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

## Job discovery (real listings)

JobPilot pulls **real** postings from public ATS job-board APIs — no scraping,
no login, ToS-friendly:

| Source | Adapter | Notes |
|--------|---------|-------|
| **Greenhouse** | `greenhouse` | `boards-api.greenhouse.io` — e.g. Anthropic, Stripe, Databricks |
| **Lever** | `lever` | `api.lever.co` — any valid board token |
| **Ashby** | `ashby` | `api.ashbyhq.com` — e.g. OpenAI |

Plus **paste-a-URL import** (`/discovery/import-url`): give it any job link. If
it's a recognized ATS URL we use that platform's API; otherwise we do a
best-effort public-page parse.

> **On LinkedIn / Indeed / Jobright:** these prohibit automated access in their
> ToS and aggressively block bots — automating them risks getting your account
> banned. JobPilot deliberately does **not** scrape them. Use paste-a-URL to
> import a specific posting you found there instead.

## LLM layer — grounded, or it doesn't ship (never fabricate)

The interesting problem in an application agent isn't generating fluent text —
it's **guaranteeing the text is true**. JobPilot treats the verified profile as
the *only* ground truth and enforces it structurally:

1. **Facts, enumerated** — the profile is flattened into atomic, citable facts
   (`skill:python`, `exp:0:summary`, `auth:sponsorship`, …). Those, plus the job
   posting, are the entire universe an answer may draw on.
2. **Generate** — the offline provider (default, no key) assembles answers
   *only* from those facts, so it can't fabricate by construction. With
   `JOBPILOT_ANTHROPIC_API_KEY` set it uses the Anthropic API instead, prompted
   to cite fact IDs and use nothing else.
3. **Verify (the guardrail)** — every draft, *from any provider*, is scanned for
   proper nouns and numbers that aren't traceable to a fact or the posting. An
   invented employer, tech, metric, or percentage is caught here regardless of
   how confident the model sounded.
4. **Gate** — only a **fully grounded, above-confidence** draft is auto-filled.
   Anything weaker (or sensitive — salary, demographics) is handed back to *you*
   as a suggestion. The agent never guesses on the record.

Same pipeline powers **resume tailoring**: it reorders and summarizes your real
experience to emphasize overlap with a role, surfaces the honest skill gaps, and
runs the summary through the guardrail — emphasize only, never embellish.

```
POST /llm/draft-answer     {profile_id, job_id, question}  -> grounded answer + confidence
POST /llm/tailor-resume    {profile_id, job_id}            -> summary, highlights, gaps, emphasis
GET  /llm/status                                           -> active provider + guardrail settings
```

To use the real Anthropic model instead of the offline provider:

```sh
uv sync --extra llm
JOBPILOT_ANTHROPIC_API_KEY=sk-ant-... uv run uvicorn app.main:app --reload
```

## Application agent (fill, then pause)

Before any browser work, `/applications/{id}/prepare` produces a plan: the
fields the agent can fill from your **verified profile** + saved answers, and
the questions that must go to **you** (salary, demographics, anything
unverifiable). The optional Playwright runner (`app/apply/browser.py`) then
fills those fields on the real form and **stops** — it never clicks Submit and
**never bypasses CAPTCHA**. You review and submit.

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
- `POST /discovery/run` — pull real jobs from the default ATS boards (or pass your own)
- `POST /discovery/import-url {"url": "..."}` — import a single posting
- `GET /matches/1` — score every job for the sample profile
- `POST /applications {"profile_id":1,"job_id":1}` — open a tracked application
- `POST /applications/1/prepare {"questions":[...]}` — build the fill/review plan (drafts grounded answers)
- `POST /llm/draft-answer {"profile_id":1,"job_id":1,"question":"..."}` — grounded answer + confidence
- `POST /llm/tailor-resume {"profile_id":1,"job_id":1}` — emphasize real experience for a role
- `GET /applications/funnel` — dashboard funnel counts

To enable the browser runner:

```sh
uv sync --extra browser && uv run playwright install chromium
```

## Quickstart (dashboard)

The Next.js dashboard talks to the API at `http://localhost:8000` (override with
`NEXT_PUBLIC_API_URL`). With the backend running:

```sh
cd frontend
npm install
npm run dev                                # http://localhost:3000
```

Pages:

- **Overview** — pipeline funnel + tracked / applied / interview / offer stats
- **Matches** — every job scored & ranked, with an expandable per-dimension
  breakdown and one-click "Track"
- **Applications** — the tracked pipeline; drill into any row for its timeline
  and the human-in-the-loop prepare/answer flow
- **Discovery** — run the ATS boards or import a single posting by URL

## Repo layout

```
backend/
  app/
    models/     # CandidateProfile, Job, Application, scoring types
    agents/     # matching.py (fit scoring), decision.py (routing)
    sources/    # ATS adapters (greenhouse/lever/ashby), normalizer, url_import
    services/   # discovery orchestration
    apply/      # prepare.py (field map + HITL) + browser.py (Playwright, optional)
    llm/        # facts.py + guardrails.py (anti-fabrication) + provider.py + answers.py + resume.py
    api/        # profiles, jobs, matches, applications, discovery, llm routers
    seed.py     # sample data
    main.py     # FastAPI app
  tests/        # 48 unit tests (matching, decision, normalize, discovery, prepare, llm)
frontend/
  src/
    app/        # Overview, matches, applications (+ [id] detail), discovery pages
    components/ # Nav + shared UI (cards, badges, score bars)
    lib/        # typed API client + useAsync hook
```

## Safety (hard rules)

The agent must never invent qualifications, employment history, or education;
misrepresent work authorization; submit duplicate applications; ignore explicit
user restrictions; or circumvent CAPTCHA / anti-bot protections. When uncertain,
it asks.

---

*Built as a portfolio project demonstrating agentic workflow engineering. See the
full product spec in the project PRD.*
