"""
BOQ sync service.

Flow:
1. Read one Google Sheet tab using ADC.
2. Parse raw rows with Gemini.
3. Validate and normalize BOQ rows.
4. Persist them as the current SCD version for (project, boq_type, sheet_name).
5. Support workbook tab discovery and multi-tab sync.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from time import perf_counter
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status
from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GoogleAuthRequest
from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.boq import BOQItem, Project
from app.services.ai_service import parse_boq_sheet_with_gemini

logger = logging.getLogger(__name__)

SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
SHEETS_API_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
ADC_REFRESH_TIMEOUT_SECONDS = 15
SHEET_FETCH_TIMEOUT_SECONDS = 30
GEMINI_PARSE_TIMEOUT_SECONDS = 120
PERSIST_TIMEOUT_SECONDS = 30
TOTAL_SYNC_TIMEOUT_SECONDS = 180
BATCH_SYNC_PER_TAB_TIMEOUT_SECONDS = 195
NON_SYNCABLE_TAB_NAMES = {"summary", "work detail"}
MAX_BATCH_SYNC_TABS = get_settings().boq_batch_sync_max_tabs
HEADER_ROW_KEYWORDS = {
    "item",
    "item no",
    "description",
    "qty",
    "quantity",
    "unit",
    "material",
    "labor",
    "total",
    "amount",
    "cost",
}
TEMPLATE_TOTAL_TOLERANCE = Decimal("1.00")
TEMPLATE_SHEET_TOTAL_PATTERN = re.compile(r"^total\s*[-–—]\s*(?P<sheet>.+)$", re.IGNORECASE)
TEMPLATE_SECTION_TOTAL_PATTERN = re.compile(
    r"^total\s*(?:[-–—]\s*)?(?P<section>\d+(?:\.\d+)*)",
    re.IGNORECASE,
)
TEMPLATE_DETAIL_SHEETS = {"IN", "EE", "SN", "AC"}
DEFAULT_TEMPLATE_COLUMNS = {
    "item_no": 0,
    "description": 1,
    "unit": 5,
    "qty": 6,
    "material_unit_price": 7,
    "total_material": 8,
    "labor_unit_price": 9,
    "total_labor": 10,
    "grand_total": 11,
}
COMPACT_TEMPLATE_COLUMNS = {
    "item_no": 0,
    "description": 1,
    "unit": 2,
    "qty": 3,
    "material_unit_price": 4,
    "total_material": 5,
    "labor_unit_price": 6,
    "total_labor": 7,
    "grand_total": 8,
}


def _resolve_project_identity(
    project: Project | None = None,
    project_id: Any | None = None,
    project_name: str | None = None,
) -> tuple[Any, str | None]:
    if project_id is None and project is not None:
        project_id = project.id
    if project_name is None and project is not None:
        project_name = project.name
    if project_id is None:
        raise ValueError("project_id is required for BOQ sync.")
    return project_id, project_name


def _sync_context(
    project: Project | None = None,
    project_id: Any | None = None,
    project_name: str | None = None,
    boq_type: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    resolved_project_id = None
    resolved_project_name = None
    if project is not None or project_id is not None:
        resolved_project_id, resolved_project_name = _resolve_project_identity(
            project=project,
            project_id=project_id,
            project_name=project_name,
        )

    return {
        "project_id": str(resolved_project_id) if resolved_project_id else None,
        "project_name": resolved_project_name,
        "boq_type": boq_type,
        "sheet_name": sheet_name,
    }


def _normalize_boq_type(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized not in {"CUSTOMER", "SUBCONTRACTOR"}:
        raise ValueError(f"Invalid BOQ type: {value}")
    return normalized


def _normalize_sheet_name(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError("sheet_name is required for BOQ sync.")
    return normalized


async def _lock_boq_sync_scope(
    session: AsyncSession,
    project_id: Any,
    boq_type: str,
    sheet_name: str,
) -> None:
    lock_key = f"boq-sync:{project_id}:{boq_type}:{sheet_name.lower()}"
    lock_statement = select(func.pg_advisory_xact_lock(func.hashtext(lock_key)))
    try:
        await session.execute(lock_statement)
    except DBAPIError as exc:
        error_text = str(exc).lower()
        connection_closed = (
            exc.connection_invalidated
            or "connection was closed" in error_text
            or "connectiondoesnotexisterror" in error_text
        )
        if not connection_closed:
            raise
        logger.warning(
            "boq_sync.advisory_lock.connection_invalidated_retry project_id=%s boq_type=%s sheet_name=%s",
            project_id,
            boq_type,
            sheet_name,
            exc_info=True,
        )
        await session.rollback()
        await session.execute(lock_statement)


def _extract_spreadsheet_id(sheet_url: str) -> str:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)|/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google Sheet URL.",
        )

    spreadsheet_id = match.group(1) or match.group(2)
    if not spreadsheet_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract spreadsheet ID from the Google Sheet URL.",
        )
    return spreadsheet_id


def _refresh_google_access_token() -> str:
    credentials, _ = google_auth_default(scopes=[SHEETS_READONLY_SCOPE])
    credentials.refresh(GoogleAuthRequest())

    if not credentials.token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to obtain Google Sheets access token from ADC.",
        )

    return credentials.token


async def fetch_google_sheet_rows(sheet_url: str, sheet_name: str) -> list[list[Any]]:
    spreadsheet_id = _extract_spreadsheet_id(sheet_url)
    try:
        async with asyncio.timeout(ADC_REFRESH_TIMEOUT_SECONDS):
            access_token = await asyncio.to_thread(_refresh_google_access_token)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timed out while obtaining Google credentials from ADC.",
        ) from exc
    encoded_range = quote(sheet_name, safe="")
    url = f"{SHEETS_API_BASE_URL}/{spreadsheet_id}/values/{encoded_range}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(SHEET_FETCH_TIMEOUT_SECONDS)) as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"majorDimension": "ROWS"},
        )

    if response.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google Sheets access denied. Share the sheet with the runtime service account.",
        )
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sheet tab '{sheet_name}' was not found in the provided Google Sheet.",
        )
    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Google Sheet data: {response.text}",
        )

    payload = response.json()
    rows = payload.get("values", [])
    non_empty_rows = [row for row in rows if any(str(cell).strip() for cell in row)]

    if not non_empty_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sheet tab '{sheet_name}' does not contain any usable rows.",
        )

    return non_empty_rows


def _is_syncable_tab(sheet_name: str) -> bool:
    return sheet_name.strip().lower() not in NON_SYNCABLE_TAB_NAMES


def _is_header_like_row(row: list[Any]) -> bool:
    normalized_cells = []
    for cell in row:
        value = str(cell).strip().lower()
        if not value:
            continue
        normalized_cells.append(value)

    if not normalized_cells:
        return False

    keyword_hits = 0
    for cell in normalized_cells:
        if cell in HEADER_ROW_KEYWORDS:
            keyword_hits += 1
            continue
        if any(keyword in cell for keyword in HEADER_ROW_KEYWORDS):
            keyword_hits += 1

    return keyword_hits >= 2


def _prepare_rows_for_ai(rows: list[list[Any]]) -> tuple[list[list[Any]], dict[str, int]]:
    prepared_rows: list[list[Any]] = []
    header_rows_removed = 0
    duplicate_rows_removed = 0
    first_header_kept = False
    previous_signature: tuple[str, ...] | None = None

    for row in rows:
        cleaned_row = [str(cell).strip() if isinstance(cell, str) else cell for cell in row]
        if not any(str(cell).strip() for cell in cleaned_row):
            continue

        signature = tuple(str(cell).strip() for cell in cleaned_row)
        if signature == previous_signature:
            duplicate_rows_removed += 1
            continue

        if _is_header_like_row(cleaned_row):
            if first_header_kept:
                header_rows_removed += 1
                continue
            first_header_kept = True

        prepared_rows.append(cleaned_row)
        previous_signature = signature

    return prepared_rows, {
        "input_rows": len(rows),
        "prepared_rows": len(prepared_rows),
        "header_rows_removed": header_rows_removed,
        "duplicate_rows_removed": duplicate_rows_removed,
    }


def _cell_text(row: list[Any], index: int) -> str:
    if index < 0 or index >= len(row):
        return ""
    return str(row[index] or "").strip()


def _normalize_template_key(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().upper())


def _row_label_text(row: list[Any]) -> str:
    return " ".join(str(cell or "").strip() for cell in row if str(cell or "").strip())


def _parse_template_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    cleaned = str(value).strip()
    if not cleaned:
        return None
    if cleaned in {"-", "–", "—"}:
        return Decimal("0")

    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    cleaned = re.sub(r"(THB|บาท|฿)", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(",", "").replace("%", "").strip()
    if not cleaned or cleaned in {"-", "–", "—"}:
        return Decimal("0")

    try:
        value_decimal = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -value_decimal if negative else value_decimal


def _template_decimal_or_zero(value: Any) -> Decimal:
    return _parse_template_decimal(value) or Decimal("0")


def _parse_template_quantity(value: Any) -> Decimal | None:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned in {"-", "–", "—"}:
        return None
    return _parse_template_decimal(cleaned)


def _clean_template_unit(value: str) -> str | None:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned in {"-", "–", "—"}:
        return None
    return cleaned


def _is_placeholder_text(value: Any) -> bool:
    cleaned = str(value or "").strip()
    return not cleaned or cleaned in {"-", "–", "—"}


def _is_template_description_candidate(value: Any) -> bool:
    cleaned = str(value or "").strip()
    if _is_placeholder_text(cleaned):
        return False
    if TEMPLATE_SHEET_TOTAL_PATTERN.match(cleaned):
        return False
    if TEMPLATE_SECTION_TOTAL_PATTERN.match(cleaned):
        return False
    return _parse_template_decimal(cleaned) is None


def _template_item_no(row: list[Any], columns: dict[str, int]) -> str:
    value = _cell_text(row, columns["item_no"])
    return "" if _is_placeholder_text(value) else value


def _template_description(row: list[Any], columns: dict[str, int]) -> str:
    primary = _cell_text(row, columns["description"])
    if _is_template_description_candidate(primary):
        return primary

    scan_start = columns["description"] + 1
    scan_end = min(len(row), columns["unit"])
    for index in range(scan_start, scan_end):
        candidate = _cell_text(row, index)
        if _is_template_description_candidate(candidate):
            return candidate

    return "" if _is_placeholder_text(primary) else primary


def _find_template_header_index(rows: list[list[Any]]) -> int | None:
    for row_index, row in enumerate(rows):
        row_text = _row_label_text(row).lower()
        if "ลำดับ" in row_text and "รายการ" in row_text:
            return row_index
        if "รายการ" in row_text and "จำนวน" in row_text:
            return row_index
        if "item" in row_text and "description" in row_text:
            return row_index
    return None


def _find_cell_index(row: list[Any], *keywords: str) -> int | None:
    normalized_keywords = [keyword.lower() for keyword in keywords]
    for index, cell in enumerate(row):
        value = str(cell or "").strip().lower()
        if not value:
            continue
        if all(keyword in value for keyword in normalized_keywords):
            return index
    return None


def _find_unit_price_column(subheader: list[Any], total_column: int, min_column: int = 0) -> int:
    candidates = []
    for index, cell in enumerate(subheader):
        value = str(cell or "").strip().lower()
        if "ต่อหน่วย" in value and min_column <= index < total_column:
            candidates.append(index)
    if candidates:
        return candidates[-1]
    return max(min_column, total_column - 1)


def _template_columns(rows: list[list[Any]]) -> dict[str, int]:
    columns = DEFAULT_TEMPLATE_COLUMNS.copy()
    header_index = _find_template_header_index(rows)
    if header_index is None:
        return columns

    header = rows[header_index]
    subheader = rows[header_index + 1] if header_index + 1 < len(rows) else []
    description_index = _find_cell_index(header, "รายการ")
    qty_index = _find_cell_index(header, "จำนวน")
    unit_index = _find_cell_index(header, "หน่วย")
    if description_index == 1 and qty_index == 3 and unit_index is None:
        return COMPACT_TEMPLATE_COLUMNS.copy()

    detected = {
        "item_no": _find_cell_index(header, "ลำดับ") or _find_cell_index(subheader, "ที่"),
        "description": description_index,
        "unit": unit_index,
        "qty": qty_index,
        "total_material": _find_cell_index(subheader, "รวมค่าวัสดุ"),
        "total_labor": _find_cell_index(subheader, "รวมค่าแรง"),
        "grand_total": _find_cell_index(header, "รวมราคา"),
    }

    for key, value in detected.items():
        if value is not None:
            columns[key] = value

    columns["material_unit_price"] = _find_unit_price_column(
        subheader,
        total_column=columns["total_material"],
    )
    columns["labor_unit_price"] = _find_unit_price_column(
        subheader,
        total_column=columns["total_labor"],
        min_column=columns["total_material"] + 1,
    )

    return columns


def _template_amounts_from_columns(
    row: list[Any],
    columns: dict[str, int],
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
    material_unit_price = _template_decimal_or_zero(_cell_text(row, columns["material_unit_price"]))
    total_material = _template_decimal_or_zero(_cell_text(row, columns["total_material"]))
    labor_unit_price = _template_decimal_or_zero(_cell_text(row, columns["labor_unit_price"]))
    total_labor = _template_decimal_or_zero(_cell_text(row, columns["total_labor"]))
    grand_total = _template_decimal_or_zero(_cell_text(row, columns["grand_total"]))

    if grand_total == 0 and (total_material != 0 or total_labor != 0):
        grand_total = total_material + total_labor

    return material_unit_price, total_material, labor_unit_price, total_labor, grand_total


def _extract_template_total_amounts(
    row: list[Any],
    columns: dict[str, int],
) -> tuple[Decimal, Decimal, Decimal] | None:
    values = (
        _parse_template_decimal(_cell_text(row, columns["total_material"])),
        _parse_template_decimal(_cell_text(row, columns["total_labor"])),
        _parse_template_decimal(_cell_text(row, columns["grand_total"])),
    )
    if any(value is None for value in values):
        return None
    return values[0], values[1], values[2]


def _add_template_totals(
    current: tuple[Decimal, Decimal, Decimal],
    values: tuple[Decimal, Decimal, Decimal],
) -> tuple[Decimal, Decimal, Decimal]:
    return (
        current[0] + values[0],
        current[1] + values[1],
        current[2] + values[2],
    )


def _extract_template_section_total(
    row: list[Any],
    columns: dict[str, int],
) -> tuple[str, tuple[Decimal, Decimal, Decimal]] | None:
    for cell in row:
        match = TEMPLATE_SECTION_TOTAL_PATTERN.match(str(cell or "").strip())
        if not match:
            continue
        totals = _extract_template_total_amounts(row, columns)
        if totals is None:
            return None
        return match.group("section"), totals
    return None


def _find_template_sheet_total(
    sheet_name: str,
    rows: list[list[Any]],
    columns: dict[str, int],
) -> tuple[int, tuple[Decimal, Decimal, Decimal]] | None:
    sheet_key = _normalize_template_key(sheet_name)
    for row_index, row in enumerate(rows):
        for cell_index, cell in enumerate(row):
            match = TEMPLATE_SHEET_TOTAL_PATTERN.match(str(cell or "").strip())
            if not match:
                continue
            if _normalize_template_key(match.group("sheet")) != sheet_key:
                continue
            totals = _extract_template_total_amounts(row, columns)
            if totals is None:
                raise ValueError(
                    f"Template total row for '{sheet_name}' must contain material, labor, and grand total amounts."
                )
            return row_index, totals
    return None


def _is_template_header_row(row: list[Any]) -> bool:
    row_text = _row_label_text(row).lower()
    thai_header_hits = sum(
        1
        for keyword in ("ลำดับ", "รายการ", "หน่วย", "จำนวน", "ค่าวัสดุ", "ค่าแรง", "รวมราคา")
        if keyword in row_text
    )
    return thai_header_hits >= 2 or _is_header_like_row(row)


def _is_template_blank_or_divider(row: list[Any]) -> bool:
    non_empty = [str(cell or "").strip() for cell in row if str(cell or "").strip()]
    if not non_empty:
        return True
    return all(value in {"-", "–", "—"} for value in non_empty)


def _template_item_level(item_no: str, is_detail_row: bool, active_level_2: int | None) -> int:
    if is_detail_row:
        return 3 if active_level_2 is not None else 2

    if re.fullmatch(r"\d+", item_no or ""):
        return 1
    if re.fullmatch(r"\d+\.\d+", item_no or ""):
        return 2
    if re.fullmatch(r"\d+(?:\.\d+){2,}", item_no or ""):
        return 3
    return 1


def _template_qty_and_unit(
    row: list[Any],
    columns: dict[str, int],
) -> tuple[Decimal, str | None]:
    first = _cell_text(row, columns["unit"])
    second = _cell_text(row, columns["qty"])
    first_number = _parse_template_quantity(first)
    second_number = _parse_template_quantity(second)

    if first_number is not None and second_number is None:
        return first_number, _clean_template_unit(second)
    if second_number is not None:
        return second_number, _clean_template_unit(first)
    return Decimal("0"), _clean_template_unit(first) or _clean_template_unit(second)


def _validate_template_sheet_total(
    sheet_name: str,
    expected: tuple[Decimal, Decimal, Decimal],
    actual: tuple[Decimal, Decimal, Decimal],
) -> str:
    labels = ("material", "labor", "total")
    mismatches: list[str] = []
    for label, expected_value, actual_value in zip(labels, expected, actual, strict=True):
        delta = actual_value - expected_value
        if abs(delta) > TEMPLATE_TOTAL_TOLERANCE:
            mismatches.append(
                f"{label} expected {expected_value:,.2f}, parsed {actual_value:,.2f}, delta {delta:,.2f}"
            )

    if mismatches:
        raise ValueError(
            f"Template validation failed for tab '{sheet_name}': "
            + "; ".join(mismatches)
        )

    return (
        f"Template parser validated TOTAL - {sheet_name}: "
        f"material {actual[0]:,.2f}, labor {actual[1]:,.2f}, total {actual[2]:,.2f}."
    )


def _template_total_mismatches(
    expected: tuple[Decimal, Decimal, Decimal],
    actual: tuple[Decimal, Decimal, Decimal],
) -> list[str]:
    labels = ("material", "labor", "total")
    mismatches: list[str] = []
    for label, expected_value, actual_value in zip(labels, expected, actual, strict=True):
        delta = actual_value - expected_value
        if abs(delta) > TEMPLATE_TOTAL_TOLERANCE:
            mismatches.append(
                f"{label} expected {expected_value:,.2f}, parsed {actual_value:,.2f}, delta {delta:,.2f}"
            )
    return mismatches


def _format_template_validation_failure(
    sheet_name: str,
    mismatches: list[str],
) -> str:
    return f"Template validation failed for tab '{sheet_name}': " + "; ".join(mismatches)


def _validate_template_section_totals(
    sheet_name: str,
    expected_totals: dict[str, tuple[Decimal, Decimal, Decimal]],
    actual_totals: dict[str, tuple[Decimal, Decimal, Decimal]],
) -> str:
    mismatches: list[str] = []
    for section, expected in expected_totals.items():
        actual = actual_totals.get(section, (Decimal("0"), Decimal("0"), Decimal("0")))
        labels = ("material", "labor", "total")
        for label, expected_value, actual_value in zip(labels, expected, actual, strict=True):
            delta = actual_value - expected_value
            if abs(delta) > TEMPLATE_TOTAL_TOLERANCE:
                mismatches.append(
                    f"Total {section} {label} expected {expected_value:,.2f}, parsed {actual_value:,.2f}, delta {delta:,.2f}"
                )

    if mismatches:
        logger.warning(
            "boq_sync.template_section_validation.warning sheet=%s mismatches=%s",
            sheet_name,
            "; ".join(mismatches),
        )
        return (
            f"Section total warnings: "
            f"{len(mismatches)} mismatched values. "
            "Sync continued because sheet-level TOTAL matched."
        )

    if not expected_totals:
        return "No section totals found to validate."
    return f"Validated {len(expected_totals)} section totals."


def _parse_template_summary_block(
    rows: list[list[Any]],
    columns: dict[str, int],
) -> tuple[list[dict[str, Any]], tuple[Decimal, Decimal, Decimal]]:
    parsed_items: list[dict[str, Any]] = []
    actual_material = Decimal("0")
    actual_labor = Decimal("0")
    actual_total = Decimal("0")

    for row_index, row in enumerate(rows):
        if _is_template_blank_or_divider(row) or _is_template_header_row(row):
            continue
        if _extract_template_section_total(row, columns) is not None:
            continue

        item_no = _template_item_no(row, columns)
        description = _template_description(row, columns)
        if not description and _is_template_description_candidate(item_no):
            description = item_no
            item_no = ""
        if not description and not item_no:
            continue

        (
            material_unit_price,
            total_material,
            labor_unit_price,
            total_labor,
            grand_total,
        ) = _template_amounts_from_columns(row, columns)
        qty, unit = _template_qty_and_unit(row, columns)
        has_amount = any(value != 0 for value in (total_material, total_labor, grand_total))
        is_summary_row = has_amount or qty > 0 or unit is not None
        if not is_summary_row:
            continue

        parsed_items.append(
            {
                "index": row_index,
                "wbs_level": 1,
                "parent_index": None,
                "item_no": item_no or None,
                "description": description or item_no,
                "qty": qty,
                "unit": unit,
                "material_unit_price": material_unit_price,
                "labor_unit_price": labor_unit_price,
                "total_material": total_material,
                "total_labor": total_labor,
                "grand_total": grand_total,
            }
        )
        if has_amount:
            actual_material += total_material
            actual_labor += total_labor
            actual_total += grand_total

    return parsed_items, (actual_material, actual_labor, actual_total)


def _zero_template_reference_amounts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reference_items: list[dict[str, Any]] = []
    for item in items:
        reference_item = item.copy()
        reference_item["qty"] = Decimal("0")
        reference_item["material_unit_price"] = Decimal("0")
        reference_item["labor_unit_price"] = Decimal("0")
        reference_item["total_material"] = Decimal("0")
        reference_item["total_labor"] = Decimal("0")
        reference_item["grand_total"] = Decimal("0")
        reference_items.append(reference_item)
    return reference_items


def _template_semantic_enrichment_reasons(items: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    if any(not _is_template_description_candidate(item.get("description")) for item in items):
        reasons.append("missing_or_placeholder_description")
    return reasons


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _merge_gemini_semantics(
    template_items: list[dict[str, Any]],
    gemini_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    gemini_by_index: dict[int, dict[str, Any]] = {}
    for item in gemini_items:
        source_index = _coerce_int(item.get("index"))
        if source_index is None:
            continue
        gemini_by_index[source_index] = item

    merged_items: list[dict[str, Any]] = []
    update_count = 0

    for item in template_items:
        merged_item = item.copy()
        source_index = _coerce_int(item.get("index"))
        gemini_item = gemini_by_index.get(source_index) if source_index is not None else None
        if gemini_item is None:
            merged_items.append(merged_item)
            continue

        gemini_description = str(gemini_item.get("description") or "").strip()
        if (
            _is_template_description_candidate(gemini_description)
            and not _is_template_description_candidate(merged_item.get("description"))
        ):
            merged_item["description"] = gemini_description
            update_count += 1

        gemini_item_no = str(gemini_item.get("item_no") or "").strip()
        if gemini_item_no and _is_placeholder_text(merged_item.get("item_no")):
            merged_item["item_no"] = gemini_item_no
            update_count += 1

        # Template parser owns hierarchy. Gemini may enrich labels, but must not
        # rewrite wbs_level/parent_index because that directly changes display tree.
        merged_items.append(merged_item)

    return merged_items, update_count


def parse_template_boq_sheet(sheet_name: str, rows: list[list[Any]]) -> dict[str, Any] | None:
    if _normalize_template_key(sheet_name) not in TEMPLATE_DETAIL_SHEETS:
        return None

    columns = _template_columns(rows)
    sheet_total = _find_template_sheet_total(sheet_name, rows, columns)
    if sheet_total is None:
        return None

    sheet_total_row_index, expected_totals = sheet_total
    summary_items, summary_totals = _parse_template_summary_block(
        rows[:sheet_total_row_index],
        columns,
    )
    parsed_items: list[dict[str, Any]] = []
    active_level_indexes: dict[int, int] = {}
    actual_material = Decimal("0")
    actual_labor = Decimal("0")
    actual_total = Decimal("0")
    active_section_keys: dict[int, str] = {}
    expected_section_totals: dict[str, tuple[Decimal, Decimal, Decimal]] = {}
    actual_section_totals: dict[str, tuple[Decimal, Decimal, Decimal]] = {}

    for row_index, row in enumerate(rows[sheet_total_row_index + 1 :], start=sheet_total_row_index + 1):
        if _is_template_blank_or_divider(row) or _is_template_header_row(row):
            continue
        section_total = _extract_template_section_total(row, columns)
        if section_total is not None:
            section_key, totals = section_total
            expected_section_totals[section_key] = totals
            continue

        item_no = _template_item_no(row, columns)
        description = _template_description(row, columns)
        row_label = _row_label_text(row)
        if not description and _is_template_description_candidate(item_no):
            description = item_no
            item_no = ""

        if not description and not item_no:
            continue
        if TEMPLATE_SHEET_TOTAL_PATTERN.match(row_label):
            continue

        (
            material_unit_price,
            total_material,
            labor_unit_price,
            total_labor,
            grand_total,
        ) = _template_amounts_from_columns(row, columns)
        qty, unit = _template_qty_and_unit(row, columns)
        has_amount = any(value != 0 for value in (total_material, total_labor, grand_total))
        is_detail_row = has_amount or qty > 0 or unit is not None
        wbs_level = _template_item_level(
            item_no=item_no,
            is_detail_row=is_detail_row,
            active_level_2=active_level_indexes.get(2),
        )
        parent_index = active_level_indexes.get(wbs_level - 1)

        parsed_items.append(
            {
                "index": row_index,
                "wbs_level": wbs_level,
                "parent_index": parent_index,
                "item_no": item_no or None,
                "description": description or item_no,
                "qty": qty,
                "unit": unit,
                "material_unit_price": material_unit_price,
                "labor_unit_price": labor_unit_price,
                "total_material": total_material,
                "total_labor": total_labor,
                "grand_total": grand_total,
            }
        )

        if has_amount:
            actual_material += total_material
            actual_labor += total_labor
            actual_total += grand_total
            row_totals = (total_material, total_labor, grand_total)
            for section_key in active_section_keys.values():
                actual_section_totals[section_key] = _add_template_totals(
                    actual_section_totals.get(
                        section_key,
                        (Decimal("0"), Decimal("0"), Decimal("0")),
                    ),
                    row_totals,
                )
        if not is_detail_row:
            active_level_indexes[wbs_level] = row_index
            if item_no:
                active_section_keys[wbs_level] = item_no
            for level in list(active_level_indexes):
                if level > wbs_level:
                    active_level_indexes.pop(level, None)
                    active_section_keys.pop(level, None)

    if not parsed_items:
        raise ValueError(f"Template parser found TOTAL - {sheet_name}, but no BOQ detail rows.")

    detail_totals = (actual_material, actual_labor, actual_total)
    detail_mismatches = _template_total_mismatches(expected_totals, detail_totals)
    if detail_mismatches:
        summary_mismatches = _template_total_mismatches(expected_totals, summary_totals)
        if summary_items and not summary_mismatches:
            logger.warning(
                "boq_sync.template_detail_validation.warning sheet=%s mismatches=%s",
                sheet_name,
                "; ".join(detail_mismatches),
            )
            parsed_items = summary_items + _zero_template_reference_amounts(parsed_items)
            enrichment_reasons = [
                "summary_fallback_used",
                "detail_total_mismatch",
                *_template_semantic_enrichment_reasons(parsed_items),
            ]
            return {
                "parsed_items": parsed_items,
                "enrichment_reasons": enrichment_reasons,
                "validation_message": (
                    f"Template parser used summary block for {sheet_name} because detail rows did not match TOTAL - {sheet_name}. "
                    f"Summary total validated: material {summary_totals[0]:,.2f}, labor {summary_totals[1]:,.2f}, total {summary_totals[2]:,.2f}. "
                    "Detail rows were retained as zero-amount reference rows."
                ),
            }
        raise ValueError(_format_template_validation_failure(sheet_name, detail_mismatches))

    validation_message = _validate_template_sheet_total(
        sheet_name=sheet_name,
        expected=expected_totals,
        actual=detail_totals,
    )
    section_validation_message = _validate_template_section_totals(
        sheet_name=sheet_name,
        expected_totals=expected_section_totals,
        actual_totals=actual_section_totals,
    )
    enrichment_reasons = _template_semantic_enrichment_reasons(parsed_items)
    if section_validation_message.startswith("Section total warnings"):
        enrichment_reasons.append("section_total_warning")

    return {
        "parsed_items": parsed_items,
        "enrichment_reasons": enrichment_reasons,
        "validation_message": f"{validation_message} {section_validation_message}",
    }


async def fetch_google_sheet_tabs(sheet_url: str) -> list[dict[str, Any]]:
    spreadsheet_id = _extract_spreadsheet_id(sheet_url)
    try:
        async with asyncio.timeout(ADC_REFRESH_TIMEOUT_SECONDS):
            access_token = await asyncio.to_thread(_refresh_google_access_token)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timed out while obtaining Google credentials from ADC.",
        ) from exc

    url = f"{SHEETS_API_BASE_URL}/{spreadsheet_id}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(SHEET_FETCH_TIMEOUT_SECONDS)) as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "sheets(properties(title,index))"},
        )

    if response.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google Sheets access denied. Share the sheet with the runtime service account.",
        )
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Sheet workbook was not found.",
        )
    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Google Sheet tabs: {response.text}",
        )

    payload = response.json()
    sheets = payload.get("sheets", [])
    tabs: list[dict[str, Any]] = []
    for entry in sheets:
        properties = entry.get("properties", {})
        name = str(properties.get("title") or "").strip()
        if not name:
            continue
        syncable = _is_syncable_tab(name)
        tabs.append(
            {
                "name": name,
                "syncable": syncable,
                "default_selected": syncable,
            }
        )

    if not tabs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Google Sheet workbook does not contain any usable tabs.",
        )

    return tabs


def _to_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    if value is None or value == "":
        return default
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    cleaned = str(value).replace(",", "").strip()
    if not cleaned:
        return default
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value: {value}") from exc


def _normalize_parsed_items(parsed_items: list[dict]) -> list[dict]:
    normalized_items: list[dict] = []

    for position, item in enumerate(parsed_items):
        try:
            source_index = int(item.get("index", position))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid index at parsed row {position}.") from exc
        description = (item.get("description") or "").strip() or None
        item_no = (item.get("item_no") or "").strip() or None
        qty = _to_decimal(item.get("qty"), default=Decimal("0"))
        material_unit_price = _to_decimal(item.get("material_unit_price"))
        labor_unit_price = _to_decimal(item.get("labor_unit_price"))
        total_material = _to_decimal(item.get("total_material"))
        total_labor = _to_decimal(item.get("total_labor"))
        grand_total = _to_decimal(
            item.get("grand_total"),
            default=total_material + total_labor,
        )
        unit = (item.get("unit") or "").strip() or None

        has_content = any(
            [
                item_no,
                description,
                qty > 0,
                material_unit_price > 0,
                labor_unit_price > 0,
                total_material > 0,
                total_labor > 0,
                grand_total > 0,
            ]
        )
        if not has_content:
            continue

        wbs_level_raw = item.get("wbs_level")
        try:
            wbs_level = int(wbs_level_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid wbs_level at parsed row {source_index}.") from exc
        if wbs_level < 1:
            # Gemini can occasionally emit 0 for section/header-like rows.
            # Treat those as root rows instead of failing the whole sheet.
            wbs_level = 1

        parent_index_raw = item.get("parent_index")
        if parent_index_raw in (None, ""):
            parent_index = None
        else:
            try:
                parent_index = int(parent_index_raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid parent_index at parsed row {source_index}.") from exc
            if parent_index >= source_index:
                raise ValueError(
                    f"parent_index must reference an earlier row at parsed row {source_index}."
                )

        normalized_items.append(
            {
                "source_index": source_index,
                "parent_index": parent_index,
                "wbs_level": wbs_level,
                "item_no": item_no,
                "description": description,
                "qty": qty,
                "unit": unit,
                "material_unit_price": material_unit_price,
                "labor_unit_price": labor_unit_price,
                "total_material": total_material,
                "total_labor": total_labor,
                "grand_total": grand_total,
            }
        )

    if not normalized_items:
        raise ValueError("No valid BOQ rows were parsed from the selected sheet.")

    return normalized_items


async def persist_boq_version(
    session: AsyncSession,
    project_id: Any,
    boq_type: str,
    sheet_name: str,
    parsed_items: list[dict],
) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    normalized_boq_type = _normalize_boq_type(boq_type)
    normalized_sheet_name = _normalize_sheet_name(sheet_name)
    normalized_items = _normalize_parsed_items(parsed_items)

    await _lock_boq_sync_scope(
        session=session,
        project_id=project_id,
        boq_type=normalized_boq_type,
        sheet_name=normalized_sheet_name,
    )
    close_result = await session.execute(
        update(BOQItem)
        .where(BOQItem.project_id == project_id)
        .where(func.upper(func.trim(BOQItem.boq_type)) == normalized_boq_type)
        .where(func.lower(func.trim(BOQItem.sheet_name)) == normalized_sheet_name.lower())
        .where(BOQItem.valid_to.is_(None))
        .values(valid_to=now)
    )
    version_closed_items = int(close_result.rowcount or 0)

    source_index_to_row: dict[int, BOQItem] = {}
    inserted_rows: list[BOQItem] = []

    for item in normalized_items:
        row = BOQItem(
            project_id=project_id,
            boq_type=normalized_boq_type,
            sheet_name=normalized_sheet_name,
            wbs_level=item["wbs_level"],
            item_no=item["item_no"],
            description=item["description"],
            qty=item["qty"],
            unit=item["unit"],
            material_unit_price=item["material_unit_price"],
            labor_unit_price=item["labor_unit_price"],
            total_material=item["total_material"],
            total_labor=item["total_labor"],
            grand_total=item["grand_total"],
            valid_from=now,
            valid_to=None,
        )
        session.add(row)
        inserted_rows.append(row)
        source_index_to_row[item["source_index"]] = row

    await session.flush()

    for item in normalized_items:
        if item["parent_index"] is None:
            continue
        row = source_index_to_row[item["source_index"]]
        parent = source_index_to_row.get(item["parent_index"])
        if parent is None:
            raise ValueError(
                f"Parent row {item['parent_index']} was not found for parsed row {item['source_index']}."
            )
        row.parent_id = parent.id

    await session.commit()

    return {
        "inserted_items": len(inserted_rows),
        "version_closed_items": version_closed_items,
    }


async def sync_boq_sheet(
    session: AsyncSession,
    project: Project | None,
    boq_type: str,
    sheet_url: str,
    sheet_name: str,
    project_id: Any | None = None,
    project_name: str | None = None,
) -> dict[str, Any]:
    resolved_project_id, resolved_project_name = _resolve_project_identity(
        project=project,
        project_id=project_id,
        project_name=project_name,
    )
    normalized_boq_type = _normalize_boq_type(boq_type)
    normalized_sheet_name = _normalize_sheet_name(sheet_name)
    context = _sync_context(
        project_id=resolved_project_id,
        project_name=resolved_project_name,
        boq_type=normalized_boq_type,
        sheet_name=normalized_sheet_name,
    )
    logger.info("boq_sync.start", extra=context)
    total_started_at = perf_counter()

    try:
        try:
            await session.rollback()
        except Exception as exc:
            logger.warning(
                "boq_sync.release_existing_transaction.warning error=%s",
                exc,
                exc_info=True,
                extra=context,
            )
            await session.close()

        async with asyncio.timeout(TOTAL_SYNC_TIMEOUT_SECONDS):
            logger.info("boq_sync.fetch_sheet.start", extra=context)
            fetch_started_at = perf_counter()
            try:
                async with asyncio.timeout(SHEET_FETCH_TIMEOUT_SECONDS + ADC_REFRESH_TIMEOUT_SECONDS):
                    raw_rows = await fetch_google_sheet_rows(
                        sheet_url=sheet_url,
                        sheet_name=normalized_sheet_name,
                    )
            except TimeoutError as exc:
                logger.exception("boq_sync.fetch_sheet.timeout", extra=context)
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Timed out while fetching sheet tab '{normalized_sheet_name}'.",
                ) from exc
            fetch_elapsed_ms = round((perf_counter() - fetch_started_at) * 1000, 1)
            logger.info(
                "boq_sync.fetch_sheet.done rows=%s elapsed_ms=%s",
                len(raw_rows),
                fetch_elapsed_ms,
                extra=context,
            )

            prepared_rows, row_stats = _prepare_rows_for_ai(raw_rows)
            logger.info(
                (
                    "boq_sync.prepare_rows.done input_rows=%s prepared_rows=%s "
                    "header_rows_removed=%s duplicate_rows_removed=%s"
                ),
                row_stats["input_rows"],
                row_stats["prepared_rows"],
                row_stats["header_rows_removed"],
                row_stats["duplicate_rows_removed"],
                extra=context,
            )
            if not prepared_rows:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Sheet tab '{normalized_sheet_name}' does not contain any usable BOQ rows after preprocessing.",
                )

            parse_started_at = perf_counter()
            parse_strategy = "gemini"
            validation_message = ""
            template_result = parse_template_boq_sheet(
                sheet_name=normalized_sheet_name,
                rows=prepared_rows,
            )
            if template_result is not None:
                parse_strategy = "template"
                parsed_items = template_result["parsed_items"]
                validation_message = template_result["validation_message"]
                enrichment_reasons = template_result.get("enrichment_reasons") or []
                if enrichment_reasons:
                    logger.info(
                        "boq_sync.gemini_enrichment.start reasons=%s",
                        ",".join(enrichment_reasons),
                        extra=context,
                    )
                    try:
                        async with asyncio.timeout(GEMINI_PARSE_TIMEOUT_SECONDS):
                            gemini_items = await parse_boq_sheet_with_gemini(
                                sheet_name=normalized_sheet_name,
                                raw_data=prepared_rows,
                            )
                        parsed_items, enriched_count = _merge_gemini_semantics(
                            template_items=parsed_items,
                            gemini_items=gemini_items,
                        )
                        parse_strategy = "template+gemini"
                        validation_message = (
                            f"{validation_message} "
                            f"Gemini semantic enrichment updated {enriched_count} fields "
                            f"for reasons: {', '.join(enrichment_reasons)}."
                        )
                    except Exception as exc:
                        logger.warning(
                            "boq_sync.gemini_enrichment.skipped error=%s",
                            exc,
                            exc_info=True,
                            extra=context,
                        )
                        validation_message = (
                            f"{validation_message} "
                            f"Gemini semantic enrichment skipped: {exc}."
                        )
                logger.info(
                    "boq_sync.template_parse.done parsed_items=%s elapsed_ms=%s",
                    len(parsed_items),
                    round((perf_counter() - parse_started_at) * 1000, 1),
                    extra=context,
                )
            else:
                logger.info("boq_sync.gemini_parse.start", extra=context)
                try:
                    async with asyncio.timeout(GEMINI_PARSE_TIMEOUT_SECONDS):
                        parsed_items = await parse_boq_sheet_with_gemini(
                            sheet_name=normalized_sheet_name,
                            raw_data=prepared_rows,
                        )
                except TimeoutError as exc:
                    logger.exception("boq_sync.gemini_parse.timeout", extra=context)
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail=(
                            f"Timed out while parsing sheet tab '{normalized_sheet_name}' with Gemini. "
                            "Please retry or use a smaller sheet."
                        ),
                    ) from exc
                parse_elapsed_ms = round((perf_counter() - parse_started_at) * 1000, 1)
                logger.info(
                    "boq_sync.gemini_parse.done parsed_items=%s elapsed_ms=%s",
                    len(parsed_items),
                    parse_elapsed_ms,
                    extra=context,
                )

            logger.info("boq_sync.persist.start", extra=context)
            persist_started_at = perf_counter()
            try:
                async with asyncio.timeout(PERSIST_TIMEOUT_SECONDS):
                    persistence_result = await persist_boq_version(
                        session=session,
                        project_id=resolved_project_id,
                        boq_type=normalized_boq_type,
                        sheet_name=normalized_sheet_name,
                        parsed_items=parsed_items,
                    )
            except TimeoutError as exc:
                logger.exception("boq_sync.persist.timeout", extra=context)
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=(
                        f"Timed out while saving BOQ rows for tab '{normalized_sheet_name}'. "
                        "No changes were committed."
                    ),
                ) from exc
            persist_elapsed_ms = round((perf_counter() - persist_started_at) * 1000, 1)
            logger.info(
                "boq_sync.persist.done inserted_items=%s closed_items=%s elapsed_ms=%s",
                persistence_result["inserted_items"],
                persistence_result["version_closed_items"],
                persist_elapsed_ms,
                extra=context,
            )
    except HTTPException:
        logger.warning("boq_sync.failed_http_exception", extra=context)
        await session.rollback()
        raise
    except ValueError as exc:
        logger.exception("boq_sync.validation_failed", extra=context)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"BOQ validation failed for tab '{normalized_sheet_name}': {exc}",
        ) from exc
    except TimeoutError as exc:
        logger.exception("boq_sync.total_timeout", extra=context)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                f"Timed out while syncing BOQ for tab '{normalized_sheet_name}'. "
                "Please retry and check the server logs."
            ),
        ) from exc
    except Exception as exc:
        logger.exception("boq_sync.unexpected_failure", extra=context)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Unexpected BOQ sync failure for tab '{normalized_sheet_name}': {exc}. "
                "Check the backend logs for the failed phase."
            ),
        ) from exc

    total_elapsed_ms = round((perf_counter() - total_started_at) * 1000, 1)
    logger.info("boq_sync.completed elapsed_ms=%s", total_elapsed_ms, extra=context)
    return {
        "project_id": resolved_project_id,
        "project_name": resolved_project_name,
        "boq_type": normalized_boq_type,
        "sheet_url": sheet_url,
        "sheet_name": normalized_sheet_name,
        "status": "COMPLETED",
        "synced_at": datetime.now(timezone.utc).isoformat(),
        **persistence_result,
        "message": (
            f"BOQ synced and persisted successfully using {parse_strategy} parser."
            + (f" {validation_message}" if validation_message else "")
        ),
    }


async def sync_boq_sheet_batch(
    session: AsyncSession,
    project: Project,
    boq_type: str,
    sheet_url: str,
    sheet_names: list[str],
) -> dict[str, Any]:
    normalized_boq_type = _normalize_boq_type(boq_type)
    cleaned_sheet_names = []
    seen_sheet_names: set[str] = set()
    for sheet_name in sheet_names:
        try:
            normalized = _normalize_sheet_name(sheet_name)
        except ValueError:
            continue
        sheet_key = normalized.lower()
        if sheet_key in seen_sheet_names:
            continue
        cleaned_sheet_names.append(normalized)
        seen_sheet_names.add(sheet_key)

    if not cleaned_sheet_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one sheet tab is required for batch BOQ sync.",
        )
    if len(cleaned_sheet_names) > MAX_BATCH_SYNC_TABS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Batch BOQ sync currently supports up to {MAX_BATCH_SYNC_TABS} tabs per request "
                "to keep AI parsing responsive. Please split larger workbooks into smaller batches."
            ),
        )

    resolved_project_id, resolved_project_name = _resolve_project_identity(project=project)
    batch_context = _sync_context(
        project_id=resolved_project_id,
        project_name=resolved_project_name,
        boq_type=normalized_boq_type,
        sheet_name=None,
    )
    batch_started_at = perf_counter()
    logger.info(
        "boq_sync.batch.start requested_tabs=%s",
        len(cleaned_sheet_names),
        extra=batch_context,
    )

    results: list[dict[str, Any]] = []
    completed = 0
    failed = 0

    for sheet_name in cleaned_sheet_names:
        try:
            async with asyncio.timeout(BATCH_SYNC_PER_TAB_TIMEOUT_SECONDS):
                result = await sync_boq_sheet(
                    session=session,
                    project=None,
                    project_id=resolved_project_id,
                    project_name=resolved_project_name,
                    boq_type=normalized_boq_type,
                    sheet_url=sheet_url,
                    sheet_name=sheet_name,
                )
            results.append(
                {
                    "sheet_name": sheet_name,
                    "status": result["status"],
                    "inserted_items": result["inserted_items"],
                    "version_closed_items": result["version_closed_items"],
                    "synced_at": result["synced_at"],
                    "message": result["message"],
                }
            )
            completed += 1
        except HTTPException as exc:
            failed += 1
            results.append(
                {
                    "sheet_name": sheet_name,
                    "status": "FAILED",
                    "inserted_items": 0,
                    "version_closed_items": 0,
                    "synced_at": None,
                    "message": exc.detail,
                }
            )
        except TimeoutError:
            failed += 1
            results.append(
                {
                    "sheet_name": sheet_name,
                    "status": "FAILED",
                    "inserted_items": 0,
                    "version_closed_items": 0,
                    "synced_at": None,
                    "message": (
                        f"Timed out while syncing tab '{sheet_name}'. "
                        "Please retry with fewer tabs."
                    ),
                }
            )

    overall_status = "COMPLETED"
    if completed and failed:
        overall_status = "PARTIAL_FAILURE"
    elif failed and not completed:
        overall_status = "FAILED"

    logger.info(
        "boq_sync.batch.completed completed_tabs=%s failed_tabs=%s elapsed_ms=%s",
        completed,
        failed,
        round((perf_counter() - batch_started_at) * 1000, 1),
        extra=batch_context,
    )

    return {
        "project_id": project.id,
        "project_name": project.name,
        "boq_type": normalized_boq_type,
        "sheet_url": sheet_url,
        "status": overall_status,
        "total_requested_tabs": len(cleaned_sheet_names),
        "total_completed_tabs": completed,
        "total_failed_tabs": failed,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
