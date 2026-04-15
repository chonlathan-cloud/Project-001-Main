"""
Pydantic V2 Schemas — Billing Domain.
Matches LLD Section 2 API Contracts (Router 4, 5, 6) and TDD spec.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Router 4: POST /api/v1/bills/extract  (AI OCR Auto-fill)
# ---------------------------------------------------------------------------
class ExtractedLineItem(BaseModel):
    """Single line item extracted from a receipt by OCR."""
    description: str
    qty: float
    price: float


class ExtractBillResponse(BaseModel):
    """Payload returned after AI OCR extraction."""
    receipt_no: Optional[str] = None
    date: Optional[str] = None
    vendor_name: Optional[str] = None
    suggested_expense_type: Optional[str] = None
    total_amount: float = 0.0
    items: list[ExtractedLineItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Router 4: POST /api/v1/bills/submit  (Subcontractor submits bill)
# ---------------------------------------------------------------------------
class BankAccountInfo(BaseModel):
    """Nested bank account details."""
    bank_name: str
    account_no: str
    account_name: str


class SubmitBillRequest(BaseModel):
    """Request body when a subcontractor submits a bill."""
    expense_category: str
    expense_type: str
    amount: float = Field(..., gt=0)
    bank_account: BankAccountInfo


# ---------------------------------------------------------------------------
# Advance Payment Request (Split Installment)
# ---------------------------------------------------------------------------
class AdvanceRequest(BaseModel):
    """Request body for advance payment (up to 50% of installment)."""
    advance_percent: float = Field(..., gt=0, le=50)
    remark: Optional[str] = None


# ---------------------------------------------------------------------------
# Router 6: POST /api/v1/admin/bills/{id}/approve
# ---------------------------------------------------------------------------
class ApproveBillRequest(BaseModel):
    """Request body when an Admin approves (or edits) a bill."""
    approved_amount: float = Field(..., gt=0)
    remark: Optional[str] = None


# ---------------------------------------------------------------------------
# Router 5: GET /api/v1/subcontractor/my-bills  (Personal History)
# ---------------------------------------------------------------------------
class DeductionBreakdown(BaseModel):
    """Net payable deduction details."""
    vat: float = 0.0
    wht: float = 0.0
    retention: float = 0.0
    advance_repayment: float = 0.0


class SubcontractorBillItem(BaseModel):
    """Single bill in the subcontractor's history."""
    model_config = ConfigDict(from_attributes=True)

    bill_id: UUID
    date: str
    expense_category: str
    requested_amount: float
    status: str
    net_payable: float = 0.0
    deductions: Optional[DeductionBreakdown] = None


class SubcontractorBillListResponse(BaseModel):
    """Payload for GET /api/v1/subcontractor/my-bills."""
    bills: list[SubcontractorBillItem] = Field(default_factory=list)
