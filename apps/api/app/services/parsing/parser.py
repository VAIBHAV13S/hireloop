# Resume Parsing and Profile Generation Orchestrator

import asyncio
from pathlib import Path
from typing import Dict, Any, List

from hireloop.apps.api.app.services.object_store import get_resume_path
from hireloop.apps.api.app.services.parsing.extractor import (
    parse_resume_to_profile,
    build_profile_embedding_text,
)
from hireloop.apps.api.app.services.embedding.embedder import get_embedder

def _extract_pdf(file_path: Path) -> str:
    try:
        import pdfplumber
        text = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or "")
        return "\n".join(text)
    except Exception as e:
        # Fallback to PyPDF if available
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            raise RuntimeError(f"Failed to extract PDF text: {e}")

def _extract_docx(file_path: Path) -> str:
    try:
        import docx
        doc = docx.Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        raise RuntimeError(f"Failed to extract DOCX text: {e}")

def extract_text(resume_id: str, filename: str) -> str:
    """Load the stored resume file and return plain extracted text."""
    file_path = get_resume_path(filename)
    if not file_path.exists():
        raise FileNotFoundError(f"Resume file not found at: {file_path}")

    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(file_path)
    if ext in {".docx", ".doc"}:
        return _extract_docx(file_path)
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    raise RuntimeError(f"Unsupported resume file format: {ext}")

async def build_profile_async(resume_id: str, raw_text: str) -> Dict[str, Any]:
    """Parse text using LLM/heuristics, embed summary, and return dictionary payload."""
    parsed_profile = await parse_resume_to_profile(raw_text)
    embed_text = build_profile_embedding_text(parsed_profile)

    embedder = get_embedder()
    embedding = await embedder.embed_text(embed_text)

    return {
        "profile": parsed_profile,
        "name": parsed_profile.name,
        "headline": parsed_profile.headline,
        "location": parsed_profile.location,
        "years_experience": parsed_profile.years_experience,
        "summary": parsed_profile.summary,
        "skills": parsed_profile.skills,
        "parsed_json": parsed_profile.model_dump(),
        "profile_embedding": embedding,
        "embedding_model": embedder.model_name,
    }

def build_profile(resume_id: str, raw_text: str) -> Dict[str, Any]:
    """Synchronous wrapper for Celery worker tasks."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return executor.submit(asyncio.run, build_profile_async(resume_id, raw_text)).result()
    else:
        return loop.run_until_complete(build_profile_async(resume_id, raw_text))
