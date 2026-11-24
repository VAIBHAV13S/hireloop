# Matches Router for HireLoop

import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.apps.api.app.db.session import get_db
from hireloop.apps.api.app.models.models import User, CandidateProfile, MatchFeedback, Job
from hireloop.apps.api.app.services.auth import get_current_user
from hireloop.apps.api.app.services.matching.retrieval import get_ranked_matches
from hireloop.apps.api.app.services.matching.explainer import generate_match_explanation
from hireloop.apps.api.app.schemas.matching import (
    MatchResponseItem,
    MatchExplanation,
    MatchFeedbackRequest,
)

router = APIRouter()

@router.get("/", response_model=List[MatchResponseItem])
async def get_matches(
    limit: int = Query(10, ge=1, le=100),
    query: str = Query("", description="Optional keyword query for sparse full-text retrieval"),
    profile_vec: Optional[str] = Query(None, description="Optional override profile embedding as comma-separated floats"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve ranked job matches using hybrid retrieval (Dense pgvector + Sparse TSVector + RRF)."""
    target_vector: Optional[List[float]] = None

    if profile_vec:
        try:
            target_vector = [float(v.strip()) for v in profile_vec.split(",") if v.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid profile_vec format. Expected comma-separated float numbers.",
            )
    else:
        # Load user's profile embedding from database
        result = await db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
        )
        profile = result.scalars().first()
        if profile and profile.profile_embedding is not None:
            target_vector = list(profile.profile_embedding)

    if not target_vector:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidate profile embedding found. Please upload a resume first or pass profile_vec.",
        )

    matches = await get_ranked_matches(
        profile_vec=target_vector,
        query=query,
        limit=limit,
        user_id=str(current_user.id),
    )

    items = []
    for m in matches:
        items.append(MatchResponseItem(
            job_id=m["job_id"],
            title=m.get("title"),
            location=m.get("location"),
            remote_type=m.get("remote_type"),
            salary_min=m.get("salary_min"),
            salary_max=m.get("salary_max"),
            score=m.get("score", 0.0),
        ))
    return items

@router.get("/{job_id}/explanation", response_model=MatchExplanation)
async def get_match_explanation(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve structured fit reasons, skill gaps, and score calibration for a job."""
    try:
        j_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job UUID string",
        )

    try:
        explanation = await generate_match_explanation(
            user_id=current_user.id,
            job_id=j_uuid,
            db=db,
        )
        return explanation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def record_match_feedback(
    feedback: MatchFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record implicit and explicit feedback signals (viewed, saved, dismissed, applied)."""
    valid_signals = {"viewed", "saved", "dismissed", "applied"}
    if feedback.signal not in valid_signals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signal '{feedback.signal}'. Allowed: {', '.join(valid_signals)}",
        )

    try:
        j_uuid = uuid.UUID(feedback.job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job UUID string",
        )

    # Check job exists
    job = (await db.execute(select(Job).where(Job.id == j_uuid))).scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Upsert feedback
    existing = await db.execute(
        select(MatchFeedback).where(
            MatchFeedback.user_id == current_user.id,
            MatchFeedback.job_id == j_uuid,
            MatchFeedback.signal == feedback.signal,
        )
    )
    if not existing.scalars().first():
        record = MatchFeedback(
            user_id=current_user.id,
            job_id=j_uuid,
            signal=feedback.signal,
        )
        db.add(record)
        await db.commit()

    return {"status": "recorded", "job_id": feedback.job_id, "signal": feedback.signal}
