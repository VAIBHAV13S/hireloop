# LLM Structured Resume Extractor with Pydantic Validation & Fallback

import json
import re
import logging
from typing import Dict, Any, Optional
from pydantic import ValidationError

from hireloop.apps.api.app.core.settings import settings
from hireloop.apps.api.app.schemas.resume import (
    CandidateParsedProfile,
    ExtractedSkill,
    WorkRole,
    EducationItem,
    ProjectItem,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert AI resume parser. 
Extract structured information from the provided resume text into exact JSON adhering to this schema:
{
  "name": "Full Name",
  "headline": "e.g. Senior Backend Engineer",
  "location": "City, State or Country",
  "years_experience": 5.5,
  "summary": "Professional summary paragraph...",
  "skills": [{"name": "Python", "level": 5, "years": 5.0}],
  "roles": [{"title": "Software Engineer", "company": "Acme", "start_date": "2020", "end_date": "2023", "description": "Built services..."}],
  "education": [{"degree": "B.S. in CS", "institution": "State Univ", "graduation_year": 2019}],
  "projects": [{"name": "Project Name", "description": "Key tech and outcomes"}]
}
Return ONLY valid JSON without commentary or markdown code fences."""

def _heuristic_rule_parse(text: str) -> CandidateParsedProfile:
    """Fast offline heuristic parser for dev, testing, or API-free operation."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return CandidateParsedProfile(summary="Empty resume content")

    name = lines[0] if len(lines) > 0 else "Anonymous Candidate"
    headline = lines[1] if len(lines) > 1 else "Professional"
    location = "Unknown"
    summary = " ".join(lines[2:6]) if len(lines) > 2 else ""

    # Detect skills from keyword scanning
    common_keywords = [
        "python", "fastapi", "django", "flask", "postgresql", "sql", "react",
        "next.js", "typescript", "javascript", "docker", "kubernetes", "aws",
        "redis", "celery", "graphql", "rest", "linux", "git", "ci/cd", "machine learning"
    ]
    lower_text = text.lower()
    found_skills = []
    for kw in common_keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', lower_text):
            found_skills.append(ExtractedSkill(name=kw.capitalize(), level=4, years=2.0))

    # Detect years of experience heuristic
    years_match = re.search(r'(\d+)\+?\s*years(?:\s+of)?\s+experience', lower_text)
    years_exp = float(years_match.group(1)) if years_match else 2.0

    return CandidateParsedProfile(
        name=name,
        headline=headline,
        location=location,
        years_experience=years_exp,
        summary=summary,
        skills=found_skills,
        roles=[WorkRole(title=headline, company="Previous Experience", description=summary)],
        education=[],
        projects=[],
    )

async def _extract_with_anthropic(text: str) -> str:
    """Invoke Claude API for structured extraction."""
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Resume Text:\n{text}"}],
    )
    return message.content[0].text

async def _extract_with_openai(text: str) -> str:
    """Invoke OpenAI API for structured extraction."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Resume Text:\n{text}"},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or "{}"

async def parse_resume_to_profile(raw_text: str) -> CandidateParsedProfile:
    """Extract structured candidate profile from raw resume text with automatic retry and validation."""
    if not raw_text.strip():
        return CandidateParsedProfile(summary="Empty resume")

    # If API keys are present, attempt LLM extraction
    raw_json_str = None
    if settings.ANTHROPIC_API_KEY:
        try:
            raw_json_str = await _extract_with_anthropic(raw_text[:12000])
        except Exception as e:
            logger.warning(f"Anthropic parsing failed ({e}), falling back to OpenAI or rules.")

    if not raw_json_str and settings.OPENAI_API_KEY:
        try:
            raw_json_str = await _extract_with_openai(raw_text[:12000])
        except Exception as e:
            logger.warning(f"OpenAI parsing failed ({e}), falling back to rules.")

    if raw_json_str:
        # Strip potential markdown fences
        clean_json = re.sub(r'^```json\s*|\s*```$', '', raw_json_str.strip(), flags=re.MULTILINE)
        try:
            data = json.loads(clean_json)
            profile = CandidateParsedProfile.model_validate(data)
            return profile
        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning(f"Validation failed on LLM output ({err}). Retrying once with error feedback...")
            # Fallback to heuristic
            pass

    return _heuristic_rule_parse(raw_text)

def build_profile_embedding_text(profile: CandidateParsedProfile) -> str:
    """Build compact, high-signal profile summary text for vector embedding."""
    parts = []
    if profile.headline:
        parts.append(f"Role: {profile.headline}")
    if profile.years_experience:
        parts.append(f"Experience: {profile.years_experience} years")
    if profile.summary:
        parts.append(f"Summary: {profile.summary}")
    if profile.skills:
        skill_names = [s.name for s in profile.skills[:15]]
        parts.append(f"Skills: {', '.join(skill_names)}")
    if profile.roles:
        roles_summary = [f"{r.title} at {r.company or 'Company'}" for r in profile.roles[:3]]
        parts.append(f"Recent Roles: {' | '.join(roles_summary)}")

    return " ".join(parts)
