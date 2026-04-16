"""
Router 8: AI Strategic Chat — Executive Assistant Brain.
POST /api/v1/chat/ask
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.responses import StandardResponse
from app.services.ai_service import ask_strategic_question
from app.services.chat_analytics_service import analyze_chat_question
from app.services.chat_history_service import (
    CHAT_HISTORY_RETENTION_LIMIT,
    clear_chat_history,
    list_recent_chat_history,
    save_chat_history_exchange,
)

router = APIRouter(prefix="/chat", tags=["AI Strategic Chat"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Request body for strategic AI chat (TDD Router 8)."""
    message: str
    project_id: Optional[UUID] = None


# ---------------------------------------------------------------------------
# GET /api/v1/chat/history
# ---------------------------------------------------------------------------
@router.get("/history", response_model=StandardResponse[list[dict]])
async def chat_history(
    limit: int = Query(default=CHAT_HISTORY_RETENTION_LIMIT, ge=1, le=CHAT_HISTORY_RETENTION_LIMIT),
    db: AsyncSession = Depends(get_db),
):
    try:
        history = await list_recent_chat_history(db, limit=limit)
        return StandardResponse(data=history)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load chat history: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# DELETE /api/v1/chat/history
# ---------------------------------------------------------------------------
@router.delete("/history", response_model=StandardResponse[dict])
async def chat_history_clear(
    db: AsyncSession = Depends(get_db),
):
    try:
        deleted_count = await clear_chat_history(db)
        return StandardResponse(data={"deleted_count": deleted_count})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear chat history: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# POST /api/v1/chat/ask
# ---------------------------------------------------------------------------
@router.post("/ask", response_model=StandardResponse[dict])
async def chat_ask(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Executive asks a strategic question.
    Flow:
      1. Detect the user's analytics intent.
      2. Aggregate grounded metrics from the database.
      3. Optionally ask Gemini to polish the grounded answer.
      4. Return structured summary + sources + next actions.
    """
    try:
        analysis = await analyze_chat_question(
            db,
            question=request.message,
            project_id=request.project_id,
        )

        # Use LLM polishing as a best-effort step. If it fails, keep the grounded reply.
        try:
            ai_response = await ask_strategic_question(
                question=request.message,
                context_data=analysis["llm_context"],
                project_name=analysis.get("project_name"),
            )
            polished_reply = (ai_response.get("reply") or "").strip()
            if polished_reply:
                analysis["reply"] = polished_reply
        except Exception:
            pass

        analysis.pop("llm_context", None)

        try:
            await save_chat_history_exchange(
                db,
                question=request.message,
                analysis=analysis,
            )
        except Exception:
            await db.rollback()

        return StandardResponse(data=analysis)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI chat failed: {exc}",
        ) from exc
