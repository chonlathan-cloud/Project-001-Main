"""
FlowAccount OpenAPI integration helpers.

This module keeps FlowAccount credentials and payload construction in the
backend. Frontend callers should only use Projects-001 endpoints.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

import httpx

from app.core.config import Settings, get_settings
from app.models.input_request import InputRequest

logger = logging.getLogger(__name__)

VAT_RATE = Decimal("0.07")
LABOR_WHT_RATE = Decimal("3.00")
TOKEN_REFRESH_SKEW_SECONDS = 300
VAT_MODES = {"no_vat", "vat_inclusive", "vat_exclusive"}
FLOWACCOUNT_CATEGORY_INT_FIELDS = {
    "systemCode",
    "categoryId",
    "creditId",
    "creditCategory",
    "debitId",
    "debitCategory",
}

_token_cache: dict[str, object] = {"access_token": None, "expires_at": 0.0}


class FlowAccountError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass(slots=True)
class FlowAccountReadiness:
    enabled: bool
    ready: bool
    can_sync_expense: bool
    can_sync_attachment: bool
    can_sync_supplier_invoice: bool
    can_mark_paid: bool
    missing_fields: list[str]
    errors: list[str]
    external_document_id: str


def _clean_text(value: object) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _money(value: object) -> Decimal:
    try:
        decimal_value = Decimal(str(value or 0))
    except Exception:
        decimal_value = Decimal("0")
    return decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _percent(value: object) -> Decimal:
    try:
        decimal_value = Decimal(str(value or 0))
    except Exception:
        decimal_value = Decimal("0")
    return decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _date_text(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def _format_amount(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _format_payment_withheld_percentage(value: Decimal) -> int:
    percentage = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole_percentage = percentage.to_integral_value(rounding=ROUND_HALF_UP)
    if percentage != whole_percentage:
        raise FlowAccountError("FlowAccount payment withholding percentage must be a whole number.")
    return int(whole_percentage)


def _format_quantity(value: object) -> float:
    try:
        return float(Decimal(str(value or 1)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
    except Exception:
        return 1.0


def _safe_flowaccount_message(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        validation_messages: list[str] = []

        def collect_validation_messages(value: Any, path: str = "") -> None:
            if len(validation_messages) >= 8:
                return
            if isinstance(value, dict):
                for child_key, child_value in value.items():
                    child_path = f"{path}.{child_key}" if path else str(child_key)
                    collect_validation_messages(child_value, child_path)
            elif isinstance(value, list):
                for index, child_value in enumerate(value):
                    collect_validation_messages(child_value, f"{path}[{index}]")
            else:
                message = _clean_text(value)
                if message:
                    validation_messages.append(f"{path}: {message}" if path else message)

        for key in ("errors", "Errors", "modelState", "ModelState", "validationErrors", "ValidationErrors", "data", "Data"):
            if key in payload:
                collect_validation_messages(payload.get(key), key)
        if validation_messages:
            return "; ".join(validation_messages)[:500]

        for key in ("message", "Message", "error", "Error", "detail", "Detail", "title", "Title"):
            value = _clean_text(payload.get(key))
            if value:
                return value[:500]
        code = payload.get("code")
        if code not in (None, "", 0, "0"):
            return f"FlowAccount returned error code {code}."
    return fallback


def _flowaccount_log_payload(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)[:2000]
    except TypeError:
        return str(payload)[:2000]


def flowaccount_external_document_id(request_id: UUID | str, settings: Settings | None = None) -> str:
    cleaned = _clean_text(request_id)
    if not cleaned:
        return ""
    try:
        return str(UUID(cleaned))
    except (TypeError, ValueError):
        return cleaned[:36]


def _request_external_document_id(input_request: InputRequest, settings: Settings | None = None) -> str:
    saved_external_id = _clean_text(input_request.flowaccount_external_document_id)
    if saved_external_id and len(saved_external_id) <= 36:
        return saved_external_id
    return flowaccount_external_document_id(input_request.id, settings)


def is_flowaccount_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.flowaccount_enabled)


def parse_expense_category_mapping(settings: Settings | None = None) -> dict[str, dict[str, Any]]:
    settings = settings or get_settings()
    raw_mapping = settings.flowaccount_expense_category_mapping_json
    if not raw_mapping:
        return {}
    cleaned_mapping = raw_mapping.strip()
    if (
        len(cleaned_mapping) >= 2
        and cleaned_mapping[0] == cleaned_mapping[-1]
        and cleaned_mapping[0] in {"'", '"'}
        and cleaned_mapping[1] == "{"
    ):
        cleaned_mapping = cleaned_mapping[1:-1]
    try:
        parsed = json.loads(cleaned_mapping)
    except json.JSONDecodeError as exc:
        raise FlowAccountError("FlowAccount expense category mapping JSON is invalid.") from exc
    if not isinstance(parsed, dict):
        raise FlowAccountError("FlowAccount expense category mapping must be a JSON object.")
    normalized_mapping: dict[str, dict[str, Any]] = {}
    for key, value in parsed.items():
        if not isinstance(value, dict):
            continue
        normalized_category = dict(value)
        for field_name in FLOWACCOUNT_CATEGORY_INT_FIELDS:
            if field_name not in normalized_category:
                continue
            try:
                normalized_category[field_name] = int(str(normalized_category[field_name]).strip())
            except (TypeError, ValueError) as exc:
                raise FlowAccountError(
                    f"FlowAccount category mapping field {key}.{field_name} must be numeric."
                ) from exc
        normalized_mapping[str(key)] = normalized_category
    return normalized_mapping


def request_wht_rate(input_request: InputRequest) -> Decimal:
    if input_request.accounting_wht_rate is not None:
        return _percent(input_request.accounting_wht_rate)
    if input_request.request_type == "ค่าแรง":
        return LABOR_WHT_RATE
    return Decimal("0.00")


def flowaccount_readiness(
    input_request: InputRequest,
    *,
    project_name: str | None = None,
    settings: Settings | None = None,
) -> FlowAccountReadiness:
    settings = settings or get_settings()
    expense_missing: list[str] = []
    expense_errors: list[str] = []
    supplier_missing: list[str] = []
    supplier_errors: list[str] = []
    payment_missing: list[str] = []
    payment_errors: list[str] = []
    external_id = _request_external_document_id(input_request, settings)

    if not settings.flowaccount_enabled:
        expense_errors.append("FlowAccount integration is disabled.")

    if not settings.flowaccount_client_id:
        expense_missing.append("FLOWACCOUNT_CLIENT_ID")
    if not settings.flowaccount_client_secret:
        expense_missing.append("FLOWACCOUNT_CLIENT_SECRET")
    has_flowaccount_credentials = bool(settings.flowaccount_client_id and settings.flowaccount_client_secret)

    mapping: dict[str, dict[str, Any]] = {}
    try:
        mapping = parse_expense_category_mapping(settings)
    except FlowAccountError as exc:
        expense_errors.append(str(exc))

    if input_request.entry_type != "EXPENSE":
        expense_errors.append("FlowAccount sync is not enabled for income requests yet.")
    if input_request.status != "APPROVED":
        expense_errors.append("Request must be APPROVED before syncing to FlowAccount.")

    amount = _money(input_request.approved_amount if input_request.approved_amount is not None else input_request.amount)
    if amount <= 0:
        expense_missing.append("approved_amount")
    if not _clean_text(input_request.request_type):
        expense_missing.append("request_type")
    if not _clean_text(input_request.vendor_name):
        expense_missing.append("vendor_name")
    if not input_request.document_date:
        expense_missing.append("document_date")
    if not _clean_text(input_request.receipt_storage_key):
        expense_missing.append("receipt_storage_key")

    vat_mode = _clean_text(input_request.accounting_vat_mode)
    if vat_mode not in VAT_MODES:
        expense_missing.append("accounting_vat_mode")

    request_types = {
        _clean_text(line_item.request_type) or _clean_text(input_request.request_type)
        for line_item in input_request.line_items or []
    }
    if not request_types:
        request_types = {_clean_text(input_request.request_type)}
    for request_type in sorted(item for item in request_types if item):
        if request_type not in mapping:
            expense_missing.append(f"FLOWACCOUNT_EXPENSE_CATEGORY_MAPPING_JSON.{request_type}")

    supplier_invoice_ready = True
    if vat_mode and vat_mode != "no_vat":
        required_tax_fields = {
            "vendor_tax_id": input_request.vendor_tax_id,
            "vendor_branch": input_request.vendor_branch,
            "vendor_address": input_request.vendor_address,
            "receipt_no": input_request.receipt_no,
        }
        for field, value in required_tax_fields.items():
            if not _clean_text(value):
                supplier_missing.append(field)
                supplier_invoice_ready = False
        if input_request.vendor_tax_id and len(str(input_request.vendor_tax_id).strip()) != 13:
            supplier_errors.append("vendor_tax_id must be 13 digits for P.P.30 Supplier Invoice.")
            supplier_invoice_ready = False

    wht_rate = request_wht_rate(input_request)
    if wht_rate >= 100:
        expense_errors.append("accounting_wht_rate must be less than 100.")
    try:
        _format_payment_withheld_percentage(wht_rate)
    except FlowAccountError as exc:
        payment_errors.append(str(exc))
    if wht_rate > 0:
        required_wht_fields = {
            "vendor_tax_id": input_request.vendor_tax_id,
            "vendor_branch": input_request.vendor_branch,
            "vendor_address": input_request.vendor_address,
        }
        for field, value in required_wht_fields.items():
            if not _clean_text(value):
                expense_missing.append(field)
        if input_request.vendor_tax_id and len(str(input_request.vendor_tax_id).strip()) != 13:
            expense_errors.append("vendor_tax_id must be 13 digits for withholding tax.")

    expense_exists = bool(_clean_text(input_request.flowaccount_expense_id))
    expense_ready = settings.flowaccount_enabled and not expense_missing and not expense_errors
    attachment_ready = (
        settings.flowaccount_enabled
        and has_flowaccount_credentials
        and expense_exists
        and bool(_clean_text(input_request.receipt_storage_key))
    )
    supplier_ready = (
        settings.flowaccount_enabled
        and has_flowaccount_credentials
        and expense_exists
        and supplier_invoice_ready
        and not supplier_missing
        and not supplier_errors
        and bool(_clean_text(input_request.receipt_storage_key))
        and vat_mode not in (None, "no_vat")
    )

    if settings.flowaccount_default_payment_method != "transfer":
        payment_missing.append("FLOWACCOUNT_DEFAULT_PAYMENT_METHOD=transfer")
    elif not settings.flowaccount_default_bank_account_id:
        payment_missing.append("FLOWACCOUNT_DEFAULT_BANK_ACCOUNT_ID")
    elif not str(settings.flowaccount_default_bank_account_id).strip().isdigit():
        payment_missing.append("FLOWACCOUNT_DEFAULT_BANK_ACCOUNT_ID numeric value")
    if not _clean_text(input_request.payment_reference):
        payment_missing.append("payment_reference")

    can_mark_paid = (
        settings.flowaccount_enabled
        and has_flowaccount_credentials
        and input_request.status == "APPROVED"
        and expense_exists
        and not payment_missing
        and not payment_errors
    )

    visible_payment_missing = payment_missing if expense_exists else []
    visible_payment_errors = payment_errors if expense_exists else []
    readiness_missing = list(dict.fromkeys(expense_missing + supplier_missing + visible_payment_missing))
    readiness_errors = list(dict.fromkeys(expense_errors + supplier_errors + visible_payment_errors))
    return FlowAccountReadiness(
        enabled=settings.flowaccount_enabled,
        ready=expense_ready,
        can_sync_expense=settings.flowaccount_enabled and has_flowaccount_credentials and (expense_ready or expense_exists),
        can_sync_attachment=attachment_ready,
        can_sync_supplier_invoice=supplier_ready,
        can_mark_paid=can_mark_paid,
        missing_fields=readiness_missing,
        errors=readiness_errors,
        external_document_id=external_id,
    )


def apply_readiness_to_request(input_request: InputRequest, readiness: FlowAccountReadiness) -> None:
    input_request.accounting_ready = readiness.ready
    input_request.accounting_readiness_errors = readiness.missing_fields + readiness.errors
    input_request.flowaccount_external_document_id = readiness.external_document_id
    if input_request.flowaccount_sync_status in (None, "", "NOT_READY") and readiness.ready:
        input_request.flowaccount_sync_status = "READY"
    if (
        input_request.flowaccount_sync_status == "PARTIAL_SYNC"
        and _clean_text(input_request.flowaccount_expense_id)
        and input_request.flowaccount_attachment_status != "FAILED"
    ):
        input_request.flowaccount_sync_status = "SYNCED"


def _require_flowaccount_settings(settings: Settings) -> None:
    if not settings.flowaccount_enabled:
        raise FlowAccountError("FlowAccount integration is disabled.")
    if not settings.flowaccount_client_id or not settings.flowaccount_client_secret:
        raise FlowAccountError("FlowAccount client id/secret are not configured.")


def _category_for_request_type(mapping: dict[str, dict[str, Any]], request_type: str | None) -> dict[str, Any]:
    if not request_type or request_type not in mapping:
        raise FlowAccountError(f"Missing FlowAccount expense category mapping for request type '{request_type or '-'}'.")
    return mapping[request_type]


def _document_amounts(input_request: InputRequest) -> dict[str, Decimal]:
    net_amount = _money(input_request.approved_amount if input_request.approved_amount is not None else input_request.amount)
    wht_rate = request_wht_rate(input_request)
    if wht_rate >= 100:
        raise FlowAccountError("accounting_wht_rate must be less than 100.")
    wht_fraction = wht_rate / Decimal("100")

    vat_mode = _clean_text(input_request.accounting_vat_mode) or "no_vat"
    if vat_mode == "vat_inclusive":
        if wht_rate > 0:
            divisor = Decimal("1") - (wht_fraction / (Decimal("1") + VAT_RATE))
            grand_total = (net_amount / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            grand_total = net_amount
        total_after_discount = grand_total
        vatable_amount = (grand_total / (Decimal("1") + VAT_RATE)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        vat_amount = (grand_total - vatable_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sub_total = grand_total
        wht_base = vatable_amount
    elif vat_mode == "vat_exclusive":
        divisor = Decimal("1") + VAT_RATE - wht_fraction
        vatable_amount = (net_amount / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sub_total = vatable_amount
        total_after_discount = vatable_amount
        vat_amount = (vatable_amount * VAT_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        grand_total = (vatable_amount + vat_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        wht_base = vatable_amount
    else:
        if wht_rate > 0:
            divisor = Decimal("1") - wht_fraction
            wht_base = (net_amount / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            wht_base = net_amount
        sub_total = wht_base
        total_after_discount = wht_base
        vatable_amount = Decimal("0.00")
        vat_amount = Decimal("0.00")
        grand_total = wht_base

    wht_amount = (wht_base * wht_fraction).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if wht_rate > 0 else Decimal("0.00")

    return {
        "net_amount": net_amount,
        "gross_amount": wht_base,
        "sub_total": sub_total,
        "total_after_discount": total_after_discount,
        "vatable_amount": vatable_amount,
        "vat_amount": vat_amount,
        "grand_total": grand_total,
        "wht_rate": wht_rate,
        "wht_amount": wht_amount,
    }


def _line_item_payloads(input_request: InputRequest, mapping: dict[str, dict[str, Any]], amounts: dict[str, Decimal]) -> list[dict[str, Any]]:
    source_items = list(input_request.line_items or [])
    if not source_items:
        request_type = _clean_text(input_request.request_type)
        category = _category_for_request_type(mapping, request_type)
        return [
            {
                **category,
                "description": _clean_text(input_request.note) or request_type or "Expense",
                "quantity": 1,
                "unitName": category.get("unitName") or "งาน",
                "pricePerUnit": _format_amount(amounts["total_after_discount"]),
                "total": _format_amount(amounts["total_after_discount"]),
                "discountAmount": 0,
                "vatRate": 7 if input_request.accounting_vat_mode in {"vat_inclusive", "vat_exclusive"} else -1,
            }
        ]

    total_source_amount = sum((_money(item.amount) for item in source_items), Decimal("0.00"))
    if total_source_amount <= 0:
        total_source_amount = amounts["total_after_discount"]

    payloads: list[dict[str, Any]] = []
    for item in source_items:
        request_type = _clean_text(item.request_type) or _clean_text(input_request.request_type)
        category = _category_for_request_type(mapping, request_type)
        raw_amount = _money(item.amount)
        share = raw_amount / total_source_amount if total_source_amount else Decimal("0")
        line_total = (amounts["total_after_discount"] * share).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        qty = Decimal(str(item.qty or 1))
        unit_price = line_total / qty if qty else line_total
        payloads.append(
            {
                **category,
                "description": item.description,
                "quantity": _format_quantity(item.qty),
                "unitName": category.get("unitName") or "งาน",
                "pricePerUnit": _format_amount(unit_price),
                "total": _format_amount(line_total),
                "discountAmount": 0,
                "vatRate": 7 if input_request.accounting_vat_mode in {"vat_inclusive", "vat_exclusive"} else -1,
            }
        )
    return payloads


class FlowAccountService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.flowaccount_base_url.rstrip("/")

    async def get_access_token(self) -> str:
        _require_flowaccount_settings(self.settings)
        now = time.time()
        cached_token = _token_cache.get("access_token")
        cached_expiry = float(_token_cache.get("expires_at") or 0)
        if cached_token and cached_expiry - TOKEN_REFRESH_SKEW_SECONDS > now:
            return str(cached_token)

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.settings.flowaccount_timeout_seconds)) as client:
            response = await client.post(
                f"{self.base_url}/token",
                data={
                    "grant_type": "client_credentials",
                    "scope": self.settings.flowaccount_scope,
                    "client_id": self.settings.flowaccount_client_id,
                    "client_secret": self.settings.flowaccount_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise FlowAccountError("FlowAccount token response was not JSON.", status_code=response.status_code) from exc

        if response.status_code >= 400 or payload.get("error"):
            raise FlowAccountError(
                _safe_flowaccount_message(payload, "FlowAccount token request failed."),
                status_code=response.status_code,
                payload=payload,
            )

        access_token = _clean_text(payload.get("access_token"))
        if not access_token:
            raise FlowAccountError("FlowAccount token response did not include access_token.", payload=payload)

        expires_in = int(payload.get("expires_in") or self.settings.flowaccount_token_cache_seconds)
        cache_seconds = min(expires_in, self.settings.flowaccount_token_cache_seconds)
        _token_cache["access_token"] = access_token
        _token_cache["expires_at"] = now + cache_seconds
        return access_token

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        token = await self.get_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.settings.flowaccount_timeout_seconds)) as client:
            response = await client.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)

        try:
            payload = response.json()
        except ValueError:
            payload = {"message": response.text[:500]}

        code = payload.get("code") if isinstance(payload, dict) else None
        response_status = payload.get("status") if isinstance(payload, dict) else None
        if (
            response.status_code >= 400
            or (isinstance(payload, dict) and payload.get("error"))
            or response_status is False
            or code not in (None, 0, "0")
        ):
            logger.warning(
                "FlowAccount request failed method=%s path=%s status_code=%s payload=%s",
                method,
                path,
                response.status_code,
                _flowaccount_log_payload(payload),
            )
            raise FlowAccountError(
                _safe_flowaccount_message(payload, "FlowAccount request failed."),
                status_code=response.status_code,
                payload=payload,
            )

        return payload if isinstance(payload, dict) else {"data": payload}

    def build_expense_payload(self, input_request: InputRequest, *, project_name: str | None = None) -> dict[str, Any]:
        mapping = parse_expense_category_mapping(self.settings)
        amounts = _document_amounts(input_request)
        vat_mode = _clean_text(input_request.accounting_vat_mode) or "no_vat"
        wht_rate = amounts["wht_rate"]
        use_inline_vat = True

        payload = {
            "expenseStructureType": "ExpenseInlineDocument",
            "contactName": input_request.vendor_name,
            "contactAddress": input_request.vendor_address or "",
            "contactTaxId": input_request.vendor_tax_id or "",
            "contactBranch": input_request.vendor_branch or "",
            "publishedOn": _date_text(input_request.document_date or input_request.request_date),
            "projectName": project_name or "",
            "reference": input_request.receipt_no or "",
            "externalDocumentId": _request_external_document_id(input_request, self.settings),
            "isVatInclusive": vat_mode == "vat_inclusive",
            "isVat": vat_mode in {"vat_inclusive", "vat_exclusive"},
            "isManualVat": False,
            "expenseCategoryView": 3,
            "subTotal": _format_amount(amounts["sub_total"]),
            "discountPercentage": 0,
            "discountAmount": 0,
            "totalAfterDiscount": _format_amount(amounts["total_after_discount"]),
            "vatAmount": _format_amount(amounts["vat_amount"]),
            "grandTotal": _format_amount(amounts["grand_total"]),
            "documentShowWithholdingTax": use_inline_vat or wht_rate > 0,
            "documentWithholdingTaxPercentage": _format_amount(wht_rate),
            "documentWithholdingTaxAmount": _format_amount(amounts["wht_amount"]),
            "remarks": input_request.note or "",
            "internalNotes": f"Projects-001 request {input_request.id}",
            "showSignatureOrStamp": True,
            "creditType": 3,
            "creditDays": 0,
            "dueDate": _date_text(input_request.document_date or input_request.request_date),
            "discountType": 1,
            "useInlineDiscount": True,
            "useInlineVat": use_inline_vat,
            "exemptAmount": 0 if vat_mode in {"vat_inclusive", "vat_exclusive"} else _format_amount(amounts["total_after_discount"]),
            "vatableAmount": _format_amount(amounts["vatable_amount"]),
            "items": _line_item_payloads(input_request, mapping, amounts),
        }
        return payload

    async def create_expense(self, input_request: InputRequest, *, project_name: str | None = None) -> dict[str, Any]:
        return await self._request("POST", "/expenses/inline", json=self.build_expense_payload(input_request, project_name=project_name))

    async def attach_expense_receipt(
        self,
        *,
        expense_id: str,
        file_bytes: bytes,
        file_name: str | None,
        content_type: str | None,
    ) -> dict[str, Any]:
        files = {
            "file": (
                PurePosixPath(file_name or "receipt").name,
                file_bytes,
                content_type or "application/octet-stream",
            )
        }
        return await self._request("POST", f"/expenses/{expense_id}/attachment", files=files)

    async def create_supplier_invoice(
        self,
        input_request: InputRequest,
        *,
        expense_id: str,
        file_bytes: bytes,
        file_name: str | None,
    ) -> dict[str, Any]:
        amounts = _document_amounts(input_request)
        payload = {
            "documentSerial": input_request.receipt_no,
            "contactName": input_request.vendor_name,
            "contactBranch": input_request.vendor_branch,
            "documentDate": _date_text(input_request.document_date),
            "contactTaxId": input_request.vendor_tax_id,
            "taxForm": 1,
            "vatableAmount": _format_amount(amounts["vatable_amount"]),
            "vatAmount": _format_amount(amounts["vat_amount"]),
            "file": {
                "fileName": PurePosixPath(file_name or "receipt").name,
                "base64Data": base64.b64encode(file_bytes).decode("ascii"),
            },
        }
        return await self._request("POST", f"/expenses/{expense_id}/supplier-invoice", json=payload)

    async def create_expense_payment(
        self,
        input_request: InputRequest,
        *,
        expense_id: str,
        payment_date: date,
    ) -> dict[str, Any]:
        if self.settings.flowaccount_default_payment_method != "transfer":
            raise FlowAccountError("Only transfer FlowAccount payment is supported in this phase.")
        amounts = _document_amounts(input_request)
        withheld_percentage = _format_payment_withheld_percentage(amounts["wht_rate"])
        payload: dict[str, Any] = {
            "paymentStructureType": "PaymentPaidTransfer",
            "paymentMethod": 5,
            "paymentDate": payment_date.isoformat(),
            "collected": _format_amount(amounts["net_amount"]),
            "withheldPercentage": withheld_percentage,
            "withheldAmount": _format_amount(amounts["wht_amount"]),
            "paymentRemarks": input_request.payment_reference or "",
            "remainingCollectedType": 0,
            "remainingCollected": 0,
        }
        try:
            payload["bankAccountId"] = int(str(self.settings.flowaccount_default_bank_account_id or "").strip())
        except ValueError as exc:
            raise FlowAccountError("FLOWACCOUNT_DEFAULT_BANK_ACCOUNT_ID must be a numeric FlowAccount bank account id.") from exc
        return await self._request("POST", f"/expenses/{expense_id}/payment", json=payload)


def flowaccount_document_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) else {}


def flowaccount_record_id(payload: dict[str, Any]) -> str | None:
    data = flowaccount_document_data(payload)
    return _clean_text(data.get("recordId") or data.get("documentId"))


def flowaccount_document_no(payload: dict[str, Any]) -> str | None:
    data = flowaccount_document_data(payload)
    return _clean_text(data.get("documentSerial"))
