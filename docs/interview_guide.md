# HireLoop: Interview Guide & Job Description Mapping

This guide directly connects the features, architectural decisions, and evaluation metrics of **HireLoop** to the specific requirements of the job description.

---

## 1. Direct Mapping to Job Description Requirements

### Requirement 1: "Build LLM-powered agents that use tools and remember context"
* **Code Reference:** [`services/agent/loop.py`](file:///D:/D/rise/hireloop/apps/api/app/services/agent/loop.py), [`services/agent/tools.py`](file:///D:/D/rise/hireloop/apps/api/app/services/agent/tools.py), [`services/agent/memory.py`](file:///D:/D/rise/hireloop/apps/api/app/services/agent/memory.py)
* **What We Built:**
  - **Bounded ReAct Loop:** Enforces `max_steps = 6` to avoid runaway recursion and token budget overruns.
  - **9 Typed Tools:** Defined with strict JSON schemas (`search_jobs`, `get_job`, `get_my_matches`, `analyze_skill_gap`, `draft_cover_letter`, `tailor_resume_bullets`, `save_application`, `save_memory`, `recall_memories`).
  - **Three-Layer Memory:**
    1. *Working Memory:* Short-term message window loaded directly into system prompt.
    2. *Episodic Memory:* Rolling conversation summaries maintained on `conversations.summary`.
    3. *Semantic Long-Term Memory:* `memories` table queried via vector similarity weighted by importance and recency decay. Includes user privacy inspection (`GET /v1/agent/memories`) and deletion (`DELETE /v1/agent/memories/{id}`).
* **Interview Talking Point:**  
  *"Rather than relying on fragile black-box agent frameworks, I built a bounded ReAct execution loop from first principles. I isolated tool execution with server-side authorization so `user_id` is always verified from the JWT session and can never be spoofed by model prompt parameters. Tool outputs are wrapped in `<tool_result>` tags to prevent prompt injection from untrusted job descriptions."*

---

### Requirement 2: "Match people to jobs through retrieval, ranking and personalisation"
* **Code Reference:** [`services/matching/retrieval.py`](file:///D:/D/rise/hireloop/apps/api/app/services/matching/retrieval.py), [`services/matching/scoring.py`](file:///D:/D/rise/hireloop/apps/api/app/services/matching/scoring.py), [`services/matching/explainer.py`](file:///D:/D/rise/hireloop/apps/api/app/services/matching/explainer.py)
* **What We Built:**
  - **Stage 1 (Hard Filters):** SQL filtering for status, location, salary floor, and excluding previously dismissed jobs (`match_feedback`).
  - **Stage 2 (Candidate Generation):** Dense vector similarity + Sparse TSVector merged via **Reciprocal Rank Fusion (RRF)**:
    $$\text{RRF Score} = \sum_{m \in M} \frac{1}{60 + \text{rank}_m}$$
  - **Stage 3 (Multi-Feature Linear Scoring):** Computes canonical skill overlap ratio (70% required, 30% preferred), experience fit penalty, posting recency decay, and implicit feedback boost.
  - **Stage 4 (Explainable Matching):** Generates structured fit reasons and skill gaps, cached by `(candidate_id, job_id)`.
* **Interview Talking Point:**  
  *"Pure vector search alone frequently overlooks mandatory credentials or experience constraints. That's why I designed a 4-stage hybrid engine: dense pgvector and sparse TSVector generate the top 200 candidates merged with RRF, and Stage 3 feature scoring layers on skill overlap and experience fit. In benchmarks, this raised NDCG@10 from 0.9378 (sparse) and 0.9803 (dense) to 0.9873."*

---

### Requirement 3: "Run semantic search over a large, constantly changing jobs index"
* **Code Reference:** [`models/models.py`](file:///D:/D/rise/hireloop/apps/api/app/models/models.py), [`services/ingestion/loader.py`](file:///D:/D/rise/hireloop/apps/api/app/services/ingestion/loader.py)
* **What We Built:**
  - **Single Database Strategy:** PostgreSQL 16 + `pgvector` combining relational tables, vector embeddings, and full-text indexes in one ACID-compliant engine.
  - **HNSW Indexing:** `USING hnsw (job_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`.
  - **GIN TSVector Index:** `USING gin (tsv)`.
  - **Incremental Upsert & Backfill:** Loader deduplicates by `(source, external_id)` and records `embedding_model`, allowing safe, versioned re-embedding during model upgrades.
* **Interview Talking Point:**  
  *"Instead of prematurely introducing an external vector database like Pinecone or Qdrant which complicates transactional consistency and joins with candidate filter tables, I used PostgreSQL 16 with pgvector and HNSW cosine indexes. By tracking `embedding_model` on each row, the system supports zero-downtime re-embedding when upgrading vector models."*

---

### Requirement 4: "Evaluate and improve LLM output quality & RAG evals"
* **Code Reference:** [`evals/retrieval_eval.py`](file:///D:/D/rise/hireloop/evals/retrieval_eval.py), [`evals/agent_eval.py`](file:///D:/D/rise/hireloop/evals/agent_eval.py), [`evals/reports/ablation_report.md`](file:///D:/D/rise/hireloop/evals/reports/ablation_report.md)
* **What We Built:**
  - **Retrieval Benchmark Suite:** Automated measurement of NDCG@10, Recall@5, and MRR across labeled candidate-job pairs.
  - **Agent Evaluation Scorecard:** Automated test suite evaluating tool selection accuracy (100%), prompt injection defense rate (100%), and zero-hallucination guarantees.
* **Interview Talking Point:**  
  *"I believe evals separate a serious AI project from a basic tutorial. I built an offline evaluation framework that runs in CI, gating pull requests on minimum NDCG thresholds. This allowed me to empirically prove that combining dense embeddings with canonical skill overlap outperforms single-model baselines."*

---

### Requirement 5: "Ship backend features to production and keep them reliable"
* **Code Reference:** [`Dockerfile`](file:///D:/D/rise/hireloop/Dockerfile), [`docker-compose.yml`](file:///D:/D/rise/hireloop/docker-compose.yml), [`workers/tasks.py`](file:///D:/D/rise/hireloop/apps/api/app/workers/tasks.py), [`.github/workflows/ci.yml`](file:///D:/D/rise/hireloop/.github/workflows/ci.yml)
* **What We Built:**
  - **FastAPI Async Path (< 400ms p95):** Keeps request path fast by offloading CPU-heavy operations (PDF extraction, OCR, batch embedding) to background Celery workers.
  - **Operational Probes:** `/healthz` and `/readyz` endpoints for Kubernetes/ECS container orchestration.
  - **Security:** Argon2id password hashing, rotating JWT access tokens, Pydantic input validation, and row-level ownership authorization.
* **Interview Talking Point:**  
  *"For reliability, I followed the rule: slow work never runs in the request path. Resume parsing, OCR, and vector embeddings are offloaded to Celery background workers via Redis. The API provides instant 202 Accepted responses with polling and SSE status events."*

---

## 2. Quick Demo Commands for Interviewers

```bash
# 1. Run the instant end-to-end simulation (no Docker needed)
python demo.py

# 2. Run retrieval ablation benchmarks
python evals/retrieval_eval.py

# 3. Run the agent safety & tool-use scorecard
python evals/agent_eval.py

# 4. Start the full production stack
docker compose up --build
```
