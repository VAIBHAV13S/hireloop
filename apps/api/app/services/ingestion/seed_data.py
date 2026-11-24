# Realistic Seed Job Catalog for HireLoop

SEED_JOBS = [
    {
        "external_id": "seed-001",
        "title": "Senior Backend Engineer (Python & Distributed Systems)",
        "company": "ScaleFlow Systems",
        "location": "San Francisco, CA",
        "remote_type": "remote",
        "min_years": 5.0,
        "salary_min": 160000,
        "salary_max": 210000,
        "required_skills": ["python", "fastapi", "postgresql", "redis"],
        "preferred_skills": ["docker", "celery", "kubernetes", "aws"],
        "description": """
We are seeking a Senior Backend Engineer to architect, build, and scale our high-throughput data pipelines and RESTful microservices.
In this role, you will design async API endpoints using FastAPI and Python 3.12, optimize complex PostgreSQL queries with pgvector, and maintain reliable background workers using Celery and Redis.
Requirements:
- 5+ years building backend web applications in Python.
- Deep expertise in relational database modeling, indexing, and connection pooling.
- Practical experience with asynchronous paradigms (asyncio, asyncpg) and event queues.
- Passion for clean architecture, automated testing, and observable systems.
"""
    },
    {
        "external_id": "seed-002",
        "title": "Lead AI / LLM Application Engineer",
        "company": "CognitiveLoop AI",
        "location": "New York, NY",
        "remote_type": "remote",
        "min_years": 4.0,
        "salary_min": 180000,
        "salary_max": 240000,
        "required_skills": ["python", "machine learning", "fastapi", "docker"],
        "preferred_skills": ["postgresql", "redis", "typescript", "aws"],
        "description": """
Join CognitiveLoop as our Lead AI Engineer building next-generation agentic workflows, multi-modal reasoning engines, and RAG retrieval pipelines.
Responsibilities:
- Build autonomous LLM agents that employ typed tool execution and persistent episodic memory.
- Evaluate retrieval performance (NDCG@10, Recall@k) and establish regression benchmarks.
- Mitigate LLM security risks including prompt injection, jailbreaks, and hallucinations.
- Deploy low-latency streaming endpoints (SSE) supporting rich agent interactions.
"""
    },
    {
        "external_id": "seed-003",
        "title": "Full Stack Engineer (TypeScript & Next.js)",
        "company": "Vanguard Interfaces",
        "location": "Austin, TX",
        "remote_type": "hybrid",
        "min_years": 3.0,
        "salary_min": 130000,
        "salary_max": 175000,
        "required_skills": ["react", "next.js", "typescript", "javascript"],
        "preferred_skills": ["python", "postgresql", "docker", "graphql"],
        "description": """
Vanguard Interfaces is hiring a Full Stack Engineer to lead front-end feature development and collaborate closely with our API team.
You will build responsive, accessible web applications using Next.js, React, Tailwind CSS, and TypeScript.
Requirements:
- 3+ years experience building modern web UIs with React and TypeScript.
- Strong knowledge of server-side rendering, streaming responses (SSE/WebSockets), and state management.
- Ability to interface cleanly with backend REST APIs and write end-to-end integration tests.
"""
    },
    {
        "external_id": "seed-004",
        "title": "DevOps & Cloud Platform Engineer",
        "company": "CloudForge Infrastructure",
        "location": "Seattle, WA",
        "remote_type": "remote",
        "min_years": 4.0,
        "salary_min": 150000,
        "salary_max": 195000,
        "required_skills": ["docker", "kubernetes", "aws", "ci/cd"],
        "preferred_skills": ["python", "postgresql", "linux"],
        "description": """
We are looking for a DevOps/Platform Engineer to maintain our containerized cloud environments, manage Kubernetes clusters on AWS (EKS), and streamline CI/CD delivery pipelines.
Key Responsibilities:
- Manage infrastructure as code and container deployment topologies.
- Build resilient observability stacks (Prometheus, Grafana, OpenTelemetry).
- Automate testing and zero-downtime rolling deployment workflows.
"""
    },
    {
        "external_id": "seed-005",
        "title": "Senior Data Engineer (Batch & Real-Time)",
        "company": "Apex Analytics",
        "location": "Chicago, IL",
        "remote_type": "onsite",
        "min_years": 5.0,
        "salary_min": 155000,
        "salary_max": 200000,
        "required_skills": ["python", "sql", "postgresql"],
        "preferred_skills": ["docker", "aws", "redis", "machine learning"],
        "description": """
Apex Analytics is searching for a Senior Data Engineer to architect and optimize analytical data warehouses and real-time ingestion pipelines.
Responsibilities:
- Build fault-tolerant ETL/ELT workflows processing hundreds of thousands of daily events.
- Structure relational, columnar, and vector storage engines for maximum throughput.
- Collaborate with ML engineers to supply curated datasets for fine-tuning and evaluation.
"""
    },
    {
        "external_id": "seed-006",
        "title": "Frontend Engineer (React UI & Design Systems)",
        "company": "PixelCraft Studios",
        "location": "San Francisco, CA",
        "remote_type": "remote",
        "min_years": 2.0,
        "salary_min": 115000,
        "salary_max": 150000,
        "required_skills": ["react", "typescript", "javascript"],
        "preferred_skills": ["next.js"],
        "description": """
PixelCraft is looking for a thoughtful Frontend Engineer passionate about crafting beautiful, performant user experiences.
You will develop component libraries, interactive dashboards, and chat interfaces using React and TypeScript.
"""
    },
    {
        "external_id": "seed-007",
        "title": "Machine Learning Research Engineer (Embeddings & Search)",
        "company": "NeuralMetrics Labs",
        "location": "Boston, MA",
        "remote_type": "hybrid",
        "min_years": 4.0,
        "salary_min": 170000,
        "salary_max": 225000,
        "required_skills": ["python", "machine learning", "sql"],
        "preferred_skills": ["docker", "fastapi", "postgresql", "aws"],
        "description": """
NeuralMetrics Labs is pushing the state of the art in representation learning, dense retrieval, and hybrid search.
You will train and benchmark dense vector embedding models, evaluate Reciprocal Rank Fusion against cross-encoders, and optimize ANN index parameters (HNSW ef_search) in production.
"""
    },
    {
        "external_id": "seed-008",
        "title": "Junior Python Developer (API & Data Scraping)",
        "company": "BrightPath Digital",
        "location": "Denver, CO",
        "remote_type": "remote",
        "min_years": 1.0,
        "salary_min": 85000,
        "salary_max": 110000,
        "required_skills": ["python", "sql"],
        "preferred_skills": ["fastapi", "docker", "postgresql"],
        "description": """
Great opportunity for an ambitious junior or early-career Python developer!
You will build internal data collectors, write REST API endpoints, and assist our senior engineers in developing backend services.
"""
    }
]
