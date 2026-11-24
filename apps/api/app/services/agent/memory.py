# Three-Layer Memory Runtime for HireLoop Career Agent

import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.apps.api.app.models.models import Memory, Conversation, Message, CandidateProfile
from hireloop.apps.api.app.services.embedding.embedder import get_embedder

logger = logging.getLogger(__name__)

async def retrieve_semantic_memories(
    user_id: uuid.UUID,
    query_text: str,
    limit: int = 5,
    db: Optional[AsyncSession] = None,
) -> List[Dict[str, Any]]:
    """Retrieve top-k relevant long-term memories weighted by similarity and importance."""
    if not db or not query_text.strip():
        return []

    embedder = get_embedder()
    query_vec = await embedder.embed_text(query_text)
    vec_str = f"[{','.join(f'{x:.6f}' for x in query_vec)}]"

    sql = text("""
        SELECT id, kind, content, importance,
               1 - (embedding <=> CAST(:vec AS vector)) AS similarity
        FROM memories
        WHERE user_id = :uid
        ORDER BY (1 - (embedding <=> CAST(:vec AS vector))) * importance DESC
        LIMIT :limit;
    """)

    result = await db.execute(sql, {"vec": vec_str, "uid": str(user_id), "limit": limit})
    rows = result.fetchall()

    memories = []
    mem_ids = []
    for r in rows:
        memories.append({
            "id": str(r.id),
            "kind": r.kind,
            "content": r.content,
            "importance": float(r.importance),
            "similarity": float(r.similarity),
        })
        mem_ids.append(r.id)

    # Touch last_used_at timestamp
    if mem_ids:
        await db.execute(
            update(Memory)
            .where(Memory.id.in_(mem_ids))
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await db.commit()

    return memories

async def save_user_memory(
    user_id: uuid.UUID,
    kind: str,
    content: str,
    importance: float = 0.7,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Persist a semantic memory (preference, constraint, goal) with its vector embedding."""
    if not db or not content.strip():
        return {"status": "skipped"}

    embedder = get_embedder()
    vec = await embedder.embed_text(content)

    mem_id = uuid.uuid4()
    memory = Memory(
        id=mem_id,
        user_id=user_id,
        kind=kind.lower().strip(),
        content=content.strip(),
        embedding=vec,
        importance=max(0.1, min(1.0, importance)),
        last_used_at=datetime.now(timezone.utc),
    )
    db.add(memory)
    await db.commit()

    return {
        "status": "saved",
        "id": str(mem_id),
        "kind": memory.kind,
        "content": memory.content,
    }

async def load_working_context(
    user_id: uuid.UUID,
    conversation_id: Optional[uuid.UUID],
    db: AsyncSession,
) -> Dict[str, Any]:
    """Assemble agent prompt context: profile card, rolling summary, recent messages."""
    # 1. Candidate profile summary card
    p_res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    profile = p_res.scalars().first()
    profile_card = "No profile uploaded yet."
    if profile:
        profile_card = (
            f"Candidate: {profile.full_name or 'N/A'}\n"
            f"Headline: {profile.headline or 'N/A'}\n"
            f"Experience: {profile.years_exp or 0.0} yrs\n"
            f"Summary: {profile.summary or 'N/A'}"
        )

    # 2. Conversation & rolling summary
    conv = None
    if conversation_id:
        c_res = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conv = c_res.scalars().first()

    summary = conv.summary if conv and conv.summary else "No previous conversation summary."

    # 3. Recent messages (Working memory: last 8 messages)
    history = []
    if conv:
        m_res = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.id.desc())
            .limit(8)
        )
        recent = list(reversed(m_res.scalars().all()))
        for m in recent:
            history.append({
                "role": m.role,
                "content": m.content.get("text", "") if isinstance(m.content, dict) else str(m.content),
            })

    return {
        "profile_card": profile_card,
        "rolling_summary": summary,
        "history": history,
    }
