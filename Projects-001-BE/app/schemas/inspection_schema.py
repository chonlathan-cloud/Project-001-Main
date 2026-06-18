"""
Schemas for project-level construction inspection workflows.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

RoundStatus = Literal["ACTIVE", "CLOSED", "ARCHIVED"]
DefectStatus = Literal["OPEN", "IN_PROGRESS", "READY_FOR_REVIEW", "RESOLVED"]
DefectSeverity = Literal["CRITICAL", "MAJOR", "MINOR", "COSMETIC"]
InspectionFileKind = Literal["PLAN_IMAGE", "BEFORE_PHOTO", "AFTER_PHOTO", "REPORT_PDF"]
ReportType = Literal["CLIENT", "CONTRACTOR", "MANAGEMENT"]

DEFAULT_INSPECTION_CATEGORIES = [
    "Architectural",
    "Electrical",
    "Plumbing",
    "Mechanical / HVAC",
    "Structural",
    "Finishes",
    "Safety",
    "Other",
]


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _clean_optional_text(value: object) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _upper_text(value: object) -> str:
    return _clean_text(value).upper().replace(" ", "_").replace("-", "_")


def _clean_unique_text_values(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        cleaned = _clean_optional_text(value)
        if cleaned is None:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


class InspectionProjectCategoriesUpdate(BaseModel):
    categories: list[str] = Field(default_factory=list)

    @field_validator("categories", mode="before")
    @classmethod
    def validate_categories(cls, value: list[str] | None) -> list[str]:
        categories = _clean_unique_text_values(value)
        if not categories:
            raise ValueError("At least one category is required.")
        return categories


class InspectionProjectCategoriesResponse(BaseModel):
    project_id: str
    categories: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None
    updated_by: str | None = None


class InspectionRoundCreate(BaseModel):
    name: str
    description: str | None = None
    target_close_at: datetime | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("Round name is required.")
        return cleaned

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: object) -> str | None:
        return _clean_optional_text(value)


class InspectionRoundUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: RoundStatus | None = None
    target_close_at: datetime | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def validate_optional_text(cls, value: object) -> str | None:
        return _clean_optional_text(value)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: object) -> str | None:
        return _upper_text(value) if value is not None else None


class InspectionRoundItem(BaseModel):
    id: str
    project_id: str
    name: str
    description: str | None = None
    status: RoundStatus = "ACTIVE"
    started_at: datetime | None = None
    target_close_at: datetime | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InspectionZoneCreate(BaseModel):
    name: str
    floor: str | None = None
    room: str | None = None
    sort_order: int = 0
    plan_file_id: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("Zone name is required.")
        return cleaned

    @field_validator("floor", "room", "plan_file_id", mode="before")
    @classmethod
    def validate_optional_text(cls, value: object) -> str | None:
        return _clean_optional_text(value)


class InspectionZoneUpdate(BaseModel):
    name: str | None = None
    floor: str | None = None
    room: str | None = None
    sort_order: int | None = None
    plan_file_id: str | None = None

    @field_validator("name", "floor", "room", "plan_file_id", mode="before")
    @classmethod
    def validate_optional_text(cls, value: object) -> str | None:
        return _clean_optional_text(value)


class InspectionZoneItem(BaseModel):
    id: str
    project_id: str
    round_id: str
    name: str
    floor: str | None = None
    room: str | None = None
    sort_order: int = 0
    plan_file_id: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InspectionDefectCreate(BaseModel):
    zone_id: str
    title: str
    description: str | None = None
    category: str = "Other"
    severity: DefectSeverity = "MINOR"
    status: DefectStatus = "OPEN"
    assigned_subcontractor_id: str | None = None
    assigned_subcontractor_name: str | None = None
    due_date: date | None = None
    plan_x: float | None = None
    plan_y: float | None = None
    before_file_ids: list[str] = Field(default_factory=list)

    @field_validator("zone_id", "title", mode="before")
    @classmethod
    def validate_required_text(cls, value: object) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("Required text field is empty.")
        return cleaned

    @field_validator(
        "description",
        "category",
        "assigned_subcontractor_id",
        "assigned_subcontractor_name",
        mode="before",
    )
    @classmethod
    def validate_optional_text(cls, value: object) -> str | None:
        return _clean_optional_text(value)

    @field_validator("severity", "status", mode="before")
    @classmethod
    def validate_upper_text(cls, value: object) -> str:
        return _upper_text(value)


class InspectionDefectUpdate(BaseModel):
    zone_id: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    severity: DefectSeverity | None = None
    assigned_subcontractor_id: str | None = None
    assigned_subcontractor_name: str | None = None
    due_date: date | None = None
    plan_x: float | None = None
    plan_y: float | None = None

    @field_validator(
        "zone_id",
        "title",
        "description",
        "category",
        "assigned_subcontractor_id",
        "assigned_subcontractor_name",
        mode="before",
    )
    @classmethod
    def validate_optional_text(cls, value: object) -> str | None:
        return _clean_optional_text(value)

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, value: object) -> str | None:
        return _upper_text(value) if value is not None else None


class InspectionStatusUpdate(BaseModel):
    status: DefectStatus
    comment: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: object) -> str:
        return _upper_text(value)

    @field_validator("comment", mode="before")
    @classmethod
    def validate_comment(cls, value: object) -> str | None:
        return _clean_optional_text(value)


class InspectionCommentCreate(BaseModel):
    comment: str

    @field_validator("comment", mode="before")
    @classmethod
    def validate_comment(cls, value: object) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("Comment is required.")
        return cleaned


class InspectionDefectItem(BaseModel):
    id: str
    display_no: str
    project_id: str
    round_id: str
    zone_id: str
    title: str
    description: str | None = None
    category: str = "Other"
    severity: DefectSeverity = "MINOR"
    status: DefectStatus = "OPEN"
    assigned_subcontractor_id: str | None = None
    assigned_subcontractor_name: str | None = None
    due_date: date | None = None
    plan_x: float | None = None
    plan_y: float | None = None
    before_file_ids: list[str] = Field(default_factory=list)
    after_file_ids: list[str] = Field(default_factory=list)
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    resolved_at: datetime | None = None


class InspectionFileItem(BaseModel):
    id: str
    project_id: str
    round_id: str
    defect_id: str | None = None
    zone_id: str | None = None
    kind: InspectionFileKind
    gcs_path: str
    content_type: str | None = None
    size_bytes: int = 0
    original_filename: str | None = None
    uploaded_by: str | None = None
    uploaded_at: datetime | None = None


class InspectionFileAccessResponse(BaseModel):
    file_id: str
    signed_url: str
    expires_in_minutes: int
    content_type: str | None = None
    original_filename: str | None = None


class InspectionEventItem(BaseModel):
    id: str
    project_id: str
    round_id: str
    defect_id: str | None = None
    event_type: str
    from_status: str | None = None
    to_status: str | None = None
    comment: str | None = None
    actor_id: str | None = None
    actor_role: str | None = None
    created_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class InspectionReportLogCreate(BaseModel):
    report_type: ReportType
    filters: dict = Field(default_factory=dict)

    @field_validator("report_type", mode="before")
    @classmethod
    def validate_report_type(cls, value: object) -> str:
        return _upper_text(value)


class InspectionReportLogItem(BaseModel):
    id: str
    project_id: str
    round_id: str
    report_type: ReportType
    filters: dict = Field(default_factory=dict)
    printed_by: str | None = None
    printed_at: datetime | None = None


class InspectionSummaryResponse(BaseModel):
    project_id: str
    round_id: str
    total_defects: int = 0
    open_defects: int = 0
    in_progress_defects: int = 0
    ready_for_review_defects: int = 0
    resolved_defects: int = 0
    overdue_count: int = 0
    severity_counts: dict[str, int] = Field(default_factory=dict)
    category_counts: dict[str, int] = Field(default_factory=dict)
    contractor_counts: dict[str, int] = Field(default_factory=dict)
    readiness_score: float = 0.0
