"""API contracts for project fund buckets and immutable allocations."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FundBucketOption(BaseModel):
    bucket_id: UUID
    project_id: UUID
    project_name: str
    project_type: str
    system_key: str | None = None
    bucket_type: str
    status: str
    currency: str
    available_margin_to_allocate: Decimal
    # Transitional alias retained for clients deployed before the forecast-margin revision.
    available_to_allocate: Decimal
    version: str
    is_active: bool


class FundSummaryResponse(BaseModel):
    project_id: UUID
    bucket_id: UUID
    currency: str
    forecast_base_type: str
    projected_boq_margin: Decimal
    opening_forecast_balance: Decimal
    forecast_allocated_in: Decimal
    forecast_allocated_out: Decimal
    forecast_reserve: Decimal
    raw_forecast_available: Decimal
    available_margin_to_allocate: Decimal
    forecast_deficit: Decimal
    monthly_forecast_opening: Decimal | None = None
    monthly_forecast_closing: Decimal | None = None
    balance_start_date: date | None = None
    bucket_status: str
    opening_forecast_balance_set: bool
    mutations_enabled: bool
    calculated_at: datetime
    version: str

    # Transitional forecast aliases retained for a safe Backend/Frontend rollout.
    allocated_in: Decimal
    allocated_out: Decimal
    protected_reserve: Decimal
    raw_available: Decimal
    available_to_allocate: Decimal
    funding_deficit: Decimal
    opening_balance: Decimal | None = None
    monthly_opening: Decimal | None = None
    monthly_closing: Decimal | None = None
    opening_balance_set: bool


class FundAllocationParty(BaseModel):
    bucket_id: UUID
    project_id: UUID
    project_name: str
    system_key: str | None = None


class FundAllocationResponse(BaseModel):
    id: UUID
    reference_no: str
    source: FundAllocationParty
    target: FundAllocationParty
    amount: Decimal
    currency: str
    reason: str
    note: str | None = None
    status: str
    reversal_of: UUID | None = None
    created_by: str
    created_at: datetime
    source_balance_before: Decimal
    source_balance_after: Decimal
    target_balance_before: Decimal
    target_balance_after: Decimal
    source_balance_version: str
    target_balance_version: str


class FundAllocationListResponse(BaseModel):
    items: list[FundAllocationResponse] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False


class CreateFundAllocationRequest(BaseModel):
    source_project_id: UUID
    target_project_id: UUID
    amount: Decimal = Field(..., gt=0, max_digits=15, decimal_places=2)
    currency: str = Field(default="THB", pattern="^THB$")
    reason: str = Field(..., min_length=1, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)
    expected_source_balance_version: str = Field(..., min_length=1, max_length=128)
    idempotency_key: str = Field(..., min_length=8, max_length=200)

    @field_validator(
        "reason",
        "note",
        "expected_source_balance_version",
        "idempotency_key",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ReverseFundAllocationRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)
    idempotency_key: str = Field(..., min_length=8, max_length=200)
    expected_source_balance_version: str | None = Field(default=None, max_length=128)

    @field_validator(
        "reason",
        "idempotency_key",
        "expected_source_balance_version",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class SetOpeningBalanceRequest(BaseModel):
    amount: Decimal = Field(..., ge=0, max_digits=15, decimal_places=2)
    currency: str = Field(default="THB", pattern="^THB$")
    activation_month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    reason: str = Field(..., min_length=1, max_length=2000)
    idempotency_key: str = Field(..., min_length=8, max_length=200)

    @field_validator("reason", "idempotency_key", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()
