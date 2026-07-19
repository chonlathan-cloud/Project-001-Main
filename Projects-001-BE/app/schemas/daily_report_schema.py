"""
Schemas for the Daily Report workflow.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DailyReportProjectItem(BaseModel):
    id: str
    name: str
    status: str


class DailyReportProjectSettingsItem(BaseModel):
    project_id: str
    enabled: bool = True
    timezone: str = "Asia/Bangkok"
    submission_due_time: str = "17:00"
    review_target_time: str = "19:00"
    reminder_minutes_before: list[int] = Field(default_factory=lambda: [120, 30])
    expected_subcontractor_ids: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None
    updated_by: str | None = None


class DailyReportProjectSettingsUpdate(BaseModel):
    enabled: bool | None = None
    timezone: str | None = None
    submission_due_time: str | None = None
    review_target_time: str | None = None
    reminder_minutes_before: list[int] | None = None
    expected_subcontractor_ids: list[str] | None = None

    @field_validator("submission_due_time", "review_target_time")
    @classmethod
    def validate_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("time must use HH:MM format.")
        hour, minute = (int(part) for part in parts)
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("time must use HH:MM format.")
        return f"{hour:02d}:{minute:02d}"


class DailyReportSubmissionCreate(BaseModel):
    project_id: str
    report_date: date


class DailyReportIssueInput(BaseModel):
    title: str
    detail: str | None = None
    severity: str = "normal"
    needs_customer_decision: bool = False

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, value: str | None) -> str:
        normalized = str(value or "normal").strip().lower()
        if normalized not in {"low", "normal", "high", "critical"}:
            raise ValueError("severity must be low, normal, high, or critical.")
        return normalized


class DailyReportSubmissionUpdate(BaseModel):
    work_summary: str | None = None
    work_areas: list[str] | None = None
    manpower_total: int | None = Field(default=None, ge=0, le=10000)
    progress_percent: float | None = Field(default=None, ge=0, le=100)
    checklist: dict[str, bool] | None = None
    site_conditions: dict[str, str] | None = None
    issues: list[DailyReportIssueInput] | None = None
    tomorrow_plan: str | None = None
    notes: str | None = None


class DailyReportSubmissionItem(BaseModel):
    id: str
    project_id: str
    project_name: str | None = None
    report_date: str
    subcontractor_id: str
    subcontractor_name: str | None = None
    status: str
    work_summary: str | None = None
    work_areas: list[str] = Field(default_factory=list)
    manpower_total: int = 0
    progress_percent: float | None = None
    checklist: dict[str, bool] = Field(default_factory=dict)
    site_conditions: dict[str, str] = Field(default_factory=dict)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    tomorrow_plan: str | None = None
    notes: str | None = None
    media_ids: list[str] = Field(default_factory=list)
    change_request_reason: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DailyReportMediaItem(BaseModel):
    id: str
    project_id: str
    submission_id: str
    owner_id: str
    media_type: str
    file_name: str
    content_type: str
    size_bytes: int
    status: str
    storage_key: str | None = None
    created_at: datetime | None = None


class DailyReportMediaAccessResponse(BaseModel):
    media_id: str
    url: str
    expires_in_minutes: int


class DailyReportDraftUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    progress_percent: float | None = Field(default=None, ge=0, le=100)
    issues: list[dict[str, Any]] | None = None
    tomorrow_plan: str | None = None
    customer_note: str | None = None


class DailyReportChangeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)
    submission_ids: list[str] = Field(default_factory=list)


class DailyReportPublishRequest(BaseModel):
    publication_note: str | None = Field(default=None, max_length=1000)


class DailyReportItem(BaseModel):
    id: str
    project_id: str
    project_name: str | None = None
    report_date: str
    status: str
    title: str
    summary: str
    progress_percent: float | None = None
    manpower_total: int = 0
    issues: list[dict[str, Any]] = Field(default_factory=list)
    tomorrow_plan: str | None = None
    customer_note: str | None = None
    source_submission_ids: list[str] = Field(default_factory=list)
    expected_subcontractor_ids: list[str] = Field(default_factory=list)
    missing_subcontractor_ids: list[str] = Field(default_factory=list)
    submissions: list[dict[str, Any]] = Field(default_factory=list)
    media: list[dict[str, Any]] = Field(default_factory=list)
    acknowledgements: list[dict[str, Any]] = Field(default_factory=list)
    questions: list[dict[str, Any]] = Field(default_factory=list)
    published_version: int | None = None
    published_at: datetime | None = None
    published_by: str | None = None
    delivery_status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DailyReportVersionItem(BaseModel):
    id: str
    report_id: str
    version: int
    snapshot: dict[str, Any]
    publication_note: str | None = None
    published_at: datetime
    published_by: str


class DailyReportEventItem(BaseModel):
    id: str
    report_id: str | None = None
    submission_id: str | None = None
    project_id: str
    event_type: str
    actor_id: str
    actor_role: str
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DailyReportAcknowledgementCreate(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class DailyReportQuestionCreate(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class DailyReportCustomerActionItem(BaseModel):
    id: str
    report_id: str
    project_id: str
    customer_id: str
    note: str | None = None
    question: str | None = None
    status: str | None = None
    created_at: datetime


class DailyReportMembershipUpsert(BaseModel):
    principal_type: str
    principal_id: str
    project_id: str
    is_active: bool = True

    @field_validator("principal_type", mode="before")
    @classmethod
    def validate_principal_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"admin", "customer"}:
            raise ValueError("principal_type must be admin or customer.")
        return normalized


class DailyReportLineDestinationItem(BaseModel):
    project_id: str
    line_target_id: str | None = None
    target_type: str = "group"
    status: str = "INACTIVE"
    updated_at: datetime | None = None
    updated_by: str | None = None


class DailyReportLineDestinationUpdate(BaseModel):
    line_target_id: str | None = None
    target_type: str = "group"
    is_active: bool = True

    @field_validator("target_type", mode="before")
    @classmethod
    def validate_target_type(cls, value: str | None) -> str:
        normalized = str(value or "group").strip().lower()
        if normalized not in {"group", "user", "room"}:
            raise ValueError("target_type must be group, room, or user.")
        return normalized
