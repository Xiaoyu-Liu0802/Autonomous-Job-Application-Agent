# JobPilot Backend

FastAPI + SQLModel service implementing the JobPilot agentic core.

## Requirements

- [`uv`](https://docs.astral.sh/uv/) (manages Python + dependencies)

## Commands

```sh
uv run pytest                            # test suite
uv run uvicorn app.main:app --reload     # dev server on http://localhost:8000
```

## Configuration

Settings are read from env vars (prefix `JOBPILOT_`) or a `.env` file:

| Variable | Default | Notes |
|----------|---------|-------|
| `JOBPILOT_DATABASE_URL` | `sqlite:///jobpilot.db` | Use `postgresql+psycopg://…` in prod |
| `JOBPILOT_SEED_ON_STARTUP` | `true` | Seed sample data if the DB is empty |
| `JOBPILOT_CORS_ORIGINS` | `["http://localhost:3000"]` | Frontend origins |

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET/POST | `/profiles` | List / create candidate profiles |
| GET | `/profiles/{id}` | Fetch a profile |
| GET/POST | `/jobs` | List / create jobs (dedupes on `external_id`) |
| GET | `/matches/{profile_id}` | Score every job; `?min_score=`, `?category=` filters |
| POST | `/applications` | Score + decide + open a tracked application |
| GET | `/applications` | List applications |
| GET | `/applications/{id}` | Application detail (incl. timeline) |
| POST | `/applications/{id}/advance` | Move to next pipeline stage |
| POST | `/applications/{id}/status` | Set a specific status |
| POST | `/applications/{id}/answer` | Human-in-the-loop answer; clears NEEDS_REVIEW |
| GET | `/applications/funnel` | Per-status counts for the dashboard |

## Layout

```
app/
  config.py      # pydantic-settings
  db.py          # engine + session
  models/        # domain models (SQLModel tables + Pydantic types)
  agents/
    matching.py  # deterministic, explainable fit scoring
    decision.py  # AUTO_APPLY / REVIEW / REJECT routing
  api/           # routers
  seed.py        # sample profile + jobs
  main.py        # app factory + lifespan (init_db, seed)
tests/           # unit tests for the agents
```
