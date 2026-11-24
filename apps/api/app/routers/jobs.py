# Jobs Router for HireLoop

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.apps.api.app.db.session import get_db
from hireloop.apps.api.app.models.models import Job, Company, Skill, job_skills, User, CandidateProfile, candidate_skills
from hireloop.apps.api.app.services.auth import get_current_user
from hireloop.apps.api.app.services.embedding.embedder import get_embedder
from hireloop.apps.api.app.services.parsing.normalizer import normalize_skill_name
from hireloop.apps.api.app.schemas.job import JobCreateRequest, JobResponse, CandidateMatchItem

router = APIRouter()

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    remote_type: Optional[str] = Query(None, description="onsite | hybrid | remote"),
    location: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Browse active job postings with basic filters."""
    query = select(Job).where(Job.status == "open")
    if remote_type:
        query = query.where(Job.remote_type == remote_type)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))

    query = query.order_by(Job.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        JobResponse(
            id=str(j.id),
            title=j.title,
            description=j.description,
            location=j.location,
            remote_type=j.remote_type,
            min_years=j.min_years,
            salary_min=j.salary_min,
            salary_max=j.salary_max,
            status=j.status,
            created_at=j.created_at,
        )
        for j in jobs
    ]

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve complete job description and requirements."""
    try:
        j_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job UUID")

    result = await db.execute(select(Job).where(Job.id == j_uuid))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job posting not found")

    return JobResponse(
        id=str(job.id),
        title=job.title,
        description=job.description,
        location=job.location,
        remote_type=job.remote_type,
        min_years=job.min_years,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        status=job.status,
        created_at=job.created_at,
    )

@router.get("/{job_id}/candidates", response_model=List[CandidateMatchItem])
async def get_ranked_candidates_for_job(
    job_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Two-sided recruiter matching: rank candidate profiles against a posted job."""
    try:
        j_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid job UUID")

    job_res = await db.execute(select(Job).where(Job.id == j_uuid))
    job = job_res.scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.job_embedding is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job has no embedding computed yet")

    # Format vector
    job_vec = list(job.job_embedding)
    vec_str = f"[{','.join(f'{x:.6f}' for x in job_vec)}]"

    # 1. Dense retrieval of candidate profiles
    sql = text("""
        SELECT cp.user_id, cp.full_name, cp.headline, cp.location, cp.years_exp, cp.summary,
               1 - (cp.profile_embedding <=> CAST(:job_vec AS vector)) AS dense_sim
        FROM candidate_profiles cp
        WHERE cp.profile_embedding IS NOT NULL
        ORDER BY cp.profile_embedding <=> CAST(:job_vec AS vector)
        LIMIT :limit;
    """)
    result = await db.execute(sql, {"job_vec": vec_str, "limit": limit})
    rows = result.fetchall()

    # 2. Get Job required skills
    jskills_res = await db.execute(
        select(Skill.name, job_skills.c.required)
        .join(job_skills, job_skills.c.skill_id == Skill.id)
        .where(job_skills.c.job_id == job.id)
    )
    job_skills_map = {r[0].lower(): r[1] for r in jskills_res.fetchall()}
    req_skills = {s for s, req in job_skills_map.items() if req}

    candidates = []
    for r in rows:
        uid = r.user_id
        # Fetch candidate skills
        c_skills_res = await db.execute(
            select(Skill.name)
            .join(candidate_skills, candidate_skills.c.skill_id == Skill.id)
            .where(candidate_skills.c.user_id == uid)
        )
        c_skills = {row[0].lower() for row in c_skills_res.fetchall()}

        matched = list(req_skills.intersection(c_skills)) if req_skills else list(c_skills)[:3]
        missing = list(req_skills - c_skills) if req_skills else []

        skill_ratio = (len(matched) / len(req_skills)) if req_skills else 0.8
        dense_sim = float(r.dense_sim) if r.dense_sim is not None else 0.5
        fit_score = round(0.55 * max(0.0, dense_sim) + 0.45 * skill_ratio, 4)

        explanation = (
            f"Strong profile match ({fit_score * 100:.0f}% fit). Meets {len(matched)}/{len(req_skills) if req_skills else 1} target skills."
            if not missing else
            f"Solid candidate with competencies in {', '.join(s.capitalize() for s in matched[:3])}. Missing {', '.join(s.capitalize() for s in missing[:2])}."
        )

        candidates.append(CandidateMatchItem(
            user_id=str(uid),
            full_name=r.full_name or "Anonymous Candidate",
            headline=r.headline or "Software Professional",
            location=r.location or "Remote",
            years_exp=float(r.years_exp) if r.years_exp else 1.0,
            summary=r.summary or "",
            fit_score=fit_score,
            matched_skills=[s.capitalize() for s in matched],
            missing_skills=[s.capitalize() for s in missing],
            fit_explanation=explanation,
        ))

    candidates.sort(key=lambda x: x.fit_score, reverse=True)
    return candidates

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    req: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recruiter posting: create job, link required/preferred skills, and compute embedding."""
    company_id = None
    if req.company_name:
        c_res = await db.execute(select(Company).where(Company.name == req.company_name))
        comp = c_res.scalars().first()
        if not comp:
            comp = Company(name=req.company_name)
            db.add(comp)
            await db.flush()
        company_id = comp.id

    skills_text = ", ".join(req.required_skills + req.preferred_skills)
    embedding_text = f"Title: {req.title}. Location: {req.location or 'Remote'}. Skills: {skills_text}. {req.description[:1000]}"

    embedder = get_embedder()
    vector = await embedder.embed_text(embedding_text)

    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        company_id=company_id,
        posted_by=current_user.id,
        source="recruiter",
        external_id=str(job_id),
        title=req.title,
        description=req.description,
        location=req.location,
        remote_type=req.remote_type or "remote",
        min_years=req.min_years or 0.0,
        salary_min=req.salary_min,
        salary_max=req.salary_max,
        status="open",
        job_embedding=vector,
        embedding_model=embedder.model_name,
    )
    db.add(job)
    await db.flush()

    for s_name in req.required_skills:
        canonical = normalize_skill_name(s_name)
        s_row = (await db.execute(select(Skill).where(func.lower(Skill.name) == canonical))).scalars().first()
        if not s_row:
            s_row = Skill(name=canonical)
            db.add(s_row)
            await db.flush()
        await db.execute(job_skills.insert().values(job_id=job.id, skill_id=s_row.id, required=True))

    for s_name in req.preferred_skills:
        canonical = normalize_skill_name(s_name)
        s_row = (await db.execute(select(Skill).where(func.lower(Skill.name) == canonical))).scalars().first()
        if not s_row:
            s_row = Skill(name=canonical)
            db.add(s_row)
            await db.flush()
        await db.execute(job_skills.insert().values(job_id=job.id, skill_id=s_row.id, required=False))

    await db.execute(
        text("UPDATE jobs SET tsv = to_tsvector('english', title || ' ' || description) WHERE id = :jid"),
        {"jid": job.id}
    )

    await db.commit()
    await db.refresh(job)

    return JobResponse(
        id=str(job.id),
        title=job.title,
        description=job.description,
        company_name=req.company_name,
        location=job.location,
        remote_type=job.remote_type,
        min_years=job.min_years,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        status=job.status,
        created_at=job.created_at,
    )
