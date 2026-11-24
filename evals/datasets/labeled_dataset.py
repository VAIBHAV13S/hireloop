# Labeled Evaluation Dataset for Retrieval & Ranking Benchmarks

LABELED_CANDIDATES = [
    {
        "candidate_id": "cand-01",
        "title": "Senior Python Backend Engineer",
        "headline": "Senior Backend Engineer | FastAPI, PostgreSQL, Distributed Systems",
        "years_experience": 6.0,
        "skills": ["python", "fastapi", "postgresql", "redis", "docker", "celery"],
        "summary": "6+ years architecting asynchronous Python services, database optimization with pgvector, and distributed Celery workers.",
        # Ground truth relevance grades: 0 (irrelevant) to 3 (perfect match)
        "relevance_grades": {
            "seed-001": 3,  # Senior Backend Engineer (Python) -> Perfect
            "seed-002": 2,  # Lead AI Engineer -> Strong overlap on Python/FastAPI/backend
            "seed-005": 2,  # Senior Data Engineer -> Overlap on Python/Postgres
            "seed-008": 1,  # Junior Python Developer -> Under-leveled / partial fit
            "seed-004": 1,  # DevOps Engineer -> Secondary fit (Docker)
            "seed-003": 0,  # Full Stack TypeScript -> Irrelevant
            "seed-006": 0,  # Frontend Engineer -> Irrelevant
            "seed-007": 1,  # ML Research -> Marginal
        }
    },
    {
        "candidate_id": "cand-02",
        "title": "AI & Agent Systems Engineer",
        "headline": "Lead AI Engineer | LLMs, Agentic Tools, RAG, PyTorch",
        "years_experience": 4.5,
        "skills": ["python", "machine learning", "fastapi", "docker", "postgresql"],
        "summary": "Specialist in building tool-using ReAct agents, evaluating retrieval quality (NDCG, Recall), and production RAG pipelines.",
        "relevance_grades": {
            "seed-002": 3,  # Lead AI / LLM Engineer -> Perfect
            "seed-007": 3,  # ML Research Engineer (Embeddings & Search) -> Perfect
            "seed-001": 2,  # Senior Backend Engineer -> Strong Python backend fit
            "seed-005": 1,  # Senior Data Engineer -> Secondary
            "seed-008": 1,  # Junior Python -> Partial
            "seed-003": 0,  # Full Stack TypeScript -> Irrelevant
            "seed-004": 1,  # DevOps -> Marginal
            "seed-006": 0,  # Frontend -> Irrelevant
        }
    },
    {
        "candidate_id": "cand-03",
        "title": "Senior Frontend Developer",
        "headline": "Frontend Engineer | React, Next.js, TypeScript, Tailwind",
        "years_experience": 4.0,
        "skills": ["react", "next.js", "typescript", "javascript", "docker"],
        "summary": "Extensive experience building performant Next.js user interfaces, state architecture, and accessible web experiences.",
        "relevance_grades": {
            "seed-003": 3,  # Full Stack (TypeScript & Next.js) -> Perfect
            "seed-006": 3,  # Frontend Engineer (React UI) -> Perfect
            "seed-001": 0,  # Senior Backend Engineer -> Irrelevant
            "seed-002": 0,  # AI Engineer -> Irrelevant
            "seed-004": 0,  # DevOps -> Irrelevant
            "seed-005": 0,  # Data Engineer -> Irrelevant
            "seed-007": 0,  # ML Research -> Irrelevant
            "seed-008": 0,  # Junior Python -> Irrelevant
        }
    },
    {
        "candidate_id": "cand-04",
        "title": "Cloud & DevOps Infrastructure Specialist",
        "headline": "DevOps Engineer | Kubernetes, Docker, AWS, CI/CD, Terraform",
        "years_experience": 5.0,
        "skills": ["docker", "kubernetes", "aws", "ci/cd", "linux", "python"],
        "summary": "Specialized in cloud platforms, Kubernetes cluster automation, and building reliable CI/CD pipelines on AWS.",
        "relevance_grades": {
            "seed-004": 3,  # DevOps Platform Engineer -> Perfect
            "seed-001": 2,  # Senior Backend -> Secondary infrastructure fit
            "seed-005": 1,  # Data Engineer -> Marginal
            "seed-002": 1,  # AI Engineer -> Marginal (containerization)
            "seed-003": 0,  # Frontend -> Irrelevant
            "seed-006": 0,  # Frontend -> Irrelevant
            "seed-007": 1,  # ML Research -> Marginal
            "seed-008": 0,  # Junior Python -> Irrelevant
        }
    }
]
