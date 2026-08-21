"""JobPilot backend — FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.api import applications, discovery, jobs, matches, profiles
from app.config import settings
from app.db import engine, init_db
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.seed_on_startup:
        with Session(engine) as session:
            if seed_if_empty(session):
                print("[jobpilot] Seeded sample profile + jobs.")
    yield


app = FastAPI(
    title="JobPilot API",
    description="Autonomous, human-in-the-loop job application agent.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profiles.router)
app.include_router(jobs.router)
app.include_router(matches.router)
app.include_router(applications.router)
app.include_router(discovery.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
