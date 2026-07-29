"""Versioned Product Backend contracts consumed only by the Product MCP service."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class McpPrincipalRequest(ClosedModel):
    contract_version: Literal["1.0"] = "1.0"
    subject: str = Field(min_length=1, max_length=255)
    issuer: str = Field(min_length=8, max_length=2048)
    client_id: str = Field(min_length=1, max_length=255)
    environment: Literal["demo", "beta"]

    @field_validator("issuer")
    @classmethod
    def normalize_issuer(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if not cleaned.startswith("https://"):
            raise ValueError("issuer must use HTTPS")
        return cleaned


class McpAccessContext(ClosedModel):
    contract_version: Literal["1.0"] = "1.0"
    subject: str
    issuer: str
    client_id: str
    user_id: str
    environment: Literal["demo", "beta"]
    active: bool
    external_mcp_enabled: bool
    role: str
    permissions: list[str] = Field(default_factory=list, max_length=32)
    all_projects_read: bool = False
    assigned_project_ids: list[str] = Field(default_factory=list, max_length=1000)
    authorization_revision: str
    resolved_at: datetime


class McpProjectListRequest(McpPrincipalRequest):
    statuses: list[str] = Field(default_factory=list, max_length=10)
    cursor: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=20, ge=1, le=100)


class McpProjectRequest(McpPrincipalRequest):
    project_id: UUID


class McpProjectSummaryRequest(McpProjectRequest):
    as_of: datetime | None = None


class McpBOQVersionsRequest(McpProjectRequest):
    cursor: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=20, ge=1, le=100)


class McpBOQVersionRequest(McpProjectRequest):
    version: str | None = Field(default=None, min_length=1, max_length=128)
    as_of: datetime | None = None

    @model_validator(mode="after")
    def require_one_selector(self) -> McpBOQVersionRequest:
        if (self.version is None) == (self.as_of is None):
            raise ValueError("Provide exactly one of version or as_of.")
        return self


class McpBOQCompareRequest(McpProjectRequest):
    version_a: str = Field(min_length=1, max_length=128)
    version_b: str = Field(min_length=1, max_length=128)


class McpSearchRequest(McpPrincipalRequest):
    query: str = Field(min_length=1, max_length=500)
    domains: list[str] = Field(default_factory=list, max_length=10)
    project_id: UUID | None = None
    record_types: list[str] = Field(default_factory=list, max_length=20)
    date_from: date | None = None
    date_to: date | None = None
    cursor: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=20, ge=1, le=50)

    @model_validator(mode="after")
    def validate_date_range(self) -> McpSearchRequest:
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from must not be after date_to.")
            if (self.date_to - self.date_from).days > 366:
                raise ValueError("Search date range cannot exceed 366 days.")
        return self


class McpFetchRequest(McpPrincipalRequest):
    reference: str = Field(
        min_length=5,
        max_length=512,
        pattern=r"^[a-z_]+:[a-z_]+:[A-Za-z0-9._~-]+$",
    )
    version: str | None = Field(default=None, min_length=1, max_length=128)
    as_of: datetime | None = None
    max_content_chars: int = Field(default=4000, ge=1, le=20000)

    @model_validator(mode="after")
    def mutually_exclusive_version_selector(self) -> McpFetchRequest:
        if self.version is not None and self.as_of is not None:
            raise ValueError("version and as_of are mutually exclusive.")
        return self


class McpProjectAccessRequest(McpProjectRequest):
    cursor: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=20, ge=1, le=100)


class McpUserAccessRequest(McpPrincipalRequest):
    user_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$")


class McpProjectFinancialSummaryRequest(McpProjectRequest):
    as_of: datetime | None = None
    fresh: bool = True


class McpFinancialSearchRequest(McpPrincipalRequest):
    query: str | None = Field(default=None, min_length=1, max_length=300)
    project_id: UUID | None = None
    statuses: list[str] = Field(default_factory=list, max_length=20)
    record_types: list[
        Literal["input_request", "payment", "installment", "transaction"]
    ] = Field(default_factory=list, max_length=10)
    date_from: date | None = None
    date_to: date | None = None
    cursor: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> McpFinancialSearchRequest:
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from must not be after date_to.")
            if (self.date_to - self.date_from).days > 366:
                raise ValueError("Financial search date range cannot exceed 366 days.")
        return self


class McpPaymentRequest(McpPrincipalRequest):
    payment_id: UUID


class McpDocumentSearchRequest(McpPrincipalRequest):
    query: str | None = Field(default=None, min_length=1, max_length=300)
    project_id: UUID | None = None
    content_types: list[Literal["pdf", "image", "text", "audio", "video"]] = Field(
        default_factory=list,
        max_length=10,
    )
    date_from: date | None = None
    date_to: date | None = None
    cursor: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=10, ge=1, le=25)

    @model_validator(mode="after")
    def validate_date_range(self) -> McpDocumentSearchRequest:
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from must not be after date_to.")
            if (self.date_to - self.date_from).days > 366:
                raise ValueError("Document search date range cannot exceed 366 days.")
        return self


class McpDocumentRequest(McpPrincipalRequest):
    document_id: str = Field(
        min_length=5,
        max_length=255,
        pattern=r"^[A-Za-z0-9._~-]+$",
    )
    version: str | None = Field(default=None, min_length=1, max_length=128)


class McpDocumentContentRequest(McpDocumentRequest):
    page: int | None = Field(default=None, ge=1, le=500)
    section: str | None = Field(default=None, min_length=1, max_length=200)
    max_content_chars: int = Field(default=4000, ge=1, le=20000)


class McpInspectionListRequest(McpProjectRequest):
    statuses: list[Annotated[str, Field(min_length=1, max_length=32)]] = Field(
        default_factory=list,
        max_length=10,
    )
    severities: list[Annotated[str, Field(min_length=1, max_length=32)]] = Field(
        default_factory=list,
        max_length=10,
    )
    due_before: date | None = None
    overdue: bool | None = None
    cursor: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=20, ge=1, le=100)


class McpInspectionRequest(McpProjectRequest):
    item_id: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._~-]+$",
    )


class McpDailyReportsListRequest(McpProjectRequest):
    date_from: date | None = None
    date_to: date | None = None
    statuses: list[Annotated[str, Field(min_length=1, max_length=32)]] = Field(
        default_factory=list,
        max_length=10,
    )
    cursor: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> McpDailyReportsListRequest:
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from must not be after date_to.")
            if (self.date_to - self.date_from).days > 366:
                raise ValueError("Daily Report date range cannot exceed 366 days.")
        return self


class McpDailyReportRequest(McpPrincipalRequest):
    report_id: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._~-]+$",
    )
    version: str | None = Field(default=None, min_length=1, max_length=128)


class McpDailyReportVersionsRequest(McpPrincipalRequest):
    report_id: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._~-]+$",
    )
    cursor: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=20, ge=1, le=100)


class McpDashboardSummaryRequest(McpPrincipalRequest):
    project_ids: list[UUID] = Field(default_factory=list, max_length=50)
    date_from: date | None = None
    date_to: date | None = None
    fresh: bool = True

    @model_validator(mode="after")
    def validate_date_range(self) -> McpDashboardSummaryRequest:
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from must not be after date_to.")
            if (self.date_to - self.date_from).days > 366:
                raise ValueError("Dashboard date range cannot exceed 366 days.")
        return self


class McpProjectInsightsRequest(McpProjectRequest):
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> McpProjectInsightsRequest:
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from must not be after date_to.")
            if (self.date_to - self.date_from).days > 366:
                raise ValueError("Insight date range cannot exceed 366 days.")
        return self
