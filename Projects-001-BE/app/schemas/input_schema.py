"""
Schemas for the Input page submission flow.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ENTRY_TYPE_VALUES = {"EXPENSE", "INCOME"}
WORK_TYPE_VALUES = {
    "งานโครงสร้าง",
    "งานสถาปัตย์",
    "งานระบบ",
    "งานบริหารโครงการ",
}
WORK_TYPE_ALIASES = {
    "งานบริหาร": "งานบริหารโครงการ",
}
REQUEST_TYPE_VALUES = {
    "ค่าวัสดุ",
    "ค่าแรง",
    "ค่าเบิกล่วงหน้า",
    "ค่าใช้จ่ายทั่วไป",
}
REQUEST_TYPE_ALIASES = {
    "วัสดุ": "ค่าวัสดุ",
    "ค่าใช้จ่าย": "ค่าใช้จ่ายทั่วไป",
    "ทั่วไป": "ค่าใช้จ่ายทั่วไป",
    "แรงงาน": "ค่าแรง",
    "เบิกล่วงหน้า": "ค่าเบิกล่วงหน้า",
}


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_work_type(value: str | None) -> str | None:
    cleaned = _clean_optional_text(value)
    if cleaned is None:
        return None
    return WORK_TYPE_ALIASES.get(cleaned, cleaned)


def _normalize_request_type(value: str | None) -> str | None:
    cleaned = _clean_optional_text(value)
    if cleaned is None:
        return None
    return REQUEST_TYPE_ALIASES.get(cleaned, cleaned)


def _normalize_date_value(value: object) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    cleaned = _clean_optional_text(str(value))
    if cleaned is None:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    if "T" in cleaned:
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date()
        except ValueError:
            pass

    raise ValueError("Invalid date format. Use YYYY-MM-DD.")


class BankAccountPayload(BaseModel):
    bank_name: str | None = None
    account_no: str | None = None
    account_name: str | None = None

    @field_validator("bank_name", "account_no", "account_name", mode="before")
    @classmethod
    def clean_optional_fields(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


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
    ocr_raw_json: dict | None = None
    ocr_low_confidence_fields: list[str] = Field(default_factory=list)

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, value: str) -> str:
        normalized = str(value).strip().upper()
        if normalized not in ENTRY_TYPE_VALUES:
            raise ValueError("entry_type must be EXPENSE or INCOME.")
        return normalized

    @field_validator("requester_name")
    @classmethod
    def validate_requester_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("requester_name is required.")
        return cleaned

    @field_validator(
        "phone",
        "note",
        "vendor_name",
        "receipt_no",
        "receipt_file_name",
        "receipt_content_type",
        "receipt_storage_key",
        mode="before",
    )
    @classmethod
    def clean_optional_text_fields(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("work_type", mode="before")
    @classmethod
    def validate_work_type(cls, value: str | None) -> str | None:
        normalized = _normalize_work_type(value)
        if normalized is None:
            return None
        if normalized not in WORK_TYPE_VALUES:
            raise ValueError("Unsupported work_type.")
        return normalized

    @field_validator("request_type", mode="before")
    @classmethod
    def validate_request_type(cls, value: str | None) -> str | None:
        normalized = _normalize_request_type(value)
        if normalized is None:
            return None
        if normalized not in REQUEST_TYPE_VALUES:
            raise ValueError("Unsupported request_type.")
        return normalized

    @field_validator("request_date", "document_date", mode="before")
    @classmethod
    def validate_dates(cls, value: object) -> date | None:
        return _normalize_date_value(value)

    @model_validator(mode="after")
    def validate_business_rules(self) -> "InputRequestCreate":
        if self.request_type == "ค่าเบิกล่วงหน้า" and self.entry_type != "EXPENSE":
            raise ValueError("ค่าเบิกล่วงหน้า ใช้ได้เฉพาะรายการรายจ่ายเท่านั้น.")
        return self

    @field_validator("ocr_raw_json")
    @classmethod
    def validate_ocr_raw_json(cls, value: dict | None) -> dict | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("ocr_raw_json must be an object.")
        return value

    @field_validator("ocr_low_confidence_fields", mode="before")
    @classmethod
    def validate_ocr_low_confidence_fields(cls, value: object) -> list[str]:
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise ValueError("ocr_low_confidence_fields must be a list.")
        normalized: list[str] = []
        for item in value:
            cleaned = _clean_optional_text(str(item) if item is not None else None)
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized


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
    ocr_raw_json: dict | None = None
    ocr_low_confidence_fields: list[str] = Field(default_factory=list)
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

    @field_validator("requester_name")
    @classmethod
    def validate_requester_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("requester_name is required.")
        return cleaned

    @field_validator("phone", "note", "vendor_name", "receipt_no", mode="before")
    @classmethod
    def clean_optional_text_fields(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("work_type", mode="before")
    @classmethod
    def validate_work_type(cls, value: str | None) -> str | None:
        normalized = _normalize_work_type(value)
        if normalized is None:
            return None
        if normalized not in WORK_TYPE_VALUES:
            raise ValueError("Unsupported work_type.")
        return normalized

    @field_validator("request_type", mode="before")
    @classmethod
    def validate_request_type(cls, value: str | None) -> str | None:
        normalized = _normalize_request_type(value)
        if normalized is None:
            return None
        if normalized not in REQUEST_TYPE_VALUES:
            raise ValueError("Unsupported request_type.")
        return normalized

    @field_validator("request_date", "document_date", mode="before")
    @classmethod
    def validate_dates(cls, value: object) -> date | None:
        return _normalize_date_value(value)


class InputRequestApproveAction(BaseModel):
    approved_amount: float | None = Field(default=None, gt=0)
    review_note: str | None = None

    @field_validator("review_note", mode="before")
    @classmethod
    def clean_review_note(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


class InputRequestRejectAction(BaseModel):
    review_note: str = Field(..., min_length=1)

    @field_validator("review_note")
    @classmethod
    def validate_review_note(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("review_note is required.")
        return cleaned


class InputRequestMarkPaidAction(BaseModel):
    payment_reference: str | None = None
    review_note: str | None = None

    @field_validator("payment_reference", "review_note", mode="before")
    @classmethod
    def clean_optional_text_fields(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


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
    ocr_raw_json: dict | None = None
    low_confidence_fields: list[str] = Field(default_factory=list)
    message: str


class ReceiptUploadResponse(BaseModel):
    file_name: str
    content_type: str | None = None
    file_size_bytes: int
    storage_key: str
    message: str


class ReceiptAccessResponse(BaseModel):
    request_id: UUID
    file_name: str | None = None
    content_type: str | None = None
    storage_key: str
    signed_url: str
    expires_in_minutes: int
    message: str


class TempReceiptCleanupResponse(BaseModel):
    bucket_name: str
    checked_object_count: int
    deleted_object_count: int
    kept_referenced_count: int
    skipped_recent_count: int
    deleted_storage_keys: list[str] = Field(default_factory=list)
    kept_referenced_storage_keys: list[str] = Field(default_factory=list)
    skipped_recent_storage_keys: list[str] = Field(default_factory=list)
    older_than_hours: int
    message: str
