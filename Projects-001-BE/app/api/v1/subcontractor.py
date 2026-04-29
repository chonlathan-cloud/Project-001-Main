"""
Router 5: Subcontractor Portal — Personal History.
GET /api/v1/subcontractor/my-bills
POST /api/v1/subcontractor/installments/{id}/advance
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import AuthenticatedUser, require_subcontractor_user
from app.core.database import get_db
from app.models.finance import Installment
from app.schemas.bill_schema import AdvanceRequest
from app.schemas.responses import StandardResponse
from app.services.finance_service import process_advance_request

router = APIRouter(prefix="/subcontractor", tags=["Subcontractor Portal"])


# ---------------------------------------------------------------------------
# Router 5: GET /api/v1/subcontractor/my-bills
# ---------------------------------------------------------------------------
@router.get("/my-bills", response_model=StandardResponse[list[dict]])
async def get_my_bills(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_subcontractor_user),
):
    """
    Return the subcontractor's bill history with deduction breakdown.
    Currently returns LLD mock data; will filter by authenticated user.
    """
    subcontractor_id = user.subcontractor_id
    if not subcontractor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated subcontractor context is missing.",
        )

    result = await db.execute(
        select(Installment).filter_by(subcontractor_id=subcontractor_id).order_by(Installment.due_date.desc())
    )
    items = []
    for installment in result.scalars().all():
        items.append(
            {
                "bill_id": str(installment.id),
                "date": str(installment.due_date) if installment.due_date else "",
                "expense_category": installment.expense_category or "-",
                "requested_amount": float(installment.amount or 0),
                "status": installment.status,
                "net_payable": float(installment.amount or 0),
                "deductions": {
                    "vat": 0.0,
                    "wht": 0.0,
                    "retention": 0.0,
                    "advance_repayment": 0.0,
                },
            }
        )
    return StandardResponse(data=items)


# ---------------------------------------------------------------------------
# POST /api/v1/subcontractor/installments/{id}/advance
# ---------------------------------------------------------------------------
@router.post(
    "/installments/{installment_id}/advance",
    response_model=StandardResponse[dict],
)
async def request_advance(
    installment_id: UUID,
    request: AdvanceRequest,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_subcontractor_user),
):
    """
    Subcontractor requests an advance payment (up to 50%).
    Calls finance_service.process_advance_request to split the installment.
    """
    result = await process_advance_request(
        session=db,
        installment_id=installment_id,
        advance_percent=request.advance_percent,
    )
    return StandardResponse(data=result)
