"""
Router 5: Subcontractor Portal — Personal History.
GET /api/v1/subcontractor/my-bills
POST /api/v1/subcontractor/installments/{id}/advance
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
async def get_my_bills(db: AsyncSession = Depends(get_db)):
    """
    Return the subcontractor's bill history with deduction breakdown.
    Currently returns LLD mock data; will filter by authenticated user.
    """
    # TODO: Filter by authenticated subcontractor ID from Firebase token
    mock_data = [
        {
            "bill_id": "uuid-bill-1",
            "date": "2026-03-15",
            "expense_category": "Concrete Work",
            "requested_amount": 50000.00,
            "status": "APPROVED",
            "net_payable": 45000.00,
            "deductions": {
                "vat": 0.00,
                "wht": 1500.00,
                "retention": 2500.00,
                "advance_repayment": 1000.00,
            },
        }
    ]
    return StandardResponse(data=mock_data)


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
