"""
Schemas for the Input page submission flow.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BankAccountPayload(BaseModel):
    bank_name: str | None = None
    account_no: str | None = None
    account_name: str | None = None


class ProjectOptionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID = Field(..., alias="id")
    name: str
    project_type: str | None = None
    status: str


class InputRequestCreate(BaseModel):
    project_id: UUID
    entry_type: str = Field(..., pattern="^(EXPENSE|INCOME)$")
    requester_name: str = Field(..., min_length=1)
    phone: str | None = None
    request_date: date
    work_type: str | None = None
    request_type: str | None = None
    note: str | None = None
    vendor_name: str | None = None
    receipt_no: str | None = None
    document_date: date | None = None
    bank_account: BankAccountPayload = Field(default_factory=BankAccountPayload)
    amount: float = Field(..., gt=0)
    receipt_file_name: str | None = None
    receipt_content_type: str | None = None
    receipt_storage_key: str | None = None


class InputRequestItem(BaseModel):
    request_id: UUID
    project_id: UUID
    project_name: str
    entry_type: str
    requester_name: str
    phone: str | None = None
    request_date: date
    work_type: str | None = None
    request_type: str | None = None
    note: str | None = None
    vendor_name: str | None = None
    receipt_no: str | None = None
    document_date: date | None = None
    bank_account: BankAccountPayload
    amount: float
    approved_amount: float | None = None
    receipt_file_name: str | None = None
    receipt_content_type: str | None = None
    receipt_storage_key: str | None = None
    is_duplicate_flag: bool = False
    duplicate_reason: str | None = None
    duplicate_of_request_id: UUID | None = None
    status: str
    review_note: str | None = None
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    payment_reference: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class InputRequestAdminUpdate(BaseModel):
    requester_name: str | None = Field(default=None, min_length=1)
    phone: str | None = None
    request_date: date | None = None
    work_type: str | None = None
    request_type: str | None = None
    note: str | None = None
    vendor_name: str | None = None
    receipt_no: str | None = None
    document_date: date | None = None
    bank_account: BankAccountPayload | None = None
    amount: float | None = Field(default=None, gt=0)


class InputRequestApproveAction(BaseModel):
    approved_amount: float | None = Field(default=None, gt=0)
    review_note: str | None = None


class InputRequestRejectAction(BaseModel):
    review_note: str = Field(..., min_length=1)


class InputRequestMarkPaidAction(BaseModel):
    payment_reference: str | None = None
    review_note: str | None = None


class ReceiptExtractItem(BaseModel):
    description: str
    qty: float
    price: float


class ReceiptExtractResponse(BaseModel):
    file_name: str
    content_type: str | None = None
    file_size_bytes: int
    suggested_entry_type: str
    vendor_name: str | None = None
    receipt_no: str | None = None
    document_date: str | None = None
    suggested_request_type: str | None = None
    total_amount: float = 0.0
    items: list[ReceiptExtractItem] = Field(default_factory=list)
    message: str
