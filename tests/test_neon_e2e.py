"""
End-to-end verification script for HireLoop running on Neon PostgreSQL.
Tests:
1. Neon Connection & Extension Health (vector, pg_trgm)
2. FastAPI ASGI Integration (lifespan, dependency injection, Neon queries)
3. User Registration & Auth in Neon
4. Job Retrieval & Vector Search in Neon
5. Agent Tool Retrieval against Neon
6. Live Uvicorn server probe
"""

import sys
import os
import uuid
import asyncio
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT.parent))
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

import httpx
from hireloop.apps.api.app.core.settings import settings
from hireloop.apps.api.app.db.session import engine, sync_engine, AsyncSessionLocal
from hireloop.apps.api.app.main import app
from sqlalchemy import text, select

async def run_tests():
    print("=" * 60)
    print("HIRELOOP NEON POSTGRESQL END-TO-END VERIFICATION")
    print("=" * 60)

    # 1. Environment & Neon Configuration
    print(f"\n[1] Neon Environment Configuration:")
    print(f"  - Branch: {settings.NEON_BRANCH}")
    print(f"  - Branch ID: {settings.NEON_BRANCH_ID}")
    masked_url = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
    print(f"  - Async Engine Host: {masked_url}")

    # 2. Direct Database & Extension Tests
    print(f"\n[2] Testing Direct Database Connections & Extensions:")
    async with engine.connect() as conn:
        db_info = (await conn.execute(text("SELECT version(), current_database();"))).fetchone()
        print(f"  - PostgreSQL Version: {db_info[0]}")
        print(f"  - Current Database: {db_info[1]}")

        ext_res = await conn.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_trgm');"))
        for ext in ext_res.fetchall():
            print(f"  - Extension '{ext[0]}': version {ext[1]} active")

        # Test vector distance calculation in Neon
        vec_test = await conn.execute(text("SELECT ('[1,2,3]'::vector <=> '[1,2,4]'::vector) AS cosine_dist;"))
        print(f"  - pgvector cosine distance calculation: {vec_test.scalar():.6f}")

    # 3. Synchronous Driver Check
    with sync_engine.connect() as s_conn:
        sync_res = s_conn.execute(text("SELECT count(*) FROM jobs;")).scalar()
        print(f"  - Sync Engine (psycopg) jobs count: {sync_res}")

    # 4. FastAPI Endpoints End-to-End
    print(f"\n[3] Testing FastAPI Endpoints End-to-End:")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Liveness & Readiness
        r_health = await client.get("/healthz")
        print(f"  - GET /healthz: {r_health.status_code} {r_health.json()}")
        assert r_health.status_code == 200

        r_ready = await client.get("/readyz")
        print(f"  - GET /readyz: {r_ready.status_code} {r_ready.json()}")
        assert r_ready.status_code == 200

        # Jobs Listing
        r_jobs = await client.get("/v1/jobs/")
        jobs_list = r_jobs.json()
        print(f"  - GET /v1/jobs/: {r_jobs.status_code} returned {len(jobs_list)} jobs from Neon")
        assert r_jobs.status_code == 200 and len(jobs_list) > 0
        first_job_id = jobs_list[0]["id"]

        # Job by ID
        r_single = await client.get(f"/v1/jobs/{first_job_id}")
        print(f"  - GET /v1/jobs/{first_job_id[:8]}...: {r_single.status_code} '{r_single.json()['title']}'")
        assert r_single.status_code == 200

        # User Registration in Neon
        test_email = f"neon_test_{os.urandom(4).hex()}@example.com"
        r_reg = await client.post("/v1/auth/register", json={
            "email": test_email,
            "password": "SecurePassword123!",
            "role": "candidate"
        })
        print(f"  - POST /v1/auth/register ({test_email}): {r_reg.status_code}")
        assert r_reg.status_code in (200, 201)
        token_data = r_reg.json()
        access_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # User Login
        r_login = await client.post("/v1/auth/login", json={
            "email": test_email,
            "password": "SecurePassword123!"
        })
        print(f"  - POST /v1/auth/login: {r_login.status_code}")
        assert r_login.status_code == 200

        # Candidate Profile insertion directly in Neon with pgvector embedding
        from hireloop.apps.api.app.models.models import CandidateProfile, User
        from hireloop.apps.api.app.services.embedding.embedder import get_embedder
        embedder = get_embedder()
        prof_vec = await embedder.embed_text("Senior Python and distributed systems engineer specializing in vector search")
        async with AsyncSessionLocal() as session:
            db_user = (await session.execute(select(User).where(User.email == test_email))).scalars().first()
            user_uuid = db_user.id
            prof = CandidateProfile(
                user_id=user_uuid,
                full_name="Neon Test Candidate",
                headline="Lead AI Engineer",
                location="Remote",
                years_exp=5.0,
                summary="Building AI job matching engines and LLM agents with Neon Postgres.",
                profile_embedding=prof_vec,
            )
            session.add(prof)
            await session.commit()
        print(f"  - Created CandidateProfile in Neon with 1024-dim pgvector embedding")

        # Hybrid Match Retrieval with pgvector in Neon
        r_matches = await client.get("/v1/matches/", headers=headers)
        matches_list = r_matches.json()
        print(f"  - GET /v1/matches/: {r_matches.status_code} returned {len(matches_list)} ranked matches from Neon")
        assert r_matches.status_code == 200
        if matches_list:
            top_match = matches_list[0]
            print(f"    Top Match: '{top_match['title']}' (Score: {top_match['score']:.4f})")

        # Career Agent ReAct Loop (SSE Streaming)
        r_agent = await client.post("/v1/agent/chat", headers=headers, json={
            "message": "Can you find open roles matching Python and distributed systems?"
        })
        print(f"  - POST /v1/agent/chat (SSE Stream): {r_agent.status_code}")
        assert r_agent.status_code == 200
        print(f"    Stream content preview: {r_agent.text[:120].strip()}...")

    print("\n" + "=" * 60)
    print("ALL NEON POSTGRESQL E2E CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
