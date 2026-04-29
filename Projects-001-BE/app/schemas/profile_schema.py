"""
Schemas for subcontractor profiles, admin management, and auth payloads.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BankAccountInfo(BaseModel):
    bank_name: str | None = None
    account_no: str | None = None
    account_name: str | None = None


class SubcontractorProfileItem(BaseModel):
    id: str
    line_uid: str | None = None
    name: str
    tax_id: str | None = None
    vat_rate: float = 0.0
    wht_rate: float = 0.0
    retention_rate: float = 0.0
    bank_account: BankAccountInfo = Field(default_factory=BankAccountInfo)
    kyc_gcs_path: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UpdateSubcontractorProfileRequest(BaseModel):
    name: str | None = None
    tax_id: str | None = None
    vat_rate: float | None = None
    wht_rate: float | None = None
    retention_rate: float | None = None
    bank_account: BankAccountInfo | None = None
    is_active: bool | None = None


class AdminDirectoryItem(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    is_active: bool = True
    granted_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UpsertAdminRequest(BaseModel):
    email: str
    display_name: str | None = None
    is_active: bool = True


class UpdateAdminRequest(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None


class SessionUserPayload(BaseModel):
    role: str
    email: str | None = None
    display_name: str | None = None
    subcontractor_id: str | None = None
    line_uid: str | None = None


class AuthSessionResponse(BaseModel):
    status: str
    session_token: str
    firebase_custom_token: str | None = None
    user: SessionUserPayload


class AdminLoginRequest(BaseModel):
    email: str | None = None
    display_name: str | None = None
    firebase_id_token: str | None = None
