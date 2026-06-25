"""
Schemas for the Input page submission flow.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ENTRY_TYPE_VALUES = {"EXPENSE", "INCOME"}
ACCOUNTING_VAT_MODE_VALUES = {"no_vat", "vat_inclusive", "vat_exclusive"}
DEFAULT_WORK_TYPE_OPTIONS = [
    "งานโครงสร้าง",
    "งานสถาปัตย์",
    "งานระบบ",
    "งานบริหารโครงการ",
    "งานตกแต่ง (Build in)",
]
WORK_TYPE_VALUES = set(DEFAULT_WORK_TYPE_OPTIONS)
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


def _normalize_tags(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("tags must be a list.")

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = _clean_optional_text(str(item) if item is not None else None)
        if cleaned is None:
            raise ValueError("tags cannot contain empty values.")
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def _to_money(value: object) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _line_items_total(line_items: list["InputRequestLineItemPayload"]) -> float:
    return round(sum(_to_money(item.amount) for item in line_items), 2)


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


class InputRequestLineItemPayload(BaseModel):
    id: UUID | None = None
    description: str = Field(..., min_length=1)
    qty: float = Field(default=1, gt=0)
    unit_price: float = 0
    amount: float | None = None
    work_type: str | None = None
    request_type: str | None = None

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("line item description is required.")
        return cleaned

    @field_validator("work_type", mode="before")
    @classmethod
    def validate_work_type(cls, value: str | None) -> str | None:
        return _normalize_work_type(value)

    @field_validator("request_type", mode="before")
    @classmethod
    def validate_request_type(cls, value: str | None) -> str | None:
        normalized = _normalize_request_type(value)
        if normalized is None:
            return None
        if normalized not in REQUEST_TYPE_VALUES:
            raise ValueError("Unsupported line item request_type.")
        return normalized

    @model_validator(mode="after")
    def derive_amount(self) -> "InputRequestLineItemPayload":
        if self.amount is None:
            self.amount = round(float(self.qty or 0) * float(self.unit_price or 0), 2)
        else:
            self.amount = _to_money(self.amount)
        self.unit_price = _to_money(self.unit_price)
        return self


class InputRequestLineItemItem(BaseModel):
    id: UUID | None = None
    line_no: int
    description: str
    qty: float
    unit_price: float
    amount: float
    work_type: str | None = None
    request_type: str | None = None


class ProjectOptionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID = Field(..., alias="id")
    name: str
    project_type: str | None = None
    status: str


class InputDefaultValuesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    requester_name: str | None = None
    phone: str | None = None
    bank_account: BankAccountPayload = Field(default_factory=BankAccountPayload)
    work_types: list[str] = Field(default_factory=list, alias="workTypes")
    tags: list[str] = Field(default_factory=list)


class InputRequestCreate(BaseModel):
    project_id: UUID
    subcontractor_id: str | None = None
    entry_type: str = Field(..., pattern="^(EXPENSE|INCOME)$")
    requester_name: str = Field(..., min_length=1)
    phone: str | None = None
    request_date: date
    work_type: str | None = None
    request_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    note: str | None = None
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    vendor_branch: str | None = None
    vendor_address: str | None = None
    receipt_no: str | None = None
    document_date: date | None = None
    accounting_vat_mode: str | None = None
    bank_account: BankAccountPayload = Field(default_factory=BankAccountPayload)
    amount: float | None = Field(default=None, gt=0)
    line_items: list[InputRequestLineItemPayload] = Field(default_factory=list)
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
        "subcontractor_id",
        "note",
        "vendor_name",
        "vendor_tax_id",
        "vendor_branch",
        "vendor_address",
        "receipt_no",
        "accounting_vat_mode",
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
        return _normalize_work_type(value)

    @field_validator("request_type", mode="before")
    @classmethod
    def validate_request_type(cls, value: str | None) -> str | None:
        normalized = _normalize_request_type(value)
        if normalized is None:
            return None
        if normalized not in REQUEST_TYPE_VALUES:
            raise ValueError("Unsupported request_type.")
        return normalized

    @field_validator("accounting_vat_mode")
    @classmethod
    def validate_accounting_vat_mode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in ACCOUNTING_VAT_MODE_VALUES:
            raise ValueError("accounting_vat_mode must be no_vat, vat_inclusive, or vat_exclusive.")
        return value

    @field_validator("request_date", "document_date", mode="before")
    @classmethod
    def validate_dates(cls, value: object) -> date | None:
        return _normalize_date_value(value)

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value: object) -> list[str]:
        return _normalize_tags(value)

    @model_validator(mode="after")
    def validate_business_rules(self) -> "InputRequestCreate":
        if self.line_items:
            total_amount = _line_items_total(self.line_items)
            if total_amount <= 0:
                raise ValueError("line_items total amount must be greater than 0.")
            if self.amount is None or self.amount <= 0:
                self.amount = total_amount
            else:
                self.amount = _to_money(self.amount)
        elif self.amount is None or self.amount <= 0:
            raise ValueError("amount is required when line_items are not provided.")

        if self.entry_type == "INCOME":
            self.work_type = None
            self.request_type = None
            for item in self.line_items:
                item.work_type = None
                item.request_type = None
            if not self.tags:
                raise ValueError("INCOME requests require at least 1 tag.")
            return self

        if self.request_type == "ค่าเบิกล่วงหน้า" and self.entry_type != "EXPENSE":
            raise ValueError("ค่าเบิกล่วงหน้า ใช้ได้เฉพาะรายการรายจ่ายเท่านั้น.")

        for item in self.line_items:
            if item.request_type == "ค่าเบิกล่วงหน้า" and self.entry_type != "EXPENSE":
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
    subcontractor_id: str | None = None
    entry_type: str
    requester_name: str
    phone: str | None = None
    request_date: date
    work_type: str | None = None
    request_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    note: str | None = None
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    vendor_branch: str | None = None
    vendor_address: str | None = None
    receipt_no: str | None = None
    document_date: date | None = None
    accounting_vat_mode: str | None = None
    accounting_wht_rate: float | None = None
    bank_account: BankAccountPayload
    amount: float
    approved_amount: float | None = None
    line_items: list[InputRequestLineItemItem] = Field(default_factory=list)
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
    accounting_ready: bool = False
    accounting_readiness_errors: list[str] = Field(default_factory=list)
    flowaccount_sync_status: str = "NOT_READY"
    flowaccount_expense_id: str | None = None
    flowaccount_document_no: str | None = None
    flowaccount_external_document_id: str | None = None
    flowaccount_synced_at: datetime | None = None
    flowaccount_sync_error: str | None = None
    flowaccount_attachment_status: str = "NOT_READY"
    flowaccount_attachment_error: str | None = None
    flowaccount_attachment_synced_at: datetime | None = None
    flowaccount_supplier_invoice_status: str = "NOT_READY"
    flowaccount_supplier_invoice_error: str | None = None
    flowaccount_supplier_invoice_id: str | None = None
    flowaccount_supplier_invoice_synced_at: datetime | None = None
    flowaccount_payment_status: str = "NOT_READY"
    flowaccount_payment_error: str | None = None
    flowaccount_payment_synced_at: datetime | None = None
    flowaccount_linked_manually: bool = False
    flowaccount_duplicate_override_reason: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class InputRequestStatusSummaryItem(BaseModel):
    status: str
    count: int = 0
    amount: float = 0.0


class InputRequestAdminSummaryResponse(BaseModel):
    total_count: int = 0
    total_amount: float = 0.0
    pending_count: int = 0
    pending_amount: float = 0.0
    duplicate_count: int = 0
    paid_count: int = 0
    paid_amount: float = 0.0
    by_status: list[InputRequestStatusSummaryItem] = Field(default_factory=list)


class InputRequestAdminUpdate(BaseModel):
    subcontractor_id: str | None = None
    requester_name: str | None = Field(default=None, min_length=1)
    phone: str | None = None
    request_date: date | None = None
    work_type: str | None = None
    request_type: str | None = None
    tags: list[str] | None = None
    note: str | None = None
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    vendor_branch: str | None = None
    vendor_address: str | None = None
    receipt_no: str | None = None
    document_date: date | None = None
    accounting_vat_mode: str | None = None
    accounting_wht_rate: float | None = Field(default=None, ge=0, le=100)
    bank_account: BankAccountPayload | None = None
    review_note: str | None = None
    payment_reference: str | None = None
    amount: float | None = Field(default=None, gt=0)
    line_items: list[InputRequestLineItemPayload] | None = None

    @field_validator("requester_name")
    @classmethod
    def validate_requester_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("requester_name is required.")
        return cleaned

    @field_validator(
        "subcontractor_id",
        "phone",
        "note",
        "vendor_name",
        "vendor_tax_id",
        "vendor_branch",
        "vendor_address",
        "receipt_no",
        "accounting_vat_mode",
        "review_note",
        "payment_reference",
        mode="before",
    )
    @classmethod
    def clean_optional_text_fields(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("accounting_vat_mode")
    @classmethod
    def validate_accounting_vat_mode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in ACCOUNTING_VAT_MODE_VALUES:
            raise ValueError("accounting_vat_mode must be no_vat, vat_inclusive, or vat_exclusive.")
        return value

    @field_validator("work_type", mode="before")
    @classmethod
    def validate_work_type(cls, value: str | None) -> str | None:
        return _normalize_work_type(value)

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

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        return _normalize_tags(value)

    @model_validator(mode="after")
    def validate_line_items_total(self) -> "InputRequestAdminUpdate":
        if self.line_items is None:
            return self
        if not self.line_items:
            raise ValueError("line_items cannot be empty when provided.")
        total_amount = _line_items_total(self.line_items)
        if total_amount <= 0:
            raise ValueError("line_items total amount must be greater than 0.")
        self.amount = total_amount
        return self


class InputRequestApproveAction(BaseModel):
    approved_amount: float | None = Field(default=None, gt=0)
    line_items: list[InputRequestLineItemPayload] | None = None
    review_note: str | None = None

    @field_validator("review_note", mode="before")
    @classmethod
    def clean_review_note(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @model_validator(mode="after")
    def validate_line_items_total(self) -> "InputRequestApproveAction":
        if self.line_items is None:
            return self
        if not self.line_items:
            raise ValueError("line_items cannot be empty when provided.")
        total_amount = _line_items_total(self.line_items)
        if total_amount <= 0:
            raise ValueError("line_items total amount must be greater than 0.")
        self.approved_amount = total_amount
        return self


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
    payment_date: date | None = None
    review_note: str | None = None

    @field_validator("payment_reference", "review_note", mode="before")
    @classmethod
    def clean_optional_text_fields(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("payment_date", mode="before")
    @classmethod
    def validate_payment_date(cls, value: object) -> date | None:
        return _normalize_date_value(value)


class FlowAccountReadinessResponse(BaseModel):
    enabled: bool
    ready: bool
    can_sync_expense: bool
    can_sync_attachment: bool
    can_sync_supplier_invoice: bool
    can_mark_paid: bool
    missing_fields: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    external_document_id: str


class FlowAccountSyncAction(BaseModel):
    override_duplicate: bool = False
    override_reason: str | None = None

    @field_validator("override_reason", mode="before")
    @classmethod
    def clean_override_reason(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


class FlowAccountLinkExistingAction(BaseModel):
    expense_id: str = Field(..., min_length=1)
    document_no: str | None = None
    external_document_id: str | None = None
    note: str | None = None

    @field_validator("expense_id", "document_no", "external_document_id", "note", mode="before")
    @classmethod
    def clean_text_fields(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("expense_id")
    @classmethod
    def validate_expense_id(cls, value: str | None) -> str:
        if not value:
            raise ValueError("expense_id is required.")
        return value


class ReceiptExtractItem(BaseModel):
    description: str
    qty: float
    price: float
    amount: float = 0.0


class ReceiptExtractResponse(BaseModel):
    file_name: str
    content_type: str | None = None
    file_size_bytes: int
    suggested_entry_type: str
    vendor_name: str | None = None
    vendor_tax_id: str | None = None
    vendor_branch: str | None = None
    vendor_address: str | None = None
    receipt_no: str | None = None
    document_date: str | None = None
    suggested_request_type: str | None = None
    suggested_accounting_vat_mode: str | None = None
    total_amount: float = 0.0
    subtotal_amount: float = 0.0
    vat_amount: float = 0.0
    vat_rate: float = 0.0
    line_items_total: float = 0.0
    line_items_complete: bool = True
    page_count: int = 0
    warnings: list[str] = Field(default_factory=list)
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
