"""
Router 4 & 6: Subcontractor Bill Input + Admin Approval.
"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.database import get_db
from app.models.boq import BOQItem  # noqa: F401
from app.models.finance import Installment
from app.api.deps.auth import AuthenticatedUser, require_admin_user
from app.schemas.bill_schema import (
    ApproveBillRequest,
    ExtractBillResponse,
    SubmitBillRequest,
)
from app.schemas.responses import StandardResponse
from app.services.finance_service import record_approved_transaction
from app.services.identity_service import get_subcontractor_financial_rates

router = APIRouter(prefix="/bills", tags=["Bills & Approval"])


# ---------------------------------------------------------------------------
# Router 4: POST /api/v1/bills/extract  (AI OCR Auto-fill)
# ---------------------------------------------------------------------------
@router.post("/extract", response_model=StandardResponse[ExtractBillResponse])
async def extract_bill(file: UploadFile):
    """
    Upload a bill image → Gemini OCR extracts data → return JSON for auto-fill.
    Currently returns LLD mock data; will integrate Gemini OCR later.
    """
    # TODO: Send file bytes to Gemini 1.5 Flash for OCR extraction
    mock_data = ExtractBillResponse(
        receipt_no="INV-2026-001",
        date="2026-03-17",
        vendor_name="Thai Construction Materials Store",
        suggested_expense_type="MATERIAL",
        total_amount=15500.00,
        items=[
            {"description": "Cement", "qty": 100, "price": 155.00},
        ],
    )
    return StandardResponse(data=mock_data)


# ---------------------------------------------------------------------------
# Router 4: POST /api/v1/bills/submit  (Subcontractor submits)
# ---------------------------------------------------------------------------
@router.post("/submit", response_model=StandardResponse[dict])
async def submit_bill(request: SubmitBillRequest):
    """
    Subcontractor submits a bill after reviewing OCR data.
    Records to Firestore with status PENDING_ADMIN.
    """
    # TODO: Write to Firestore draft_bills collection
    return StandardResponse(
        data={
            "message": "Bill submitted successfully.",
            "subcontractor_id": request.subcontractor_id,
            "expense_category": request.expense_category,
            "expense_type": request.expense_type,
            "amount": request.amount,
            "status": "PENDING_ADMIN",
        }
    )


# ---------------------------------------------------------------------------
# Router 6: GET /api/v1/admin/bills?status=PENDING  (Admin view)
# ---------------------------------------------------------------------------
@router.get("/admin/bills", response_model=StandardResponse[list[dict]])
async def list_pending_bills(
    bill_status: str = Query("PENDING", alias="status"),
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    """Return bills filtered by status for Admin review."""
    try:
        result = await db.execute(
            select(Installment).options(noload("*")).filter_by(status=bill_status)
        )
        bills = sorted(
            result.scalars().all(),
            key=lambda bill: (bill.due_date is None, bill.due_date),
        )

        items = [
            {
                "id": str(b.id),
                "boq_item_id": str(b.boq_item_id),
                "subcontractor_id": b.subcontractor_id,
                "expense_category": b.expense_category,
                "expense_type": b.expense_type,
                "installment_no": b.installment_no,
                "amount": float(b.amount or 0),
                "status": b.status,
                "due_date": str(b.due_date) if b.due_date else None,
                "is_overdue": b.is_overdue,
            }
            for b in bills
        ]
        return StandardResponse(data=items)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch bills: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 6: PUT /api/v1/admin/bills/{id}  (Admin direct edit)
# ---------------------------------------------------------------------------
@router.put("/admin/bills/{bill_id}", response_model=StandardResponse[dict])
async def edit_bill(
    bill_id: UUID,
    request: ApproveBillRequest,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    """Admin can directly edit bill amount before approving."""
    try:
        result = await db.execute(
            select(Installment).options(noload("*")).filter_by(id=bill_id)
        )
        installment = result.scalar_one_or_none()

        if installment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bill {bill_id} not found.",
            )

        installment.amount = Decimal(str(request.approved_amount))
        await db.commit()

        return StandardResponse(
            data={
                "id": str(installment.id),
                "subcontractor_id": installment.subcontractor_id,
                "amount": float(installment.amount),
                "message": "Bill updated successfully.",
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update bill: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 6: POST /api/v1/admin/bills/{id}/approve
# ---------------------------------------------------------------------------
@router.post("/admin/bills/{bill_id}/approve", response_model=StandardResponse[dict])
async def approve_bill(
    bill_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    """
    Admin approves a bill:
    1. Calculate Net Payable using subcontractor rates.
    2. Record into transactions table.
    3. Update bill status to APPROVED.
    4. Move image file to /perm_bills (TODO).
    """
    try:
        result = await db.execute(
            select(Installment).options(noload("*")).filter_by(id=bill_id)
        )
        installment = result.scalar_one_or_none()

        if installment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bill {bill_id} not found.",
            )

        rates = (
            get_subcontractor_financial_rates(installment.subcontractor_id)
            if installment.subcontractor_id
            else {
                "vat_rate": Decimal("0.07"),
                "wht_rate": Decimal("0.03"),
                "retention_rate": Decimal("0.05"),
            }
        )

        transaction = await record_approved_transaction(
            session=db,
            installment_id=bill_id,
            base_amount=installment.amount,
            vat_rate=rates["vat_rate"],
            wht_rate=rates["wht_rate"],
            retention_rate=rates["retention_rate"],
        )

        # Update installment status
        installment.status = "APPROVED"
        await db.commit()

        # TODO: Move image from /temp_bills to /perm_bills in GCS

        return StandardResponse(
            data={
                "bill_id": str(bill_id),
                "subcontractor_id": installment.subcontractor_id,
                "status": "APPROVED",
                "net_payable": float(transaction.net_payable),
                "message": "Bill approved and transaction recorded.",
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve bill: {exc}",
        ) from exc
