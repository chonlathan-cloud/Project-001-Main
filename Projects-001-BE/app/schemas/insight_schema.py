"""
Schemas for the Insight Warehouse API contract.

This module defines the normalized row shape, filter contract, summary cards,
and metadata needed by the admin-facing warehouse explorer page.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

SOURCE_TYPE_VALUES = {"INPUT_REQUEST", "INSTALLMENT", "TRANSACTION"}
FLOW_DIRECTION_VALUES = {"INFLOW", "OUTFLOW", "NEUTRAL"}
ENTRY_TYPE_VALUES = {"EXPENSE", "INCOME"}
DATE_FIELD_VALUES = {"event_date", "due_date", "approved_at", "paid_at", "created_at"}
SORT_BY_VALUES = {
    "event_date",
    "due_date",
    "amount",
    "created_at",
    "updated_at",
    "status",
    "project_name",
    "actor_name",
}
SORT_ORDER_VALUES = {"asc", "desc"}
EXPORT_FORMAT_VALUES = {"csv", "json"}


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_unique_uppercase_items(values: object) -> list[str]:
    if values in (None, ""):
        return []
    if not isinstance(values, list):
        raise ValueError("Expected a list value.")

    normalized: list[str] = []
    for item in values:
        cleaned = _clean_optional_text(str(item) if item is not None else None)
        if not cleaned:
            continue
        upper_value = cleaned.upper()
        if upper_value not in normalized:
            normalized.append(upper_value)
    return normalized


class InsightWarehouseNavigationTarget(BaseModel):
    label: str
    path: str


class InsightWarehouseFlag(BaseModel):
    key: str
    label: str
    tone: str = "neutral"


class InsightWarehouseRow(BaseModel):
    id: str
    source_type: str
    source_id: str
    project_id: UUID | None = None
    project_name: str | None = None
    actor_id: str | None = None
    actor_name: str | None = None
    reference_no: str | None = None
    title: str
    description: str | None = None
    entry_type: str | None = None
    flow_direction: str
    request_type: str | None = None
    status: str
    amount: float | None = None
    currency: str = "THB"
    event_date: date | None = None
    due_date: date | None = None
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_duplicate_flag: bool = False
    is_overdue: bool = False
    tags: list[str] = Field(default_factory=list)
    flags: list[InsightWarehouseFlag] = Field(default_factory=list)
    navigation_target: InsightWarehouseNavigationTarget | None = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str) -> str:
        normalized = str(value).strip().upper()
        if normalized not in SOURCE_TYPE_VALUES:
            raise ValueError(f"source_type must be one of {sorted(SOURCE_TYPE_VALUES)}.")
        return normalized

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, value: str | None) -> str | None:
        cleaned = _clean_optional_text(value)
        if cleaned is None:
            return None
        normalized = cleaned.upper()
        if normalized not in ENTRY_TYPE_VALUES:
            raise ValueError(f"entry_type must be one of {sorted(ENTRY_TYPE_VALUES)}.")
        return normalized

    @field_validator("flow_direction")
    @classmethod
    def validate_flow_direction(cls, value: str) -> str:
        normalized = str(value).strip().upper()
        if normalized not in FLOW_DIRECTION_VALUES:
            raise ValueError(
                f"flow_direction must be one of {sorted(FLOW_DIRECTION_VALUES)}."
            )
        return normalized

    @field_validator("reference_no", "title", "description", "request_type", "status", mode="before")
    @classmethod
    def clean_optional_text_fields(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        cleaned = _clean_optional_text(value) or "THB"
        return cleaned.upper()


class InsightWarehouseFilterSet(BaseModel):
    q: str | None = None
    quick_view: str | None = None
    project_id: UUID | None = None
    source_types: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    entry_types: list[str] = Field(default_factory=list)
    flow_directions: list[str] = Field(default_factory=list)
    duplicate_only: bool = False
    overdue_only: bool = False
    date_field: str = "event_date"
    date_from: date | None = None
    date_to: date | None = None
    amount_min: float | None = Field(default=None, ge=0)
    amount_max: float | None = Field(default=None, ge=0)

    @field_validator("q", "quick_view", mode="before")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("source_types", "statuses", "entry_types", "flow_directions", mode="before")
    @classmethod
    def normalize_list_fields(cls, value: object, info) -> list[str]:
        normalized = _clean_unique_uppercase_items(value)
        allowed_values = {
            "source_types": SOURCE_TYPE_VALUES,
            "entry_types": ENTRY_TYPE_VALUES,
            "flow_directions": FLOW_DIRECTION_VALUES,
        }.get(info.field_name)

        if allowed_values is None:
            return normalized

        invalid_values = [item for item in normalized if item not in allowed_values]
        if invalid_values:
            raise ValueError(
                f"{info.field_name} contains unsupported values: {', '.join(invalid_values)}."
            )
        return normalized

    @field_validator("date_field")
    @classmethod
    def validate_date_field(cls, value: str) -> str:
        cleaned = str(value).strip()
        if cleaned not in DATE_FIELD_VALUES:
            raise ValueError(f"date_field must be one of {sorted(DATE_FIELD_VALUES)}.")
        return cleaned

    @model_validator(mode="after")
    def validate_ranges(self) -> "InsightWarehouseFilterSet":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from cannot be after date_to.")
        if (
            self.amount_min is not None
            and self.amount_max is not None
            and self.amount_min > self.amount_max
        ):
            raise ValueError("amount_min cannot be greater than amount_max.")
        return self


class InsightWarehouseRowsQuery(InsightWarehouseFilterSet):
    sort_by: str = "event_date"
    sort_order: str = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=200)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, value: str) -> str:
        cleaned = str(value).strip()
        if cleaned not in SORT_BY_VALUES:
            raise ValueError(f"sort_by must be one of {sorted(SORT_BY_VALUES)}.")
        return cleaned

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in SORT_ORDER_VALUES:
            raise ValueError(f"sort_order must be one of {sorted(SORT_ORDER_VALUES)}.")
        return normalized


class InsightWarehousePageInfo(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class InsightWarehouseRowsResponse(BaseModel):
    items: list[InsightWarehouseRow] = Field(default_factory=list)
    page_info: InsightWarehousePageInfo
    applied_filters: InsightWarehouseRowsQuery
    last_updated_at: datetime | None = None
    empty_state_message: str | None = None


class InsightWarehouseSummaryCard(BaseModel):
    key: str
    label: str
    count: int | None = None
    amount: float | None = None
    tone: str = "neutral"
    description: str | None = None


class InsightWarehouseSummaryResponse(BaseModel):
    cards: list[InsightWarehouseSummaryCard] = Field(default_factory=list)
    applied_filters: InsightWarehouseFilterSet
    last_updated_at: datetime | None = None


class InsightWarehouseFilterOptionItem(BaseModel):
    value: str
    label: str
    count: int | None = None


class InsightWarehouseQuickView(BaseModel):
    key: str
    label: str
    description: str | None = None


class InsightWarehouseColumnDefinition(BaseModel):
    key: str
    label: str
    data_type: str
    sortable: bool = True
    default_visible: bool = True


class InsightWarehouseFiltersResponse(BaseModel):
    projects: list[InsightWarehouseFilterOptionItem] = Field(default_factory=list)
    source_types: list[InsightWarehouseFilterOptionItem] = Field(default_factory=list)
    statuses: list[InsightWarehouseFilterOptionItem] = Field(default_factory=list)
    entry_types: list[InsightWarehouseFilterOptionItem] = Field(default_factory=list)
    flow_directions: list[InsightWarehouseFilterOptionItem] = Field(default_factory=list)
    quick_views: list[InsightWarehouseQuickView] = Field(default_factory=list)
    columns: list[InsightWarehouseColumnDefinition] = Field(default_factory=list)
    date_fields: list[InsightWarehouseFilterOptionItem] = Field(default_factory=list)
    sort_fields: list[InsightWarehouseFilterOptionItem] = Field(default_factory=list)
    export_formats: list[InsightWarehouseFilterOptionItem] = Field(default_factory=list)
    last_updated_at: datetime | None = None


class InsightWarehouseExportQuery(InsightWarehouseFilterSet):
    format: str = "csv"

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in EXPORT_FORMAT_VALUES:
            raise ValueError(f"format must be one of {sorted(EXPORT_FORMAT_VALUES)}.")
        return normalized


class InsightWarehouseExportResponse(BaseModel):
    format: str
    file_name: str
    download_url: str | None = None
    expires_at: datetime | None = None
    message: str | None = None
