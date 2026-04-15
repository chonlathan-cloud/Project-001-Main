"""
Router 8: AI Strategic Chat — Executive Assistant Brain.
POST /api/v1/chat/ask
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.boq import BOQItem, Project
from app.schemas.responses import StandardResponse
from app.services.ai_service import ask_strategic_question, generate_embedding

router = APIRouter(prefix="/chat", tags=["AI Strategic Chat"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """Request body for strategic AI chat (TDD Router 8)."""
    message: str
    project_id: Optional[UUID] = None


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
    Flow (LLD §3.2):
      1. Generate embedding from the question.
      2. Vector search in boq_items (pgvector cosine similarity).
      3. Aggregate financial context from results.
      4. Send context + question to Gemini 2.0 Flash.
      5. Return AI reply + cited sources.
    """
    try:
        # 1. Generate embedding from the question
        question_vector = await generate_embedding(request.message)

        # 2. Vector search — find the 10 most similar BOQ items
        query = (
            select(BOQItem)
            .filter(BOQItem.embedding.isnot(None))
            .order_by(BOQItem.embedding.cosine_distance(question_vector))
            .limit(10)
        )

        # Scope to a specific project if provided
        if request.project_id is not None:
            query = query.filter(BOQItem.project_id == request.project_id)

        result = await db.execute(query)
        similar_items = result.scalars().all()

        # 3. Aggregate financial context
        context_data = [
            {
                "description": item.description,
                "sheet_name": item.sheet_name,
                "wbs_level": item.wbs_level,
                "material_unit_price": float(item.material_unit_price or 0),
                "labor_unit_price": float(item.labor_unit_price or 0),
                "total_material": float(item.total_material or 0),
                "total_labor": float(item.total_labor or 0),
                "grand_total": float(item.grand_total or 0),
            }
            for item in similar_items
        ]

        # 4. Determine project name for scope
        project_name = None
        if request.project_id is not None:
            proj_result = await db.execute(
                select(Project).filter_by(id=request.project_id)
            )
            project = proj_result.scalar_one_or_none()
            if project:
                project_name = project.name

        # 5. Send to Gemini for analysis
        ai_response = await ask_strategic_question(
            question=request.message,
            context_data=context_data,
            project_name=project_name,
        )

        return StandardResponse(data=ai_response)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI chat failed: {exc}",
        ) from exc
