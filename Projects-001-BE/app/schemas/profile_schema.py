"""
Schemas for subcontractor profiles, admin management, and auth payloads.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

ADMIN_ROLE_VALUES = {"admin", "owner", "inspector"}


def _normalize_admin_role(value: str | None, *, default: str = "admin") -> str:
    cleaned = str(value or "").strip().lower()
    if not cleaned:
        return default
    if cleaned not in ADMIN_ROLE_VALUES:
        raise ValueError("role must be one of 'admin', 'owner', or 'inspector'.")
    return cleaned


def _normalize_admin_roles(value: list[str] | None, *, fallback: str = "admin") -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value or []:
        cleaned = _normalize_admin_role(item, default=fallback)
        if cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)

    fallback_role = _normalize_admin_role(fallback)
    if fallback_role not in seen:
        normalized.insert(0, fallback_role)
    return normalized


class BankAccountInfo(BaseModel):
    bank_name: str | None = None
    account_no: str | None = None
    account_name: str | None = None


class SubcontractorProfileItem(BaseModel):
    id: str
    line_uid: str | None = None
    line_picture_url: str | None = None
    profile_image_url: str | None = None
    name: str
    contact_name: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    assigned_project_ids: list[str] = Field(default_factory=list)
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
    contact_name: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    assigned_project_ids: list[str] | None = None
    vat_rate: float | None = None
    wht_rate: float | None = None
    retention_rate: float | None = None
    bank_account: BankAccountInfo | None = None
    is_active: bool | None = None


class UpdateMyProfileRequest(BaseModel):
    display_name: str | None = None
    name: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    company: str | None = None
    time: str | None = None
    bank_account: BankAccountInfo | None = None


class AdminDirectoryItem(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    role: str = "admin"
    roles: list[str] = Field(default_factory=list)
    is_active: bool = True
    granted_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: str | None) -> str:
        return _normalize_admin_role(value)

    @field_validator("roles", mode="before")
    @classmethod
    def validate_roles(cls, value: list[str] | None) -> list[str]:
        return _normalize_admin_roles(value)


class UpsertAdminRequest(BaseModel):
    email: str
    display_name: str | None = None
    role: str = "admin"
    roles: list[str] | None = None
    is_active: bool = True

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: str | None) -> str:
        return _normalize_admin_role(value)


class UpdateAdminRequest(BaseModel):
    display_name: str | None = None
    role: str | None = None
    roles: list[str] | None = None
    is_active: bool | None = None

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_admin_role(value)

    @field_validator("roles", mode="before")
    @classmethod
    def validate_roles(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_admin_roles(value)


class SessionUserPayload(BaseModel):
    role: str
    roles: list[str] = Field(default_factory=list)
    email: str | None = None
    display_name: str | None = None
    subcontractor_id: str | None = None
    line_uid: str | None = None
    permissions: list[str] = Field(default_factory=list)


class AuthSessionResponse(BaseModel):
    status: str
    session_token: str
    firebase_custom_token: str | None = None
    user: SessionUserPayload


class AdminLoginRequest(BaseModel):
    email: str | None = None
    display_name: str | None = None
    firebase_id_token: str | None = None
