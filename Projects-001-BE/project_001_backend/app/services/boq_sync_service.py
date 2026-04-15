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
import os
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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
MAX_BATCH_SYNC_TABS = int(os.getenv("BOQ_BATCH_SYNC_MAX_TABS", "3"))
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


def _sync_context(
    project: Project | None = None,
    boq_type: str | None = None,
    sheet_name: str | None = None,
) -> dict[str, Any]:
    return {
        "project_id": str(project.id) if project else None,
        "project_name": project.name if project else None,
        "boq_type": boq_type,
        "sheet_name": sheet_name,
    }


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
            raise ValueError(f"wbs_level must be >= 1 at parsed row {source_index}.")

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
    normalized_items = _normalize_parsed_items(parsed_items)

    result = await session.execute(
        select(BOQItem)
        .filter_by(project_id=project_id, boq_type=boq_type, sheet_name=sheet_name)
        .filter(BOQItem.valid_to.is_(None))
    )
    current_items = result.scalars().all()
    for item in current_items:
        item.valid_to = now

    source_index_to_row: dict[int, BOQItem] = {}
    inserted_rows: list[BOQItem] = []

    for item in normalized_items:
        row = BOQItem(
            project_id=project_id,
            boq_type=boq_type,
            sheet_name=sheet_name,
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
        "version_closed_items": len(current_items),
    }


async def sync_boq_sheet(
    session: AsyncSession,
    project: Project,
    boq_type: str,
    sheet_url: str,
    sheet_name: str,
) -> dict[str, Any]:
    context = _sync_context(project=project, boq_type=boq_type, sheet_name=sheet_name)
    logger.info("boq_sync.start", extra=context)
    total_started_at = perf_counter()

    try:
        async with asyncio.timeout(TOTAL_SYNC_TIMEOUT_SECONDS):
            logger.info("boq_sync.fetch_sheet.start", extra=context)
            fetch_started_at = perf_counter()
            try:
                async with asyncio.timeout(SHEET_FETCH_TIMEOUT_SECONDS + ADC_REFRESH_TIMEOUT_SECONDS):
                    raw_rows = await fetch_google_sheet_rows(
                        sheet_url=sheet_url,
                        sheet_name=sheet_name,
                    )
            except TimeoutError as exc:
                logger.exception("boq_sync.fetch_sheet.timeout", extra=context)
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Timed out while fetching sheet tab '{sheet_name}'.",
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
                    detail=f"Sheet tab '{sheet_name}' does not contain any usable BOQ rows after preprocessing.",
                )

            logger.info("boq_sync.gemini_parse.start", extra=context)
            parse_started_at = perf_counter()
            try:
                async with asyncio.timeout(GEMINI_PARSE_TIMEOUT_SECONDS):
                    parsed_items = await parse_boq_sheet_with_gemini(
                        sheet_name=sheet_name,
                        raw_data=prepared_rows,
                    )
            except TimeoutError as exc:
                logger.exception("boq_sync.gemini_parse.timeout", extra=context)
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=(
                        f"Timed out while parsing sheet tab '{sheet_name}' with Gemini. "
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
                        project_id=project.id,
                        boq_type=boq_type,
                        sheet_name=sheet_name,
                        parsed_items=parsed_items,
                    )
            except TimeoutError as exc:
                logger.exception("boq_sync.persist.timeout", extra=context)
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=(
                        f"Timed out while saving BOQ rows for tab '{sheet_name}'. "
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
            detail=f"BOQ validation failed for tab '{sheet_name}': {exc}",
        ) from exc
    except TimeoutError as exc:
        logger.exception("boq_sync.total_timeout", extra=context)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                f"Timed out while syncing BOQ for tab '{sheet_name}'. "
                "Please retry and check the server logs."
            ),
        ) from exc
    except Exception as exc:
        logger.exception("boq_sync.unexpected_failure", extra=context)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Unexpected BOQ sync failure for tab '{sheet_name}': {exc}. "
                "Check the backend logs for the failed phase."
            ),
        ) from exc

    total_elapsed_ms = round((perf_counter() - total_started_at) * 1000, 1)
    logger.info("boq_sync.completed elapsed_ms=%s", total_elapsed_ms, extra=context)
    return {
        "project_id": project.id,
        "project_name": project.name,
        "boq_type": boq_type,
        "sheet_url": sheet_url,
        "sheet_name": sheet_name,
        "status": "COMPLETED",
        "synced_at": datetime.now(timezone.utc).isoformat(),
        **persistence_result,
        "message": "BOQ synced and persisted successfully.",
    }


async def sync_boq_sheet_batch(
    session: AsyncSession,
    project: Project,
    boq_type: str,
    sheet_url: str,
    sheet_names: list[str],
) -> dict[str, Any]:
    cleaned_sheet_names = []
    seen_sheet_names: set[str] = set()
    for sheet_name in sheet_names:
        normalized = str(sheet_name or "").strip()
        if not normalized:
            continue
        if normalized in seen_sheet_names:
            continue
        cleaned_sheet_names.append(normalized)
        seen_sheet_names.add(normalized)

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

    batch_context = _sync_context(project=project, boq_type=boq_type, sheet_name=None)
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
                    project=project,
                    boq_type=boq_type,
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
        "boq_type": boq_type,
        "sheet_url": sheet_url,
        "status": overall_status,
        "total_requested_tabs": len(cleaned_sheet_names),
        "total_completed_tabs": completed,
        "total_failed_tabs": failed,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
