# Unit Tests for Resume Extraction & Skill Normalization

from hireloop.apps.api.app.schemas.resume import CandidateParsedProfile, ExtractedSkill
from hireloop.apps.api.app.services.parsing.normalizer import normalize_skill_name
from hireloop.apps.api.app.services.parsing.extractor import build_profile_embedding_text

def test_skill_name_normalization():
    assert normalize_skill_name("python3") == "python"
    assert normalize_skill_name("Postgres") == "postgresql"
    assert normalize_skill_name("K8s") == "kubernetes"
    assert normalize_skill_name("Fast-API") == "fastapi"
    assert normalize_skill_name("custom-tool") == "custom-tool"

def test_profile_embedding_text_builder():
    profile = CandidateParsedProfile(
        name="Alice Smith",
        headline="Senior Python Engineer",
        years_experience=6.0,
        summary="Specializing in distributed systems and FastAPI microservices.",
        skills=[ExtractedSkill(name="Python"), ExtractedSkill(name="FastAPI")],
    )
    text = build_profile_embedding_text(profile)
    assert "Senior Python Engineer" in text
    assert "Experience: 6.0 years" in text
    assert "Python, FastAPI" in text
