# Bulk Job Ingestion & Incremental Upsert Pipeline

import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.apps.api.app.models.models import Job, Company, Skill, job_skills
from hireloop.apps.api.app.services.embedding.embedder import get_embedder
from hireloop.apps.api.app.services.parsing.normalizer import normalize_skill_name
from hireloop.apps.api.app.services.ingestion.seed_data import SEED_JOBS

logger = logging.getLogger(__name__)

async def ingest_job(
    data: Dict[str, Any],
    db: AsyncSession,
    source: str = "import",
) -> Job:
    """Ingest a single job posting: deduplicate, compute embedding, update TSVector, and link skills."""
    ext_id = data.get("external_id") or str(uuid.uuid4())

    # 1. Deduplicate by (source, external_id)
    existing_res = await db.execute(
        select(Job).where(Job.source == source, Job.external_id == ext_id)
    )
    job = existing_res.scalars().first()

    # 2. Resolve company
    comp_name = data.get("company", "Unknown Company")
    c_res = await db.execute(select(Company).where(Company.name == comp_name))
    company = c_res.scalars().first()
    if not company:
        company = Company(name=comp_name)
        db.add(company)
        await db.flush()

    # 3. Generate embedding vector
    req_skills = data.get("required_skills", [])
    pref_skills = data.get("preferred_skills", [])
    skills_text = ", ".join(req_skills + pref_skills)
    embed_input = (
        f"Title: {data['title']}. Location: {data.get('location', 'Remote')}. "
        f"Skills: {skills_text}. {data['description'][:1500]}"
    )
    embedder = get_embedder()
    embedding = await embedder.embed_text(embed_input)

    if not job:
        job = Job(
            id=uuid.uuid4(),
            company_id=company.id,
            source=source,
            external_id=ext_id,
            title=data["title"],
            description=data["description"].strip(),
            location=data.get("location"),
            remote_type=data.get("remote_type", "remote"),
            min_years=data.get("min_years", 0.0),
            salary_min=data.get("salary_min"),
            salary_max=data.get("salary_max"),
            status=data.get("status", "open"),
            job_embedding=embedding,
            embedding_model=embedder.model_name,
        )
        db.add(job)
        await db.flush()
    else:
        # Update existing
        job.title = data["title"]
        job.description = data["description"].strip()
        job.location = data.get("location")
        job.remote_type = data.get("remote_type", "remote")
        job.min_years = data.get("min_years", 0.0)
        job.salary_min = data.get("salary_min")
        job.salary_max = data.get("salary_max")
        job.job_embedding = embedding
        job.embedding_model = embedder.model_name
        await db.flush()

    # 4. Link skills
    # Clear existing links
    await db.execute(job_skills.delete().where(job_skills.c.job_id == job.id))

    for s_name in req_skills:
        canonical = normalize_skill_name(s_name)
        s_row = (await db.execute(select(Skill).where(func.lower(Skill.name) == canonical))).scalars().first()
        if not s_row:
            s_row = Skill(name=canonical)
            db.add(s_row)
            await db.flush()
        await db.execute(job_skills.insert().values(job_id=job.id, skill_id=s_row.id, required=True))

    for s_name in pref_skills:
        canonical = normalize_skill_name(s_name)
        s_row = (await db.execute(select(Skill).where(func.lower(Skill.name) == canonical))).scalars().first()
        if not s_row:
            s_row = Skill(name=canonical)
            db.add(s_row)
            await db.flush()
        await db.execute(job_skills.insert().values(job_id=job.id, skill_id=s_row.id, required=False))

    # 5. Populate / Refresh TSVector
    await db.execute(
        text("UPDATE jobs SET tsv = to_tsvector('english', title || ' ' || description) WHERE id = :jid"),
        {"jid": job.id}
    )

    await db.commit()
    await db.refresh(job)
    return job

async def seed_jobs_inventory(db: AsyncSession) -> int:
    """Populate database with standard seed jobs catalog."""
    count = 0
    for item in SEED_JOBS:
        await ingest_job(item, db=db, source="seed")
        count += 1
    logger.info(f"Successfully seeded {count} jobs into HireLoop index.")
    return count
