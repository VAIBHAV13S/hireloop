# Unit Tests for Matching Engine & Feature Scoring

from datetime import datetime, timezone, timedelta
from hireloop.apps.api.app.services.matching.scoring import (
    compute_skill_overlap,
    compute_experience_fit,
    compute_recency_boost,
    calculate_composite_score,
)
from hireloop.apps.api.app.services.matching.retrieval import reciprocal_rank_fusion

def test_skill_overlap():
    candidate_skills = {1, 2, 3}  # e.g. Python, FastAPI, Docker
    required = {1, 2}             # Python, FastAPI
    preferred = {3, 4}            # Docker, K8s

    # Meets 100% of required (2/2) and 50% of preferred (1/2) -> 0.7*1.0 + 0.3*0.5 = 0.85
    overlap = compute_skill_overlap(candidate_skills, required, preferred)
    assert round(overlap, 2) == 0.85

def test_experience_fit():
    # Exact fit
    assert compute_experience_fit(candidate_years=5.0, job_min_years=5.0) == 1.0

    # Under-qualified by 2 years -> 1.0 - (2 * 0.15) = 0.70
    under = compute_experience_fit(candidate_years=3.0, job_min_years=5.0)
    assert round(under, 2) == 0.70

    # Over-qualified by 6 years -> penalty applies
    over = compute_experience_fit(candidate_years=10.0, job_min_years=4.0)
    assert over < 1.0
    assert over >= 0.6

def test_recency_boost():
    now = datetime.now(timezone.utc)
    fresh = compute_recency_boost(now)
    assert fresh > 0.95

    old = compute_recency_boost(now - timedelta(days=90))
    assert old < fresh

def test_reciprocal_rank_fusion():
    dense = [
        {"job_id": "job-1", "title": "Software Eng", "dense_score": 0.95},
        {"job_id": "job-2", "title": "DevOps", "dense_score": 0.90},
    ]
    sparse = [
        {"job_id": "job-2", "title": "DevOps", "sparse_score": 0.85},
        {"job_id": "job-3", "title": "Data Eng", "sparse_score": 0.80},
    ]

    # job-2 appears in both lists, so its RRF score should be highest!
    merged = reciprocal_rank_fusion(dense, sparse, k=60)
    assert len(merged) == 3
    assert merged[0]["job_id"] == "job-2"
    assert merged[0]["score"] > merged[1]["score"]
