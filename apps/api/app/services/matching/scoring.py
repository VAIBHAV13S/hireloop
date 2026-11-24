# Stage 3 Feature Scoring for Hybrid Job-Candidate Matching

import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Optional

def compute_skill_overlap(
    candidate_skill_ids: Set[int],
    job_required_skill_ids: Set[int],
    job_preferred_skill_ids: Set[int],
) -> float:
    """Compute weighted skill overlap ratio (required skills have 2x weight)."""
    if not job_required_skill_ids and not job_preferred_skill_ids:
        return 0.8  # neutral baseline when job has no explicit skill tags

    req_matches = len(candidate_skill_ids.intersection(job_required_skill_ids))
    req_total = len(job_required_skill_ids)
    req_ratio = (req_matches / req_total) if req_total > 0 else 1.0

    pref_matches = len(candidate_skill_ids.intersection(job_preferred_skill_ids))
    pref_total = len(job_preferred_skill_ids)
    pref_ratio = (pref_matches / pref_total) if pref_total > 0 else 1.0

    # 70% required, 30% preferred
    if req_total > 0 and pref_total > 0:
        return 0.7 * req_ratio + 0.3 * pref_ratio
    elif req_total > 0:
        return req_ratio
    else:
        return pref_ratio

def compute_experience_fit(candidate_years: float, job_min_years: Optional[float]) -> float:
    """Calculate experience compatibility, penalizing significant over/under-qualification."""
    if job_min_years is None or job_min_years <= 0.0:
        return 1.0

    diff = candidate_years - job_min_years
    if diff >= 0:
        # Candidate meets or exceeds: slight decay only if overqualified by > 5 years
        penalty = max(0.0, (diff - 4.0) * 0.05)
        return max(0.6, 1.0 - penalty)
    else:
        # Candidate is under-qualified: penalize 0.15 per year gap
        gap = abs(diff)
        return max(0.2, 1.0 - (gap * 0.15))

def compute_recency_boost(created_at: Optional[datetime], half_life_days: float = 30.0) -> float:
    """Compute exponential decay recency boost for fresh job postings."""
    if not created_at:
        return 0.5
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
    decay = math.exp(-age_days / half_life_days)
    return float(decay)

def calculate_composite_score(
    dense_score: float,
    sparse_score: float,
    skill_overlap: float,
    experience_fit: float,
    recency_boost: float,
) -> float:
    """Weighted multi-feature linear scoring formula (Stage 3):

    - Dense Semantic Similarity: 40%
    - Keyword / TSVector BM25: 15%
    - Canonical Skill Overlap: 25%
    - Experience Alignment: 10%
    - Posting Recency: 10%
    """
    score = (
        0.40 * dense_score +
        0.15 * min(sparse_score, 1.0) +
        0.25 * skill_overlap +
        0.10 * experience_fit +
        0.10 * recency_boost
    )
    return round(float(score), 4)
