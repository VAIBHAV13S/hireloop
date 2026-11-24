# Celery Tasks for HireLoop Background Processing

import uuid
import logging
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from hireloop.apps.api.app.workers.celery import celery_app
from hireloop.apps.api.app.db.session import sync_engine
from hireloop.apps.api.app.models.models import Resume, CandidateProfile
from hireloop.apps.api.app.services.parsing.parser import extract_text, build_profile
from hireloop.apps.api.app.services.parsing.normalizer import normalize_and_link_candidate_skills

logger = logging.getLogger(__name__)

@celery_app.task(name="parse_resume", bind=True, max_retries=2)
def parse_resume(self, resume_id: str):
    """Background task to extract text, parse structured profile, normalize skills, and store embeddings."""
    logger.info(f"Starting resume parsing task for ID: {resume_id}")

    try:
        r_uuid = uuid.UUID(resume_id)
    except ValueError:
        logger.error(f"Invalid UUID string received: {resume_id}")
        return

    try:
        with sync_engine.connect() as conn:
            # 1. Load Resume row
            result = conn.execute(select(Resume).where(Resume.id == r_uuid)).first()
            if not result:
                logger.error(f"Resume {resume_id} not found in database")
                return
            resume = result[0]

            # Mark status as parsing
            conn.execute(
                update(Resume)
                .where(Resume.id == r_uuid)
                .values(status="parsing")
            )
            conn.commit()

            # 2. Extract plain text from PDF/DOCX/TXT
            raw_text = extract_text(str(r_uuid), resume.storage_key)

            # Update raw_text on resume
            conn.execute(
                update(Resume)
                .where(Resume.id == r_uuid)
                .values(raw_text=raw_text)
            )
            conn.commit()

            # 3. Parse profile and generate embeddings
            profile_data = build_profile(str(r_uuid), raw_text)

            # 4. Upsert candidate profile
            profile_values = {
                "user_id": resume.user_id,
                "full_name": profile_data.get("name"),
                "headline": profile_data.get("headline"),
                "location": profile_data.get("location"),
                "years_exp": profile_data.get("years_experience"),
                "summary": profile_data.get("summary"),
                "parsed_json": profile_data.get("parsed_json"),
                "profile_embedding": profile_data.get("profile_embedding"),
                "embedding_model": profile_data.get("embedding_model", "hireloop-deterministic-v1"),
            }

            insert_stmt = pg_insert(CandidateProfile).values(**profile_values)
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[CandidateProfile.user_id],
                set_={
                    "full_name": profile_values["full_name"],
                    "headline": profile_values["headline"],
                    "location": profile_values["location"],
                    "years_exp": profile_values["years_exp"],
                    "summary": profile_values["summary"],
                    "parsed_json": profile_values["parsed_json"],
                    "profile_embedding": profile_values["profile_embedding"],
                    "embedding_model": profile_values["embedding_model"],
                },
            )
            conn.execute(upsert_stmt)

            # 5. Normalize extracted skills and persist to candidate_skills table
            skills_list = profile_data.get("skills", [])
            if skills_list:
                normalize_and_link_candidate_skills(
                    user_id=resume.user_id,
                    extracted_skills=skills_list,
                    session=conn,
                )

            # 6. Mark resume as parsed
            conn.execute(
                update(Resume)
                .where(Resume.id == r_uuid)
                .values(status="parsed", error=None)
            )
            conn.commit()

            logger.info(f"Successfully parsed resume {resume_id} for user {resume.user_id}")

    except Exception as exc:
        logger.exception(f"Error parsing resume {resume_id}: {exc}")
        with sync_engine.connect() as conn:
            conn.execute(
                update(Resume)
                .where(Resume.id == r_uuid)
                .values(status="failed", error=str(exc))
            )
            conn.commit()
        raise exc
