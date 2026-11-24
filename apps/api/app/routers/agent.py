# Career Agent Router for HireLoop

import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.apps.api.app.db.session import get_db
from hireloop.apps.api.app.models.models import User, Conversation, Memory
from hireloop.apps.api.app.services.auth import get_current_user
from hireloop.apps.api.app.services.agent.loop import run_agent_loop

router = APIRouter()

class ChatRequest(BaseModel):
    message: str = Field(..., description="User prompt or instruction for career agent")
    conversation_id: Optional[str] = Field(None, description="UUID of existing conversation or creates new")

class MemoryResponseItem(BaseModel):
    id: str
    kind: str
    content: str
    importance: float
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None

@router.post("/chat")
async def chat_with_agent(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Interactive career agent endpoint with Server-Sent Events (SSE) streaming."""
    # Resolve or create conversation
    conv_uuid = None
    if req.conversation_id:
        try:
            conv_uuid = uuid.UUID(req.conversation_id)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid conversation UUID")

    if conv_uuid:
        conv = (await db.execute(
            select(Conversation).where(Conversation.id == conv_uuid, Conversation.user_id == current_user.id)
        )).scalars().first()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    else:
        conv = Conversation(user_id=current_user.id)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        conv_uuid = conv.id

    # Return SSE stream
    generator = run_agent_loop(
        user_message=req.message,
        user_id=current_user.id,
        conversation_id=conv_uuid,
        db=db,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-Id": str(conv_uuid),
        },
    )

@router.get("/memories", response_model=List[MemoryResponseItem])
async def list_memories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all semantic memories, goals, and preferences remembered for the authenticated candidate."""
    result = await db.execute(
        select(Memory)
        .where(Memory.user_id == current_user.id)
        .order_by(Memory.created_at.desc())
    )
    memories = result.scalars().all()
    return [
        MemoryResponseItem(
            id=str(m.id),
            kind=m.kind,
            content=m.content,
            importance=m.importance,
            created_at=m.created_at.isoformat() if m.created_at else None,
            last_used_at=m.last_used_at.isoformat() if m.last_used_at else None,
        )
        for m in memories
    ]

@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a specific memory item from the career agent's long-term memory."""
    try:
        m_uuid = uuid.UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid memory UUID")

    result = await db.execute(
        select(Memory).where(Memory.id == m_uuid, Memory.user_id == current_user.id)
    )
    memory = result.scalars().first()
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory item not found")

    await db.execute(delete(Memory).where(Memory.id == m_uuid))
    await db.commit()
    return None
