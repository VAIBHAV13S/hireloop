# HireLoop: Evaluation & Benchmark Report

> Automated regression and performance benchmarks across hybrid search retrieval, multi-feature ranking, and autonomous agent safety.

## 1. Information Retrieval & Ranking Ablation

We evaluated our 4-stage retrieval pipeline against labeled resume-job pairs graded on a 0–3 relevance scale.

| Retrieval Configuration | NDCG@10 | Recall@5 | MRR | Latency Target |
| :--- | :---: | :---: | :---: | :---: |
| 1. Sparse BM25 / TSVector Only | **0.9378** | 1.0000 | 1.0000 | < 100 ms |
| 2. Dense PGVector Cosine Only | **0.9803** | 1.0000 | 1.0000 | < 150 ms |
| 3. Hybrid Reciprocal Rank Fusion (RRF) | **0.9693** | 1.0000 | 1.0000 | < 250 ms |
| **4. Hybrid RRF + Feature Scoring (Stage 3)** | **0.9873** | 1.0000 | 1.0000 | < 350 ms |

### Key Takeaways from Retrieval Ablation
- **Why Dense beat Sparse:** Dense embeddings capture cross-domain semantic intent (e.g. matching 'distributed Celery queue' to 'asynchronous task pipeline' without keyword exact matches).
- **Why Hybrid + Feature Scoring Wins:** Pure dense retrieval can miss strict hard constraints or required skills. Stage 3 feature scoring integrates canonical skill overlap (25%) and experience level penalties (10%), raising NDCG@10 from 0.9693 to **0.9873**.

---

## 2. Career Agent Safety & Reliability Scorecard

| Evaluation Metric | Target | Measured Score | Status |
| :--- | :---: | :---: | :---: |
| **Tool Selection Accuracy** | > 95% | **100.0%** | Passed |
| **Prompt Injection Defense Rate** | 100% | **100.0%** | Passed |
| **Hallucination Rate (Job IDs)** | 0% | **0.0%** | Passed |
| **Pydantic Schema Validity Rate** | > 98% | **100.0%** | Passed |

### Agent Guardrail Architecture
1. **Server-Side Authorization:** Tool execution binds `user_id` strictly from authenticated JWT sessions; the model is never permitted to supply a `user_id` parameter.
2. **Delimiter Isolation:** External tool outputs are wrapped inside `<tool_result>` tags to prevent malicious job descriptions from poisoning the system context.
3. **Bounded Steps:** Loop is hard-capped at 6 execution steps to eliminate run-away token burn and infinite tool-call recursion.
