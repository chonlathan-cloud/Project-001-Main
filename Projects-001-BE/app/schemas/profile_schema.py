"""
Schemas for subcontractor profiles, admin management, and auth payloads.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

ADMIN_ROLE_VALUES = {"admin", "owner", "inspector"}
MCP_PERMISSION_VALUES = {
    "mcp_access",
    "financial_data_read",
    "sensitive_documents_read",
    "infrastructure_read",
    "audit_log_read",
}


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

    if normalized:
        return normalized

    fallback_role = _normalize_admin_role(fallback)
    return [fallback_role]


def _normalize_mcp_permissions(value: list[str] | None) -> list[str]:
    normalized = sorted({str(item or "").strip().lower() for item in value or []})
    unknown = set(normalized) - MCP_PERMISSION_VALUES
    if unknown:
        raise ValueError(f"Unsupported MCP permissions: {', '.join(sorted(unknown))}.")
    return normalized


def _normalize_mcp_issuer(value: str | None) -> str | None:
    cleaned = str(value or "").strip().rstrip("/")
    if not cleaned:
        return None
    if not cleaned.startswith("https://"):
        raise ValueError("mcp_oauth_issuer must use HTTPS.")
    return cleaned


class BankAccountInfo(BaseModel):
    bank_name: str | None = None
    account_no: str | None = None
    account_name: str | None = None


class SubcontractorProfileItem(BaseModel):
    id: str
    email: str | None = None
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


class CustomerProfileItem(BaseModel):
    id: str
    email: str | None = None
    line_uid: str | None = None
    line_picture_url: str | None = None
    name: str
    first_name: str | None = None
    nickname: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    assigned_project_ids: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UpdateCustomerProfileRequest(BaseModel):
    name: str | None = None
    first_name: str | None = None
    nickname: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    assigned_project_ids: list[str] | None = None
    is_active: bool | None = None


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
    department: str | None = None
    time: str | None = None
    timezone: str | None = None
    bank_account: BankAccountInfo | None = None


class AdminDirectoryItem(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    company: str | None = None
    department: str | None = None
    time: str | None = None
    timezone: str | None = None
    bank_account: BankAccountInfo = Field(default_factory=BankAccountInfo)
    role: str = "admin"
    roles: list[str] = Field(default_factory=list)
    assigned_project_ids: list[str] = Field(default_factory=list)
    external_mcp_enabled: bool = False
    mcp_oauth_issuer: str | None = None
    mcp_oauth_subject: str | None = None
    mcp_permissions: list[str] = Field(default_factory=list)
    mcp_all_projects_read: bool = False
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
    contact_name: str | None = None
    phone: str | None = None
    company: str | None = None
    department: str | None = None
    time: str | None = None
    timezone: str | None = None
    bank_account: BankAccountInfo | None = None
    role: str = "admin"
    roles: list[str] | None = None
    assigned_project_ids: list[str] = Field(default_factory=list)
    external_mcp_enabled: bool | None = None
    mcp_oauth_issuer: str | None = None
    mcp_oauth_subject: str | None = None
    mcp_permissions: list[str] | None = None
    mcp_all_projects_read: bool | None = None
    is_active: bool = True

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, value: str | None) -> str:
        return _normalize_admin_role(value)

    @field_validator("roles", mode="before")
    @classmethod
    def validate_roles(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_admin_roles(value)

    @field_validator("mcp_permissions", mode="before")
    @classmethod
    def validate_mcp_permissions(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_mcp_permissions(value)

    @field_validator("mcp_oauth_issuer", mode="before")
    @classmethod
    def validate_mcp_issuer(cls, value: str | None) -> str | None:
        return _normalize_mcp_issuer(value)


class UpdateAdminRequest(BaseModel):
    display_name: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    company: str | None = None
    department: str | None = None
    time: str | None = None
    timezone: str | None = None
    bank_account: BankAccountInfo | None = None
    role: str | None = None
    roles: list[str] | None = None
    assigned_project_ids: list[str] | None = None
    external_mcp_enabled: bool | None = None
    mcp_oauth_issuer: str | None = None
    mcp_oauth_subject: str | None = None
    mcp_permissions: list[str] | None = None
    mcp_all_projects_read: bool | None = None
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

    @field_validator("mcp_permissions", mode="before")
    @classmethod
    def validate_mcp_permissions(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_mcp_permissions(value)

    @field_validator("mcp_oauth_issuer", mode="before")
    @classmethod
    def validate_mcp_issuer(cls, value: str | None) -> str | None:
        return _normalize_mcp_issuer(value)


class SessionUserPayload(BaseModel):
    role: str
    roles: list[str] = Field(default_factory=list)
    email: str | None = None
    display_name: str | None = None
    subcontractor_id: str | None = None
    customer_id: str | None = None
    line_uid: str | None = None
    auth_provider: str | None = None
    access_request_id: str | None = None
    access_status: str | None = None
    rejection_reason: str | None = None
    tenant_id: str | None = None
    app_env: str | None = None
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


class AccessRequestItem(BaseModel):
    id: str
    provider: str
    email: str | None = None
    line_uid: str | None = None
    display_name: str | None = None
    picture_url: str | None = None
    status: str = "pending"
    requested_account_type: str | None = None
    company_name: str | None = None
    first_name: str | None = None
    nickname: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    bank_account: BankAccountInfo = Field(default_factory=BankAccountInfo)
    kyc_gcs_path: str | None = None
    decided_account_type: str | None = None
    decided_role: str | None = None
    decided_roles: list[str] = Field(default_factory=list)
    target_admin_id: str | None = None
    target_subcontractor_id: str | None = None
    target_customer_id: str | None = None
    rejection_reason: str | None = None
    decided_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    decided_at: datetime | None = None


class ApproveAccessRequestRequest(BaseModel):
    account_type: str = Field(default="subcontractor")
    existing_subcontractor_id: str | None = None
    project_ids: list[str] = Field(default_factory=list)
    display_name: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    company: str | None = None
    department: str | None = None
    time: str | None = None
    timezone: str | None = None
    tax_id: str | None = None
    bank_account: BankAccountInfo | None = None
    role: str = "admin"
    roles: list[str] | None = None

    @field_validator("account_type", mode="before")
    @classmethod
    def validate_account_type(cls, value: str | None) -> str:
        cleaned = str(value or "subcontractor").strip().lower()
        if cleaned not in {"admin", "subcontractor", "customer"}:
            raise ValueError("account_type must be admin, subcontractor, or customer.")
        return cleaned

    @field_validator("role", mode="before")
    @classmethod
    def validate_decision_role(cls, value: str | None) -> str:
        return _normalize_admin_role(value)

    @field_validator("roles", mode="before")
    @classmethod
    def validate_decision_roles(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_admin_roles(value)


class RejectAccessRequestRequest(BaseModel):
    reason: str | None = None
