"""Candidate profile endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import CandidateProfile

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=list[CandidateProfile])
def list_profiles(session: Session = Depends(get_session)) -> list[CandidateProfile]:
    return list(session.exec(select(CandidateProfile)).all())


@router.get("/{profile_id}", response_model=CandidateProfile)
def get_profile(profile_id: int, session: Session = Depends(get_session)) -> CandidateProfile:
    profile = session.get(CandidateProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile


@router.post("", response_model=CandidateProfile, status_code=201)
def create_profile(profile: CandidateProfile, session: Session = Depends(get_session)) -> CandidateProfile:
    profile.id = None
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
