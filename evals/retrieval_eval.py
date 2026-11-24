# Retrieval and Ranking Evaluation Benchmark Suite

import sys
from pathlib import Path
REPO_ROOT = str(Path(__file__).resolve().parents[1])
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
for p in [REPO_ROOT, PROJECT_ROOT]:
    if p not in sys.path:
        sys.path.insert(0, p)

import math
import asyncio
from typing import List, Dict, Any, Set
from evals.datasets.labeled_dataset import LABELED_CANDIDATES
from hireloop.apps.api.app.services.ingestion.seed_data import SEED_JOBS
from hireloop.apps.api.app.services.embedding.embedder import DeterministicLocalEmbedder
from hireloop.apps.api.app.services.matching.scoring import (
    compute_skill_overlap,
    compute_experience_fit,
    calculate_composite_score,
)

def compute_dcg(relevances: List[int], k: int = 10) -> float:
    """Discounted Cumulative Gain at rank k."""
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        dcg += (2.0 ** rel - 1.0) / math.log2(i + 1.0)
    return dcg

def compute_ndcg(retrieved_relevances: List[int], ideal_relevances: List[int], k: int = 10) -> float:
    """Normalized Discounted Cumulative Gain at rank k."""
    actual_dcg = compute_dcg(retrieved_relevances, k)
    sorted_ideal = sorted(ideal_relevances, reverse=True)
    ideal_dcg = compute_dcg(sorted_ideal, k)
    if ideal_dcg <= 0.0:
        return 0.0
    return round(actual_dcg / ideal_dcg, 4)

def compute_recall_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int = 5) -> float:
    """Recall@k against all ground truth relevant items (grade >= 2)."""
    if not relevant_ids:
        return 1.0
    top_k = set(retrieved_ids[:k])
    hits = len(top_k.intersection(relevant_ids))
    return round(hits / len(relevant_ids), 4)

def compute_mrr(retrieved_ids: List[str], target_ids: Set[str]) -> float:
    """Mean Reciprocal Rank of first relevant item."""
    for rank, item_id in enumerate(retrieved_ids, start=1):
        if item_id in target_ids:
            return round(1.0 / rank, 4)
    return 0.0

def evaluate_retrievers() -> Dict[str, Dict[str, float]]:
    """Execute comparative ablation benchmark across retrieval configurations."""
    embedder = DeterministicLocalEmbedder()

    # Pre-embed jobs
    job_embeddings = {}
    for j in SEED_JOBS:
        text = f"{j['title']} {j['description']} {' '.join(j['required_skills'])}"
        job_embeddings[j["external_id"]] = embedder.embed_text_sync(text)

    configs = ["dense_only", "sparse_only", "hybrid_rrf", "hybrid_with_features"]
    results = {cfg: {"ndcg_at_10": 0.0, "recall_at_5": 0.0, "mrr": 0.0} for cfg in configs}

    num_candidates = len(LABELED_CANDIDATES)

    for cand in LABELED_CANDIDATES:
        cand_text = f"{cand['title']} {cand['headline']} {cand['summary']} {' '.join(cand['skills'])}"
        cand_vec = embedder.embed_text_sync(cand_text)
        cand_skills = set(cand["skills"])
        grades = cand["relevance_grades"]
        relevant_ids = {jid for jid, g in grades.items() if g >= 2}
        all_grades = list(grades.values())

        # 1. Dense retrieval scoring (cosine similarity)
        dense_ranked = []
        for j in SEED_JOBS:
            jid = j["external_id"]
            jvec = job_embeddings[jid]
            # Cosine similarity for unit vectors = dot product
            sim = sum(a * b for a, b in zip(cand_vec, jvec))
            dense_ranked.append((jid, sim))
        dense_ranked.sort(key=lambda x: x[1], reverse=True)
        dense_ids = [x[0] for x in dense_ranked]

        # 2. Sparse retrieval scoring (token overlap heuristic)
        cand_tokens = set(cand_text.lower().split())
        sparse_ranked = []
        for j in SEED_JOBS:
            jid = j["external_id"]
            j_tokens = set(f"{j['title']} {j['description']}".lower().split())
            overlap = len(cand_tokens.intersection(j_tokens))
            sparse_ranked.append((jid, float(overlap)))
        sparse_ranked.sort(key=lambda x: x[1], reverse=True)
        sparse_ids = [x[0] for x in sparse_ranked]

        # 3. Hybrid RRF
        rrf_scores = {}
        for rank, jid in enumerate(dense_ids, start=1):
            rrf_scores[jid] = rrf_scores.get(jid, 0.0) + (1.0 / (60 + rank))
        for rank, jid in enumerate(sparse_ids, start=1):
            rrf_scores[jid] = rrf_scores.get(jid, 0.0) + (1.0 / (60 + rank))
        hybrid_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # 4. Hybrid with Feature Scoring (Stage 3)
        feature_scores = {}
        dense_map = dict(dense_ranked)
        sparse_map = dict(sparse_ranked)
        max_sparse = max(sparse_map.values()) if sparse_map.values() else 1.0

        for j in SEED_JOBS:
            jid = j["external_id"]
            d_sc = (dense_map.get(jid, 0.0) + 1.0) / 2.0  # normalize -1..1 to 0..1
            s_sc = sparse_map.get(jid, 0.0) / max(1.0, max_sparse)
            sk_overlap = compute_skill_overlap(cand_skills, set(j["required_skills"]), set(j["preferred_skills"]))
            exp_fit = compute_experience_fit(cand["years_experience"], j.get("min_years", 0.0))
            composite = calculate_composite_score(
                dense_score=d_sc,
                sparse_score=s_sc,
                skill_overlap=sk_overlap,
                experience_fit=exp_fit,
                recency_boost=1.0,
            )
            feature_scores[jid] = composite
        feature_ids = sorted(feature_scores.keys(), key=lambda x: feature_scores[x], reverse=True)

        # Accumulate metrics
        orderings = {
            "dense_only": dense_ids,
            "sparse_only": sparse_ids,
            "hybrid_rrf": hybrid_ids,
            "hybrid_with_features": feature_ids,
        }

        for cfg, ids in orderings.items():
            retrieved_grades = [grades.get(i, 0) for i in ids]
            results[cfg]["ndcg_at_10"] += compute_ndcg(retrieved_grades, all_grades, k=10)
            results[cfg]["recall_at_5"] += compute_recall_at_k(ids, relevant_ids, k=5)
            results[cfg]["mrr"] += compute_mrr(ids, relevant_ids)

    # Average metrics
    for cfg in configs:
        results[cfg]["ndcg_at_10"] = round(results[cfg]["ndcg_at_10"] / num_candidates, 4)
        results[cfg]["recall_at_5"] = round(results[cfg]["recall_at_5"] / num_candidates, 4)
        results[cfg]["mrr"] = round(results[cfg]["mrr"] / num_candidates, 4)

    return results

if __name__ == "__main__":
    report = evaluate_retrievers()
    print("\n=== RETRIEVAL ABLATION RESULTS ===")
    for config, metrics in report.items():
        print(f"[{config.upper()}] NDCG@10: {metrics['ndcg_at_10']:.4f} | Recall@5: {metrics['recall_at_5']:.4f} | MRR: {metrics['mrr']:.4f}")
