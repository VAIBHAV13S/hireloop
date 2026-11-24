# Hybrid Matching Retrieval Service for HireLoop

import logging
from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy import text
from hireloop.apps.api.app.db.session import engine

logger = logging.getLogger(__name__)

async def dense_retrieval(
    profile_vec: List[float],
    limit: int = 200,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Dense vector retrieval using pgvector cosine distance (HNSW index)."""
    if not profile_vec:
        return []

    vec_str = f"[{','.join(f'{x:.6f}' for x in profile_vec)}]"

    sql = text("""
        SELECT jobs.id AS job_id,
               jobs.title,
               jobs.location,
               jobs.remote_type,
               jobs.salary_min,
               jobs.salary_max,
               1 - (jobs.job_embedding <=> CAST(:profile_vec AS vector)) AS dense_score
        FROM jobs
        WHERE jobs.status = 'open'
          AND (CAST(:user_id AS uuid) IS NULL OR NOT EXISTS (
              SELECT 1 FROM match_feedback mf
              WHERE mf.user_id = CAST(:user_id AS uuid)
                AND mf.job_id = jobs.id
                AND mf.signal = 'dismissed'
          ))
        ORDER BY jobs.job_embedding <=> CAST(:profile_vec AS vector)
        LIMIT :limit;
    """)

    u_uuid = str(user_id) if user_id else None

    async with engine.connect() as conn:
        result = await conn.execute(sql, {
            "profile_vec": vec_str,
            "limit": limit,
            "user_id": u_uuid,
        })
        rows = result.fetchall()
        return [
            {
                "job_id": str(row.job_id),
                "title": row.title,
                "location": row.location,
                "remote_type": row.remote_type,
                "salary_min": row.salary_min,
                "salary_max": row.salary_max,
                "dense_score": float(row.dense_score),
            }
            for row in rows
        ]

async def sparse_retrieval(
    query: str,
    limit: int = 200,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Sparse full-text retrieval using Postgres TSVector and ts_rank_cd."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    sql = text("""
        SELECT jobs.id AS job_id,
               jobs.title,
               jobs.location,
               jobs.remote_type,
               jobs.salary_min,
               jobs.salary_max,
               ts_rank_cd(jobs.tsv, websearch_to_tsquery('english', :q)) AS sparse_score
        FROM jobs
        WHERE jobs.status = 'open'
          AND jobs.tsv @@ websearch_to_tsquery('english', :q)
          AND (CAST(:user_id AS uuid) IS NULL OR NOT EXISTS (
              SELECT 1 FROM match_feedback mf
              WHERE mf.user_id = CAST(:user_id AS uuid)
                AND mf.job_id = jobs.id
                AND mf.signal = 'dismissed'
          ))
        ORDER BY sparse_score DESC
        LIMIT :limit;
    """)

    u_uuid = str(user_id) if user_id else None

    async with engine.connect() as conn:
        result = await conn.execute(sql, {
            "q": cleaned_query,
            "limit": limit,
            "user_id": u_uuid,
        })
        rows = result.fetchall()
        return [
            {
                "job_id": str(row.job_id),
                "title": row.title,
                "location": row.location,
                "remote_type": row.remote_type,
                "salary_min": row.salary_min,
                "salary_max": row.salary_max,
                "sparse_score": float(row.sparse_score),
            }
            for row in rows
        ]

def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]],
    sparse_results: List[Dict[str, Any]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """Merge dense and sparse lists using Reciprocal Rank Fusion: RRF = sum(1 / (k + rank))."""
    scores: Dict[str, float] = {}
    job_metadata: Dict[str, Dict[str, Any]] = {}

    for rank, item in enumerate(dense_results, start=1):
        jid = item["job_id"]
        scores[jid] = scores.get(jid, 0.0) + (1.0 / (k + rank))
        if jid not in job_metadata:
            job_metadata[jid] = item

    for rank, item in enumerate(sparse_results, start=1):
        jid = item["job_id"]
        scores[jid] = scores.get(jid, 0.0) + (1.0 / (k + rank))
        if jid not in job_metadata:
            job_metadata[jid] = item

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for jid, rrf_score in ranked:
        meta = job_metadata.get(jid, {})
        results.append({
            "job_id": jid,
            "title": meta.get("title"),
            "location": meta.get("location"),
            "remote_type": meta.get("remote_type"),
            "salary_min": meta.get("salary_min"),
            "salary_max": meta.get("salary_max"),
            "score": round(rrf_score, 6),
        })

    return results

async def get_ranked_matches(
    profile_vec: List[float],
    query: str = "",
    limit: int = 10,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """End-to-end hybrid retrieval: dense ANN + sparse BM25-equivalent + RRF merging."""
    dense_candidates = await dense_retrieval(profile_vec, limit=200, user_id=user_id)
    sparse_candidates = await sparse_retrieval(query, limit=200, user_id=user_id) if query else []

    if not sparse_candidates and dense_candidates:
        # If no text query provided, rank by dense similarity directly
        results = [
            {
                "job_id": item["job_id"],
                "title": item.get("title"),
                "location": item.get("location"),
                "remote_type": item.get("remote_type"),
                "salary_min": item.get("salary_min"),
                "salary_max": item.get("salary_max"),
                "score": round(item["dense_score"], 6),
            }
            for item in dense_candidates[:limit]
        ]
        return results

    merged = reciprocal_rank_fusion(dense_candidates, sparse_candidates)
    return merged[:limit]
