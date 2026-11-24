# Resume Router for HireLoop

import uuid
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.apps.api.app.db.session import get_db
from hireloop.apps.api.app.models.models import Resume, CandidateProfile, User
from hireloop.apps.api.app.services.object_store import store_resume
from hireloop.apps.api.app.services.auth import get_current_user
from hireloop.apps.api.app.workers.celery import celery_app

router = APIRouter()

MAX_RESUME_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a resume (PDF/DOCX), store securely, and trigger parsing pipeline."""
    # Check extension
    filename = file.filename or "resume.pdf"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file contents and check size
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )
    if len(contents) > MAX_RESUME_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Resume file size exceeds maximum limit of {MAX_RESUME_SIZE // (1024 * 1024)} MB",
        )

    # Save to object store
    storage_key = store_resume(contents, filename)

    # Insert Resume row in DB
    resume_id = uuid.uuid4()
    resume_record = Resume(
        id=resume_id,
        user_id=current_user.id,
        storage_key=storage_key,
        status="uploaded",
    )
    db.add(resume_record)
    await db.commit()
    await db.refresh(resume_record)

    # Enqueue background parsing task
    celery_app.send_task("parse_resume", args=[str(resume_id)])

    return {
        "resume_id": str(resume_id),
        "status": "uploaded",
        "message": "Resume uploaded successfully. Parsing in progress.",
    }

@router.get("/{resume_id}")
async def get_resume_status(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve resume status and parsed profile if available."""
    try:
        r_uuid = uuid.UUID(resume_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resume UUID format",
        )

    result = await db.execute(select(Resume).where(Resume.id == r_uuid))
    resume = result.scalars().first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # Check ownership
    if resume.user_id != current_user.id and current_user.role not in {"recruiter", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this resume",
        )

    response: Dict[str, Any] = {
        "resume_id": str(resume.id),
        "status": resume.status,
        "error": resume.error,
        "created_at": resume.created_at.isoformat() if resume.created_at else None,
    }

    if resume.status == "parsed":
        profile_res = await db.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == resume.user_id)
        )
        profile = profile_res.scalars().first()
        if profile:
            response["profile"] = {
                "full_name": profile.full_name,
                "headline": profile.headline,
                "location": profile.location,
                "years_exp": profile.years_exp,
                "summary": profile.summary,
                "parsed_json": profile.parsed_json,
            }

    return response
