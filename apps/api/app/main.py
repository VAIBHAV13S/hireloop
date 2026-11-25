# FastAPI Entry Point for HireLoop API

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, select

from hireloop.apps.api.app.core.settings import settings
from hireloop.apps.api.app.db.session import engine, AsyncSessionLocal
from hireloop.apps.api.app.models.models import Base, Job
from hireloop.apps.api.app.services.ingestion.loader import seed_jobs_inventory
from hireloop.apps.api.app.routers import auth, resumes, matches, agent, jobs

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: automatically initialize schema & seed inventory if empty."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as session:
            existing_job = (await session.execute(select(Job))).first()
            if not existing_job:
                await seed_jobs_inventory(session)
    except Exception as err:
        print(f"[HireLoop Startup Notice] Database auto-initialization deferred: {err}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="Production-grade AI job-matching platform with vector search and career agent runtime.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to trusted domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(resumes.router, prefix="/v1/resumes", tags=["Resumes"])
app.include_router(jobs.router, prefix="/v1/jobs", tags=["Jobs"])
app.include_router(matches.router, prefix="/v1/matches", tags=["Matching"])
app.include_router(agent.router, prefix="/v1/agent", tags=["Career Agent"])

STATIC_INDEX = Path(__file__).resolve().parent / "static" / "index.html"

@app.get("/", response_class=HTMLResponse, tags=["Web Interface"])
@app.get("/app", response_class=HTMLResponse, tags=["Web Interface"])
async def serve_dashboard():
    """Serve the Designeer-crafted interactive HireLoop web dashboard."""
    if STATIC_INDEX.exists():
        return FileResponse(STATIC_INDEX)
    return HTMLResponse("<h1>HireLoop API is running. Visit /docs for OpenAPI documentation.</h1>")

# Health and Ops endpoints (as defined in Section 7 of technical design)
@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["Operations"])
async def healthz():
    """Liveness probe: verifies that the application server is responsive."""
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.API_VERSION}

@app.get("/readyz", status_code=status.HTTP_200_OK, tags=["Operations"])
async def readyz():
    """Readiness probe: verifies database connection and dependency loading."""
    db_connected = False
    db_error = None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_connected = True
    except Exception as e:
        db_error = str(e)

    masked_host = "not-configured (using local default)"
    if settings.RAW_DATABASE_URL:
        masked_host = settings.RAW_DATABASE_URL.split("@")[-1].split("/")[0]

    return {
        "status": "ready" if db_connected else "degraded",
        "database_connected": db_connected,
        "database_host": masked_host,
        "error": db_error,
        "app": settings.PROJECT_NAME,
    }
