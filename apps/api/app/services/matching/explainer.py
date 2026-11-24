# Stage 4 Explainable Match Reranker and Explanation Generator

import json
import logging
from typing import Dict, Any, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.apps.api.app.core.settings import settings
from hireloop.apps.api.app.models.models import Job, CandidateProfile, Skill, candidate_skills, job_skills
from hireloop.apps.api.app.schemas.matching import MatchExplanation

logger = logging.getLogger(__name__)

# In-memory cache for explanations: (candidate_user_id, job_id) -> MatchExplanation
_EXPLANATION_CACHE: Dict[str, MatchExplanation] = {}

def _make_cache_key(user_id: uuid.UUID, job_id: uuid.UUID) -> str:
    return f"{user_id}:{job_id}"

async def generate_match_explanation(
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    db: AsyncSession,
) -> MatchExplanation:
    """Generate detailed fit reasons, gaps, and calibration for a candidate-job pair."""
    cache_key = _make_cache_key(user_id, job_id)
    if cache_key in _EXPLANATION_CACHE:
        return _EXPLANATION_CACHE[cache_key]

    # 1. Fetch Candidate Profile & Skills
    p_res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    profile = p_res.scalars().first()

    cand_skills_res = await db.execute(
        select(Skill.name, candidate_skills.c.level, candidate_skills.c.years)
        .join(candidate_skills, candidate_skills.c.skill_id == Skill.id)
        .where(candidate_skills.c.user_id == user_id)
    )
    cand_skills = {row[0].lower(): (row[1], row[2]) for row in cand_skills_res.fetchall()}

    # 2. Fetch Job & Required Skills
    j_res = await db.execute(select(Job).where(Job.id == job_id))
    job = j_res.scalars().first()
    if not job:
        raise ValueError(f"Job {job_id} not found")

    job_skills_res = await db.execute(
        select(Skill.name, job_skills.c.required)
        .join(job_skills, job_skills.c.skill_id == Skill.id)
        .where(job_skills.c.job_id == job_id)
    )
    req_skills = set()
    pref_skills = set()
    for row in job_skills_res.fetchall():
        s_name, is_req = row[0].lower(), row[1]
        if is_req:
            req_skills.add(s_name)
        else:
            pref_skills.add(s_name)

    # 3. Compute overlap & gaps
    matched_req = [s for s in req_skills if s in cand_skills]
    missing_req = [s for s in req_skills if s not in cand_skills]
    matched_pref = [s for s in pref_skills if s in cand_skills]

    fit_reasons = []
    gaps = []

    # Experience comparison
    cand_years = profile.years_exp if profile and profile.years_exp else 1.0
    if job.min_years:
        if cand_years >= job.min_years:
            fit_reasons.append(f"Meets or exceeds minimum experience requirement ({cand_years:.1f} yrs vs {job.min_years:.1f} required).")
        else:
            gaps.append(f"Experience gap: role asks for {job.min_years:.1f} years, profile shows ~{cand_years:.1f} years.")

    # Location / Remote fit
    if job.remote_type == "remote":
        fit_reasons.append("Full remote flexibility aligns with platform matches.")
    elif job.location:
        fit_reasons.append(f"Location aligns with job posting ({job.location}).")

    # Skills evidence
    if matched_req:
        fit_reasons.append(f"Strong overlap in core required skills: {', '.join(s.capitalize() for s in matched_req[:4])}.")
    if matched_pref:
        fit_reasons.append(f"Possesses preferred bonus competencies: {', '.join(s.capitalize() for s in matched_pref[:3])}.")

    if missing_req:
        gaps.append(f"Missing stated requirement(s): {', '.join(s.capitalize() for s in missing_req[:3])}.")
    else:
        if not gaps:
            fit_reasons.append("Covers all essential technical requirements listed.")

    summary = (
        f"Solid alignment on core skills with {len(matched_req)}/{len(req_skills) if req_skills else 1} target requirements satisfied."
        if not missing_req else
        f"Competitive profile with minor skill gaps in {', '.join(missing_req[:2])}."
    )

    explanation = MatchExplanation(
        job_id=str(job_id),
        fit_reasons=fit_reasons,
        gaps=gaps,
        score_adjustment=0.05 if not missing_req else -0.05,
        summary=summary,
    )

    _EXPLANATION_CACHE[cache_key] = explanation
    return explanation
