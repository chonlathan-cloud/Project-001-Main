"""
BOQ hierarchy normalization.

This module turns parser output into a display-ready hierarchy contract before
rows are persisted. The database still stores parent_id relationships, but the
rules here keep Google Sheet row order and row semantics visible to the UI.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

ROW_TYPE_SYSTEM = "SYSTEM"
ROW_TYPE_GROUP = "GROUP"
ROW_TYPE_ITEM = "ITEM"
ROW_TYPE_TOTAL = "TOTAL"

STATUS_OK = "OK"
STATUS_INFERRED_PARENT = "INFERRED_PARENT"
STATUS_PARENT_MISSING = "PARENT_MISSING"
STATUS_RAW_LEVEL_MISMATCH = "RAW_LEVEL_MISMATCH"

SHEET_TOTAL_RE = re.compile(r"^\s*(?:total|รวม)\s*[-–—]?\s*(?P<sheet>[A-Za-zก-๙0-9 _./()-]+)?\s*$", re.IGNORECASE)
SECTION_TOTAL_RE = re.compile(r"^\s*(?:total|รวม)\s*[-–—]?\s*(?P<section>\d+(?:\.\d+)*)\s*$", re.IGNORECASE)


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _text_key(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _numeric_value(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _has_amount(item: dict[str, Any]) -> bool:
    return any(
        abs(_numeric_value(item.get(key))) > Decimal("0")
        for key in (
            "qty",
            "material_unit_price",
            "labor_unit_price",
            "total_material",
            "total_labor",
            "grand_total",
        )
    ) or bool(_clean_text(item.get("unit")))


def _combined_label(item: dict[str, Any]) -> str:
    return _clean_text(" ".join([_clean_text(item.get("item_no")), _clean_text(item.get("description"))]))


def _is_total_marker(value: Any) -> bool:
    label = _clean_text(value)
    if not label:
        return False
    normalized = label.lower()
    return (
        normalized.startswith("total")
        or normalized.startswith("รวม")
        or bool(SECTION_TOTAL_RE.match(label))
        or bool(SHEET_TOTAL_RE.match(label))
    )


def _is_total_row(item: dict[str, Any]) -> bool:
    description = _clean_text(item.get("description"))
    item_no = _clean_text(item.get("item_no"))
    if _is_total_marker(description):
        return True
    if _is_total_marker(item_no):
        return not description or _is_total_marker(description)
    return False


def _has_conflicting_total_item_no(item: dict[str, Any]) -> bool:
    return (
        _is_total_marker(item.get("item_no"))
        and bool(_clean_text(item.get("description")))
        and not _is_total_marker(item.get("description"))
    )


def _section_total_key(item: dict[str, Any]) -> str | None:
    if _has_conflicting_total_item_no(item):
        return None
    for value in (item.get("description"), item.get("item_no")):
        match = SECTION_TOTAL_RE.match(_clean_text(value))
        if match:
            return match.group("section")
    return None


def _is_sheet_total(item: dict[str, Any], sheet_name: str) -> bool:
    label = _combined_label(item)
    if not _is_total_row(item):
        return False
    section_key = _section_total_key(item)
    if section_key:
        return False
    sheet_key = _text_key(sheet_name)
    label_key = _text_key(label)
    return sheet_key and sheet_key in label_key


def _has_system_description(item: dict[str, Any]) -> bool:
    description = _clean_text(item.get("description")).lower()
    if not description:
        return False
    return (
        description.startswith("ระบบ")
        or " system" in f" {description}"
        or description.endswith("system")
    )


def _is_system_row(item: dict[str, Any]) -> bool:
    return _has_system_description(item)


def _classify_row(item: dict[str, Any]) -> str:
    if _is_total_row(item):
        return ROW_TYPE_TOTAL
    if _has_system_description(item):
        return ROW_TYPE_SYSTEM
    if _is_system_row(item):
        return ROW_TYPE_SYSTEM
    if _has_amount(item):
        return ROW_TYPE_ITEM
    return ROW_TYPE_GROUP


def _display_level(item: dict[str, Any], row_type: str, sheet_name: str) -> int:
    raw_level = int(item.get("wbs_level") or 1)
    if row_type == ROW_TYPE_TOTAL:
        return 1 if _is_sheet_total(item, sheet_name) else 2
    if row_type == ROW_TYPE_SYSTEM:
        return 1
    if row_type == ROW_TYPE_GROUP:
        return 2
    return 3


def _add_status(statuses: set[str], status: str) -> None:
    if status and status != STATUS_OK:
        statuses.add(status)


def _status_value(statuses: set[str]) -> str:
    return "|".join(sorted(statuses)) if statuses else STATUS_OK


def _source_index(source: dict[str, Any], fallback: int) -> int:
    try:
        return int(source.get("source_index", fallback))
    except (TypeError, ValueError):
        return fallback


def _item_no_root(value: Any) -> str | None:
    match = re.match(r"\s*(\d+)", str(value or "").strip())
    return match.group(1) if match else None


def _item_no_sort_parts(value: Any) -> tuple[int, ...]:
    parts = [int(part) for part in re.findall(r"\d+", str(value or ""))]
    return tuple(parts) if parts else (9999,)


def _row_affinity(item: dict[str, Any]) -> str | None:
    text = _text_key(_combined_label(item))
    if not text:
        return None
    if any(token in text for token in ("น้ำเสีย", "soilwater", "siolwater", "wastewater")):
        return "wastewater"
    if any(token in text for token in ("stopvalve", "gatevalve", "solenoidvalve", "วาล์ว", "valve", "มิเตอร์น้ำ")):
        return "valve"
    if any(token in text for token in ("น้ำดี", "coldwater", "ppr", "ประปา")):
        return "cold_water"
    return None


def _system_affinity(item: dict[str, Any]) -> str | None:
    affinity = _row_affinity(item)
    if affinity == "valve":
        return "cold_water"
    return affinity


def _group_parent_affinity(item: dict[str, Any]) -> str | None:
    affinity = _row_affinity(item)
    if affinity in {"valve", "cold_water"}:
        return "cold_water"
    return affinity


def _valid_parent_for(child: dict[str, Any], parent: dict[str, Any] | None) -> bool:
    if parent is None:
        return False
    if parent["source_index"] == child["source_index"]:
        return False
    return int(parent["display_wbs_level"]) < int(child["display_wbs_level"])


def _nearest_previous_parent(
    record: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    previous = [
        candidate
        for candidate in candidates
        if int(candidate["source_index"]) < int(record["source_index"])
    ]
    if previous:
        return max(previous, key=lambda candidate: int(candidate["source_index"]))
    return candidates[0] if candidates else None


def _display_sort_tuple(record: dict[str, Any], max_source_index: int) -> tuple[Any, ...]:
    is_sheet_total = bool(record.get("_is_sheet_total"))
    if is_sheet_total:
        return (1, max_source_index + 1, 9999, int(record["source_index"]))
    return (
        0,
        _item_no_sort_parts(record.get("item_no")),
        int(record["source_index"]),
        _clean_text(record.get("description")),
    )


def _is_zero(value: Any) -> bool:
    return abs(_numeric_value(value)) <= Decimal("0")


def _totals_tuple(item: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
    return (
        _numeric_value(item.get("total_material")),
        _numeric_value(item.get("total_labor")),
        _numeric_value(item.get("grand_total")),
    )


def _add_totals(
    left: tuple[Decimal, Decimal, Decimal],
    right: tuple[Decimal, Decimal, Decimal],
) -> tuple[Decimal, Decimal, Decimal]:
    return left[0] + right[0], left[1] + right[1], left[2] + right[2]


def _totals_match(
    left: tuple[Decimal, Decimal, Decimal],
    right: tuple[Decimal, Decimal, Decimal],
) -> bool:
    return all(abs(a - b) <= Decimal("1.00") for a, b in zip(left, right, strict=True))


def _has_nonzero_total(item: dict[str, Any]) -> bool:
    return any(abs(value) > Decimal("0") for value in _totals_tuple(item))


def _looks_like_misparsed_total(item: dict[str, Any]) -> bool:
    return (
        item["row_type"] == ROW_TYPE_ITEM
        and not _clean_text(item.get("item_no"))
        and not _clean_text(item.get("unit"))
        and _is_zero(item.get("qty"))
        and _has_nonzero_total(item)
        and not _is_total_row(item)
    )


def _set_inferred_total(
    item: dict[str, Any],
    *,
    description: str,
    display_level: int,
    sheet_total: bool,
) -> None:
    item["description"] = description
    item["row_type"] = ROW_TYPE_TOTAL
    item["display_wbs_level"] = display_level
    item["wbs_level"] = display_level
    item["_is_sheet_total"] = sheet_total
    if int(item.get("raw_wbs_level") or 1) != display_level:
        _add_status(item["_statuses"], STATUS_RAW_LEVEL_MISMATCH)


def _infer_misparsed_total_rows(records: list[dict[str, Any]], sheet_name: str) -> None:
    current_system: dict[str, Any] | None = None
    running_totals = (Decimal("0"), Decimal("0"), Decimal("0"))
    inferred_or_explicit_section_totals: list[dict[str, Any]] = []

    for record in sorted(records, key=lambda item: (int(item["source_index"]), int(item["_input_order"]))):
        if record["row_type"] == ROW_TYPE_SYSTEM:
            current_system = record
            running_totals = (Decimal("0"), Decimal("0"), Decimal("0"))
            continue

        if record["row_type"] == ROW_TYPE_TOTAL and not record.get("_is_sheet_total"):
            inferred_or_explicit_section_totals.append(record)
            running_totals = (Decimal("0"), Decimal("0"), Decimal("0"))
            continue

        if (
            current_system is not None
            and _looks_like_misparsed_total(record)
            and _totals_match(running_totals, _totals_tuple(record))
        ):
            section_key = _clean_text(current_system.get("item_no")) or str(len(inferred_or_explicit_section_totals) + 1)
            _set_inferred_total(
                record,
                description=f"TOTAL - {section_key}",
                display_level=2,
                sheet_total=False,
            )
            inferred_or_explicit_section_totals.append(record)
            running_totals = (Decimal("0"), Decimal("0"), Decimal("0"))
            continue

        if record["row_type"] == ROW_TYPE_ITEM:
            running_totals = _add_totals(running_totals, _totals_tuple(record))

    section_total_sum = (Decimal("0"), Decimal("0"), Decimal("0"))
    for total_row in inferred_or_explicit_section_totals:
        section_total_sum = _add_totals(section_total_sum, _totals_tuple(total_row))

    if not _has_nonzero_total({"total_material": section_total_sum[0], "total_labor": section_total_sum[1], "grand_total": section_total_sum[2]}):
        return

    for record in sorted(records, key=lambda item: (int(item["source_index"]), int(item["_input_order"]))):
        if record["row_type"] == ROW_TYPE_SYSTEM:
            break
        if _looks_like_misparsed_total(record) and _totals_match(_totals_tuple(record), section_total_sum):
            _set_inferred_total(
                record,
                description=f"TOTAL - {sheet_name}",
                display_level=1,
                sheet_total=True,
            )
            break


def normalize_boq_hierarchy(
    items: list[dict[str, Any]],
    *,
    sheet_name: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for input_order, source in enumerate(items):
        source = dict(source)
        has_conflicting_total_item_no = _has_conflicting_total_item_no(source)
        if has_conflicting_total_item_no:
            source["item_no"] = None
        source_index = _source_index(source, input_order)
        raw_level = int(source.get("wbs_level") or 1)
        row_type = _classify_row(source)
        display_level = _display_level(source, row_type, sheet_name)
        statuses: set[str] = set()
        if raw_level != display_level:
            _add_status(statuses, STATUS_RAW_LEVEL_MISMATCH)
        if has_conflicting_total_item_no:
            _add_status(statuses, STATUS_RAW_LEVEL_MISMATCH)
        records.append({
            **source,
            "source_index": source_index,
            "source_row_index": source_index,
            "_input_order": input_order,
            "_statuses": statuses,
            "_is_sheet_total": row_type == ROW_TYPE_TOTAL and _is_sheet_total(source, sheet_name),
            "raw_wbs_level": raw_level,
            "display_wbs_level": display_level,
            "wbs_level": display_level,
            "row_type": row_type,
            "parent_source_index": None,
        })

    _infer_misparsed_total_rows(records, sheet_name)

    by_source_index = {int(record["source_index"]): record for record in records}
    system_records = [record for record in records if record["row_type"] == ROW_TYPE_SYSTEM]
    group_records = [record for record in records if record["row_type"] == ROW_TYPE_GROUP]
    systems_by_item_no: dict[str, dict[str, Any]] = {}
    systems_by_affinity: dict[str, dict[str, Any]] = {}
    groups_by_affinity: dict[str, list[dict[str, Any]]] = {}

    for system in system_records:
        item_no = _clean_text(system.get("item_no"))
        if item_no:
            systems_by_item_no[item_no] = system
        affinity = _system_affinity(system)
        if affinity:
            systems_by_affinity[affinity] = system

    for group in group_records:
        affinity = _row_affinity(group)
        if affinity:
            groups_by_affinity.setdefault(affinity, []).append(group)

    latest_by_level: dict[int, dict[str, Any]] = {}
    for record in sorted(records, key=lambda item: (int(item["source_index"]), int(item["_input_order"]))):
        statuses: set[str] = record["_statuses"]
        row_type = record["row_type"]
        parent_source_index: int | None = None

        parsed_parent = by_source_index.get(_source_index({"source_index": record.get("parent_index")}, -1))
        if _valid_parent_for(record, parsed_parent):
            parent_source_index = int(parsed_parent["source_index"])
        elif row_type == ROW_TYPE_TOTAL and record["_is_sheet_total"]:
            parent_source_index = None
        elif row_type == ROW_TYPE_TOTAL:
            section_parent = systems_by_item_no.get(_section_total_key(record) or "")
            if _valid_parent_for(record, section_parent):
                parent_source_index = int(section_parent["source_index"])
                _add_status(statuses, STATUS_INFERRED_PARENT)
            else:
                fallback_parent = _nearest_previous_parent(
                    record,
                    [candidate for candidate in system_records if _valid_parent_for(record, candidate)],
                )
                if fallback_parent:
                    parent_source_index = int(fallback_parent["source_index"])
                _add_status(statuses, STATUS_PARENT_MISSING)
        elif row_type == ROW_TYPE_SYSTEM:
            parent_source_index = None
        elif row_type == ROW_TYPE_GROUP:
            parent = systems_by_affinity.get(_group_parent_affinity(record) or "")
            if parent is None:
                root_item_no = _item_no_root(record.get("item_no"))
                parent = systems_by_item_no.get(root_item_no or "")
            if parent is None:
                parent = _nearest_previous_parent(
                    record,
                    [candidate for candidate in system_records if _valid_parent_for(record, candidate)],
                )
            if _valid_parent_for(record, parent):
                parent_source_index = int(parent["source_index"])
                _add_status(statuses, STATUS_INFERRED_PARENT)
            else:
                _add_status(statuses, STATUS_PARENT_MISSING)
        else:
            affinity = _row_affinity(record)
            group_candidates = groups_by_affinity.get(affinity or "", [])
            parent = _nearest_previous_parent(
                record,
                [candidate for candidate in group_candidates if _valid_parent_for(record, candidate)],
            )
            if parent is None:
                parent = latest_by_level.get(int(record["display_wbs_level"]) - 1)
            if _valid_parent_for(record, parent):
                parent_source_index = int(parent["source_index"])
                _add_status(statuses, STATUS_INFERRED_PARENT)
            else:
                _add_status(statuses, STATUS_PARENT_MISSING)

        record["parent_source_index"] = parent_source_index
        if row_type != ROW_TYPE_TOTAL:
            latest_by_level[int(record["display_wbs_level"])] = record
            for level in list(latest_by_level):
                if level > int(record["display_wbs_level"]):
                    latest_by_level.pop(level, None)

    max_source_index = max((int(record["source_index"]) for record in records), default=0)
    sorted_for_display = sorted(records, key=lambda item: _display_sort_tuple(item, max_source_index))
    sort_order_by_source_index = {
        int(record["source_index"]): sort_order
        for sort_order, record in enumerate(sorted_for_display)
    }

    normalized: list[dict[str, Any]] = []
    for record in records:
        cleaned = {
            key: value
            for key, value in record.items()
            if not key.startswith("_")
        }
        cleaned["sort_order"] = sort_order_by_source_index[int(record["source_index"])]
        cleaned["hierarchy_status"] = _status_value(record["_statuses"])
        normalized.append(cleaned)

    return normalized
