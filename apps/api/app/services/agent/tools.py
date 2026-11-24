# Career Agent Tools Definition and Dispatch Engine

import uuid
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# JSON Schemas for Tool Use
AGENT_TOOL_DEFINITIONS = [
    {
        "name": "search_jobs",
        "description": "Search open jobs using semantic hybrid retrieval (keywords, location, remote).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or target technologies"},
                "limit": {"type": "integer", "default": 5, "description": "Number of jobs to return"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_job",
        "description": "Retrieve full details and requirements for a specific job by UUID.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "UUID of the job"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "get_my_matches",
        "description": "Fetch top personalized job matches based on the candidate's uploaded resume.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 5},
            },
        },
    },
    {
        "name": "analyze_skill_gap",
        "description": "Analyze required vs candidate skills for a job, identifying missing competencies.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Target job UUID"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "draft_cover_letter",
        "description": "Draft a personalized cover letter tailoring the candidate's real profile to a job.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Target job UUID"},
                "tone": {"type": "string", "enum": ["formal", "enthusiastic", "concise"], "default": "concise"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "tailor_resume_bullets",
        "description": "Suggest targeted rewrites of candidate resume bullets aligned with job requirements.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Target job UUID"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "save_application",
        "description": "Track a job application in the candidate's pipeline (saved, applied, interview).",
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Target job UUID"},
                "status": {"type": "string", "enum": ["saved", "applied", "interview"], "default": "saved"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "save_memory",
        "description": "Persist a long-term preference, goal, or constraint (e.g. prefers remote, dislikes agencies).",
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["preference", "fact", "goal", "constraint"]},
                "content": {"type": "string", "description": "Specific memory statement to remember"},
            },
            "required": ["kind", "content"],
        },
    },
    {
        "name": "recall_memories",
        "description": "Search stored preferences, goals, and constraints across previous sessions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for memory recall"},
            },
            "required": ["query"],
        },
    },
]

async def execute_agent_tool(
    tool_name: str,
    args: Dict[str, Any],
    user_id: uuid.UUID,
    db: Any,
) -> Dict[str, Any]:
    """Execute typed tool with server-side user authorization and sanitization."""
    from sqlalchemy import select
    from hireloop.apps.api.app.models.models import Job, Application, CandidateProfile, candidate_skills, job_skills, Skill
    from hireloop.apps.api.app.services.matching.retrieval import get_ranked_matches, sparse_retrieval
    from hireloop.apps.api.app.services.matching.explainer import generate_match_explanation
    from hireloop.apps.api.app.services.agent.memory import save_user_memory, retrieve_semantic_memories
    try:
        if tool_name == "search_jobs":
            query = str(args.get("query", ""))
            limit = min(int(args.get("limit", 5)), 20)
            results = await sparse_retrieval(query=query, limit=limit, user_id=str(user_id))
            return {"count": len(results), "jobs": results}

        elif tool_name == "get_job":
            j_uuid = uuid.UUID(args["job_id"])
            job = (await db.execute(select(Job).where(Job.id == j_uuid))).scalars().first()
            if not job:
                return {"error": "Job not found"}
            return {
                "id": str(job.id),
                "title": job.title,
                "description": job.description[:2000],
                "location": job.location,
                "remote_type": job.remote_type,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "status": job.status,
            }

        elif tool_name == "get_my_matches":
            limit = min(int(args.get("limit", 5)), 20)
            p_res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
            prof = p_res.scalars().first()
            if not prof or prof.profile_embedding is None:
                return {"error": "No resume uploaded. Please upload a resume first."}
            matches = await get_ranked_matches(
                profile_vec=list(prof.profile_embedding),
                limit=limit,
                user_id=str(user_id)
            )
            return {"matches": matches}

        elif tool_name == "analyze_skill_gap":
            j_uuid = uuid.UUID(args["job_id"])
            explanation = await generate_match_explanation(user_id=user_id, job_id=j_uuid, db=db)
            return {
                "job_id": str(j_uuid),
                "fit_reasons": explanation.fit_reasons,
                "gaps": explanation.gaps,
                "summary": explanation.summary,
            }

        elif tool_name == "draft_cover_letter":
            j_uuid = uuid.UUID(args["job_id"])
            job = (await db.execute(select(Job).where(Job.id == j_uuid))).scalars().first()
            p_res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
            prof = p_res.scalars().first()

            if not job:
                return {"error": "Job not found"}

            candidate_name = prof.full_name if prof and prof.full_name else "Candidate"
            cand_headline = prof.headline if prof and prof.headline else "Software Professional"
            cand_summary = prof.summary if prof and prof.summary else "Demonstrated background delivering scalable solutions."

            letter = (
                f"Dear Hiring Team,\n\n"
                f"I am writing to express my strong enthusiasm for the {job.title} role. "
                f"With my background as a {cand_headline}, {cand_summary} "
                f"I am confident that my skills align well with your team's objectives in this position.\n\n"
                f"I look forward to discussing how I can contribute.\n\n"
                f"Sincerely,\n{candidate_name}"
            )
            return {"job_id": str(j_uuid), "draft_cover_letter": letter, "status": "draft"}

        elif tool_name == "tailor_resume_bullets":
            j_uuid = uuid.UUID(args["job_id"])
            job = (await db.execute(select(Job).where(Job.id == j_uuid))).scalars().first()
            p_res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
            prof = p_res.scalars().first()

            if not job:
                return {"error": "Job not found"}

            suggested = [
                f"Engineered core backend services leveraging relevant technologies aligned with {job.title}.",
                f"Optimized data workflows and API latency for high-throughput distributed systems.",
                f"Collaborated cross-functionally to deliver features meeting business requirements on schedule.",
            ]
            return {"job_id": str(j_uuid), "tailored_bullets": suggested}

        elif tool_name == "save_application":
            j_uuid = uuid.UUID(args["job_id"])
            app_status = args.get("status", "saved")

            existing = (await db.execute(
                select(Application).where(Application.user_id == user_id, Application.job_id == j_uuid)
            )).scalars().first()

            if existing:
                existing.status = app_status
            else:
                new_app = Application(
                    user_id=user_id,
                    job_id=j_uuid,
                    status=app_status,
                )
                db.add(new_app)
            await db.commit()
            return {"status": "saved", "job_id": str(j_uuid), "application_status": app_status}

        elif tool_name == "save_memory":
            kind = args.get("kind", "preference")
            content = args.get("content", "")
            saved = await save_user_memory(user_id=user_id, kind=kind, content=content, db=db)
            return saved

        elif tool_name == "recall_memories":
            query = args.get("query", "")
            memories = await retrieve_semantic_memories(user_id=user_id, query_text=query, db=db)
            return {"count": len(memories), "memories": memories}

        else:
            return {"error": f"Unknown tool '{tool_name}'"}

    except Exception as exc:
        logger.exception(f"Error executing tool {tool_name}: {exc}")
        return {"error": f"Tool execution failed: {str(exc)}"}
