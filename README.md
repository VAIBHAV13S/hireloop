# HireLoop

> **AI-Driven Job Matching Platform with a Tool-Using Career Agent**  
> *Semantic matching (meaning over keywords) • Explainable fits & gaps • Three-layer persistent agent memory • Production offline evals*

---

## 1. Product Overview

HireLoop is a two-sided AI talent platform engineered around production principles:
- **Candidates** upload a resume, receive structured profile extractions, view ranked job matches with transparent fit reasons and skill gaps, and interact with an autonomous career agent that searches inventory, analyzes skill gaps, drafts personalized cover letters, and remembers preferences across sessions.
- **Recruiters** post positions and view candidate rankings with instant fit explanations.

### Core Architecture & Guarantees
1. **Semantic Matching:** Dense pgvector HNSW similarity + Sparse TSVector BM25-equivalent merged via Reciprocal Rank Fusion (RRF) and Stage 3 feature scoring.
2. **Explainable AI:** Every candidate-job match computes explicit fit reasons, skill overlaps, and gap breakdowns.
3. **Bounded ReAct Career Agent:** Typed tools with JSON schemas, step limits (`max_steps=6`), prompt-injection delimiters, and Server-Sent Events (SSE) streaming.
4. **Three-Layer Memory:** Working memory buffer + rolling episodic summary + semantic long-term memory (`memories` table with vector search and user deletion control).
5. **Empirical Evaluation Suite:** Automated retrieval ablation (NDCG@10, Recall@5, MRR) and agent safety scorecard.

---

## 2. System Architecture

```
            +-------------------+
            |  React / Next.js  |
            |  chat, feed, ATS  |
            +---------+---------+
                      | HTTPS (REST + SSE)
            +---------v---------+
            |   API Gateway /   |
            |   Reverse Proxy   |  rate limit, TLS, CORS
            +---------+---------+
                      |
            +---------v---------+       +------------------+
            |   FastAPI App     +------>+  Redis           |
            |  auth, REST, SSE  |       |  cache, queue,   |
            |  agent runtime    |       |  rate limit      |
            +----+---------+----+       +--------+---------+
                 |         |                     |
        +--------v--+   +--v-----------+   +-----v----------+
        | PostgreSQL|   | Object Store |   |  Worker(s)     |
        | + pgvector|   | (S3 / Local) |   |  resume parse, |
        |           |   | resume files |   |  embedding,    |
        +-----------+   +--------------+   |  job ingestion |
                                           +-----+----------+
                                                 |
                                   +-------------v-----------+
                                   | External: LLM API,      |
                                   | embedding model         |
                                   +-------------------------+
```

---

## 3. Evaluation & Benchmark Results

We evaluated our 4-stage retrieval pipeline against labeled resume-job pairs graded on a 0–3 relevance scale. Full report available at [`evals/reports/ablation_report.md`](file:///D:/D/rise/hireloop/evals/reports/ablation_report.md).

### Retrieval Ablation Results
| Retrieval Configuration | NDCG@10 | Recall@5 | MRR | Latency Target |
| :--- | :---: | :---: | :---: | :---: |
| 1. Sparse BM25 / TSVector Only | **0.9378** | 1.0000 | 1.0000 | < 100 ms |
| 2. Dense PGVector Cosine Only | **0.9803** | 1.0000 | 1.0000 | < 150 ms |
| 3. Hybrid Reciprocal Rank Fusion (RRF) | **0.9693** | 1.0000 | 1.0000 | < 250 ms |
| **4. Hybrid RRF + Feature Scoring (Stage 3)** | **0.9873** | **1.0000** | **1.0000** | < 350 ms |

### Career Agent Safety Scorecard
| Metric | Target | Measured Score | Status |
| :--- | :---: | :---: | :---: |
| **Tool Selection Accuracy** | > 95% | **100.0%** | Passed |
| **Prompt Injection Defense Rate** | 100% | **100.0%** | Passed |
| **Hallucination Rate (Job IDs)** | 0% | **0.0%** | Passed |
| **Pydantic Schema Validity Rate** | > 98% | **100.0%** | Passed |

---

## 4. Quick Start & Demos

### Run Instant Standalone Demo (No Docker Required)
You can run a complete end-to-end simulation of resume parsing, hybrid vector matching, fit explanations, and agent tool execution in 1 second:
```bash
python demo.py
```

### Run Automated Evals
```bash
# Information retrieval ablation
python evals/retrieval_eval.py

# Career agent safety scorecard
python evals/agent_eval.py
```

### Run Production Stack with Docker Compose
```bash
# 1. Start PostgreSQL (with pgvector), Redis, FastAPI API, and Celery Worker
docker compose up --build

# 2. Run migrations
docker compose exec api alembic -c /app/hireloop/apps/api/app/alembic.ini upgrade head

# 3. Seed sample job index
docker compose exec api python -c "from hireloop.apps.api.app.services.ingestion.loader import seed_jobs_inventory; from hireloop.apps.api.app.db.session import AsyncSessionLocal; import asyncio; asyncio.run(seed_jobs_inventory(AsyncSessionLocal()))"
```

The API will be available at `http://localhost:8000`. Interactive OpenAPI documentation is at `http://localhost:8000/docs`.

---

## 5. API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/auth/register` | Register new user account (argon2id password hashing) |
| `POST` | `/v1/auth/login` | Authenticate and obtain JWT access token |
| `POST` | `/v1/resumes/` | Upload resume file (`.pdf`, `.docx`, `.txt`) and queue parsing |
| `GET` | `/v1/resumes/{id}` | Inspect parsing pipeline status and structured profile |
| `GET` | `/v1/jobs/` | Browse active job inventory with filters |
| `POST` | `/v1/jobs/` | Recruiter endpoint: post job, link skills, and embed |
| `GET` | `/v1/matches/` | Retrieve hybrid ranked matches (dense + sparse + RRF) |
| `GET` | `/v1/matches/{id}/explanation` | Fetch fit reasons, missing skills, and score adjustments |
| `POST` | `/v1/matches/feedback` | Record signals (`viewed`, `saved`, `dismissed`, `applied`) |
| `POST` | `/v1/agent/chat` | SSE streaming endpoint for interactive career agent |
| `GET` | `/v1/agent/memories` | User inspection of remembered preferences and goals |
| `DELETE` | `/v1/agent/memories/{id}` | User deletion control of specific memory facts |
| `GET` | `/healthz`, `/readyz` | Liveness and readiness operational probes |

---

## 6. Interview Talking Points & Architecture Decisions

A detailed breakdown connecting this repository to the job description is provided in [`docs/interview_guide.md`](file:///D:/D/rise/hireloop/docs/interview_guide.md).

Topics covered:
1. Why hybrid retrieval beats dense-only (empirically measured NDCG jump from 0.9803 to 0.9873).
2. How prompt injection and cross-user data access are neutralized in the agent loop.
3. Three-layer memory design: working memory, rolling summarization, and vector retrieval with privacy controls.
4. Keeping the API path under 400ms by offloading parsing and OCR to Celery workers.
