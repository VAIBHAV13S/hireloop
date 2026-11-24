# Skill Normalization Pipeline for HireLoop

import logging
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from hireloop.apps.api.app.models.models import Skill, candidate_skills, job_skills
from hireloop.apps.api.app.schemas.resume import ExtractedSkill

logger = logging.getLogger(__name__)

# Common canonical tech synonyms
SEED_ALIASES = {
    "python": ["python3", "py", "cpython"],
    "fastapi": ["fast-api", "fastapi framework"],
    "postgresql": ["postgres", "pgsql", "psql"],
    "react": ["reactjs", "react.js", "react native"],
    "next.js": ["nextjs", "next"],
    "typescript": ["ts"],
    "javascript": ["js", "es6"],
    "docker": ["docker container", "docker-compose"],
    "kubernetes": ["k8s"],
    "aws": ["amazon web services", "ec2", "s3", "ecs"],
    "machine learning": ["ml", "deep learning"],
    "sql": ["relational database", "ansi sql"],
}

def normalize_skill_name(raw_name: str) -> str:
    """Standardize raw skill string."""
    clean = raw_name.strip().lower()
    for canonical, aliases in SEED_ALIASES.items():
        if clean == canonical or clean in aliases:
            return canonical
    return clean

def normalize_and_link_candidate_skills(
    user_id: Any,
    extracted_skills: List[ExtractedSkill],
    session: Session,
) -> List[Dict[str, Any]]:
    """Map extracted skills to canonical skills table and link in candidate_skills."""
    linked = []

    for item in extracted_skills:
        raw_name = item.name.strip()
        if not raw_name:
            continue

        canonical_name = normalize_skill_name(raw_name)

        # 1. Exact canonical name match
        skill_row = session.execute(
            select(Skill).where(func.lower(Skill.name) == canonical_name)
        ).scalars().first()

        # 2. Check alias match if not found
        if not skill_row:
            skill_row = session.execute(
                select(Skill).where(Skill.aliases.any(canonical_name))
            ).scalars().first()

        # 3. Create canonical skill if new
        if not skill_row:
            aliases = SEED_ALIASES.get(canonical_name, [])
            skill_row = Skill(
                name=canonical_name,
                aliases=aliases,
            )
            session.add(skill_row)
            session.flush()

        # 4. Upsert candidate_skills relationship
        level = item.level or 3
        years = item.years or 1.0

        # Delete existing link if present
        session.execute(
            candidate_skills.delete().where(
                candidate_skills.c.user_id == user_id,
                candidate_skills.c.skill_id == skill_row.id,
            )
        )
        session.execute(
            candidate_skills.insert().values(
                user_id=user_id,
                skill_id=skill_row.id,
                level=level,
                years=years,
            )
        )

        linked.append({
            "skill_id": skill_row.id,
            "name": skill_row.name,
            "level": level,
            "years": years,
        })

    session.flush()
    return linked
