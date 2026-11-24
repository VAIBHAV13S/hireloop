# Object Storage Abstraction for HireLoop

import os
from pathlib import Path
from uuid import uuid4

# Base storage directory: configurable via env or defaults to <project_root>/data/resumes
_default_root = Path(__file__).resolve().parents[4] / "data"
DATA_ROOT = Path(os.environ.get("DATA_STORAGE_DIR", str(_default_root))).resolve()
RESUMES_DIR = DATA_ROOT / "resumes"
RESUMES_DIR.mkdir(parents=True, exist_ok=True)

def store_resume(file_bytes: bytes, filename: str) -> str:
    """Store raw resume bytes and return a normalized storage key."""
    ext = Path(filename).suffix.lower() if filename else ".pdf"
    unique_name = f"{uuid4()}{ext}"
    dest_path = RESUMES_DIR / unique_name

    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    # Return normalized relative storage key: resumes/<uuid>.<ext>
    return f"resumes/{unique_name}"

def get_resume_path(storage_key: str) -> Path:
    """Resolve normalized storage key to an absolute filesystem Path."""
    # Ensure key is relative and safe
    clean_key = storage_key.lstrip("/\\")
    full_path = (DATA_ROOT / clean_key).resolve()
    return full_path
