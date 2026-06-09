"""Validate SN BOQ hierarchy normalization against the Phase 1 contract.

Run from the repository root:
    python3 Projects-001-BE/scripts/validate_sn_boq_hierarchy.py
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
CONTRACT_PATH = REPO_ROOT / "Design" / "S-BOQ" / "sn-customer-hierarchy.contract.json"
SOURCE_SAMPLE_PATH = REPO_ROOT / "Design" / "S-BOQ" / "S-BOQ.json"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.boq_hierarchy import normalize_boq_hierarchy  # noqa: E402


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))


def _raw_level_for_contract_node(node: dict[str, Any]) -> int:
    row_type = str(node.get("row_type") or "").upper()
    if row_type == "SYSTEM":
        return 3
    if row_type == "GROUP":
        return 1
    if row_type == "ITEM":
        return 2
    return int(node.get("display_wbs_level") or 1)


def _contract_rows(
    nodes: list[dict[str, Any]],
    *,
    rows: list[dict[str, Any]],
    parent_index: int | None = None,
) -> None:
    for node in nodes:
        source_index = len(rows) + 1
        row_type = str(node.get("row_type") or "").upper()
        is_budget_source = row_type in {"ITEM", "TOTAL"}
        material_total = _decimal(node.get("material_total")) if is_budget_source else Decimal("0")
        labor_total = _decimal(node.get("labor_total")) if is_budget_source else Decimal("0")
        grand_total = _decimal(node.get("grand_total")) if is_budget_source else Decimal("0")

        rows.append(
            {
                "source_index": source_index,
                "parent_index": parent_index,
                "wbs_level": _raw_level_for_contract_node(node),
                "item_no": node.get("item_no") or None,
                "description": node.get("description") or "",
                "qty": _decimal(node.get("qty")),
                "unit": node.get("unit") or None,
                "material_unit_price": Decimal("0"),
                "labor_unit_price": Decimal("0"),
                "total_material": material_total,
                "total_labor": labor_total,
                "grand_total": grand_total,
            }
        )
        _contract_rows(node.get("children") or [], rows=rows, parent_index=source_index)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _tree_from_normalized(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    children_by_parent: dict[int | None, list[dict[str, Any]]] = {}
    for item in items:
        children_by_parent.setdefault(item.get("parent_source_index"), []).append(item)

    def build(parent_source_index: int | None) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for item in sorted(
            children_by_parent.get(parent_source_index, []),
            key=lambda row: int(row.get("sort_order") or 0),
        ):
            nodes.append(
                {
                    "description": _normalize_text(item.get("description")),
                    "row_type": item.get("row_type"),
                    "display_wbs_level": item.get("display_wbs_level"),
                    "children": build(int(item["source_index"])),
                }
            )
        return nodes

    return build(None)


def _expected_tree(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "description": _normalize_text(node.get("description")),
            "row_type": node.get("row_type"),
            "display_wbs_level": node.get("display_wbs_level"),
            "children": _expected_tree(node.get("children") or []),
        }
        for node in nodes
    ]


def _assert_tree_matches(actual: list[dict[str, Any]], expected: list[dict[str, Any]], path: str = "root") -> None:
    assert len(actual) == len(expected), f"{path}: expected {len(expected)} nodes, got {len(actual)}"
    for index, (actual_node, expected_node) in enumerate(zip(actual, expected, strict=True)):
        node_path = f"{path}.{index}:{expected_node['description']}"
        for key in ("description", "row_type", "display_wbs_level"):
            assert actual_node[key] == expected_node[key], (
                f"{node_path}: expected {key}={expected_node[key]!r}, got {actual_node[key]!r}"
            )
        _assert_tree_matches(actual_node["children"], expected_node["children"], node_path)


def _assert_summary(items: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for item in items:
        counts[item["row_type"]] = counts.get(item["row_type"], 0) + 1

    assert counts == {
        "SYSTEM": 2,
        "GROUP": 3,
        "ITEM": 11,
        "TOTAL": 3,
    }, f"Unexpected row type counts: {counts}"

    sheet_total = next(item for item in items if item["description"] == "TOTAL - SN")
    assert sheet_total["display_wbs_level"] == 1
    assert sheet_total["parent_source_index"] is None


def _sample_rows_from_s_boq() -> list[dict[str, Any]]:
    source_rows = json.loads(SOURCE_SAMPLE_PATH.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(source_rows):
        if row.get("boq_type") != "CUSTOMER" or row.get("sheet_name") != "SN":
            continue
        rows.append(
            {
                "source_index": index,
                "parent_index": None,
                "wbs_level": int(row.get("wbs_level") or 1),
                "item_no": row.get("item_no") or None,
                "description": row.get("description") or "",
                "qty": Decimal("0"),
                "unit": None,
                "material_unit_price": Decimal("0"),
                "labor_unit_price": Decimal("0"),
                "total_material": Decimal("0"),
                "total_labor": Decimal("0"),
                "grand_total": _decimal(row.get("grand_total")),
            }
        )
    return rows


def _assert_sample_anomaly_regression() -> None:
    normalized = normalize_boq_hierarchy(_sample_rows_from_s_boq(), sheet_name="SN")
    by_description = {
        _normalize_text(item["description"]): item
        for item in normalized
    }
    by_source_index = {
        int(item["source_index"]): item
        for item in normalized
    }

    expected_parent_descriptions = {
        "วาล์ว (VALVE) ทองเหลือง": "ระบบน้ำดี (COLD WATER)",
        "ท่อประปา PPR (PN 20)": "ระบบน้ำดี (COLD WATER)",
        "ท่อน้ำเสีย PVC CLASS 13.5": "ระบบน้ำเสีย (SIOL WATER)",
    }
    for child_description, parent_description in expected_parent_descriptions.items():
        child = by_description[child_description]
        parent = by_source_index.get(int(child["parent_source_index"]))
        assert parent is not None, f"{child_description}: expected parent {parent_description}, got none"
        assert _normalize_text(parent["description"]) == parent_description, (
            f"{child_description}: expected parent {parent_description}, "
            f"got {_normalize_text(parent['description'])}"
        )


def _assert_latest_sync_shape_regression() -> None:
    rows = [
        {
            "source_index": 8,
            "parent_index": None,
            "wbs_level": 1,
            "item_no": None,
            "description": "HANGER & SUPPORT",
            "qty": Decimal("0"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("7450"),
            "total_labor": Decimal("2650"),
            "grand_total": Decimal("10100"),
        },
        {
            "source_index": 9,
            "parent_index": None,
            "wbs_level": 1,
            "item_no": "1",
            "description": "ระบบน้ำเสีย (SIOL WATER)",
            "qty": Decimal("0"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("0"),
            "total_labor": Decimal("0"),
            "grand_total": Decimal("0"),
        },
        {
            "source_index": 10,
            "parent_index": None,
            "wbs_level": 1,
            "item_no": "2",
            "description": "ท่อน้ำเสีย PVC CLASS 13.5",
            "qty": Decimal("0"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("0"),
            "total_labor": Decimal("0"),
            "grand_total": Decimal("0"),
        },
        {
            "source_index": 11,
            "parent_index": 10,
            "wbs_level": 2,
            "item_no": None,
            "description": "ขนาด Æ 2\"",
            "qty": Decimal("1"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("120"),
            "total_labor": Decimal("80"),
            "grand_total": Decimal("200"),
        },
        {
            "source_index": 12,
            "parent_index": 10,
            "wbs_level": 2,
            "item_no": None,
            "description": "ACCESSORIES & FITTING",
            "qty": Decimal("1"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("1000"),
            "total_labor": Decimal("0"),
            "grand_total": Decimal("1000"),
        },
        {
            "source_index": 13,
            "parent_index": 10,
            "wbs_level": 2,
            "item_no": None,
            "description": "HANGER & SUPPORT",
            "qty": Decimal("1"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("1000"),
            "total_labor": Decimal("0"),
            "grand_total": Decimal("1000"),
        },
        {
            "source_index": 14,
            "parent_index": None,
            "wbs_level": 2,
            "item_no": None,
            "description": "HANGER & SUPPORT",
            "qty": Decimal("0"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("2120"),
            "total_labor": Decimal("80"),
            "grand_total": Decimal("2200"),
        },
        {
            "source_index": 15,
            "parent_index": None,
            "wbs_level": 1,
            "item_no": "2",
            "description": "ระบบน้ำดี (COLD WATER)",
            "qty": Decimal("0"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("0"),
            "total_labor": Decimal("0"),
            "grand_total": Decimal("0"),
        },
        {
            "source_index": 20,
            "parent_index": None,
            "wbs_level": 1,
            "item_no": None,
            "description": "วาล์ว (VALVE) ทองเหลือง",
            "qty": Decimal("0"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("0"),
            "total_labor": Decimal("0"),
            "grand_total": Decimal("0"),
        },
        {
            "source_index": 21,
            "parent_index": None,
            "wbs_level": 2,
            "item_no": "TOTAL - 2",
            "description": "STOP VALVE Æ 1/2\"",
            "qty": Decimal("1"),
            "unit": "SET",
            "material_unit_price": Decimal("150"),
            "labor_unit_price": Decimal("150"),
            "total_material": Decimal("150"),
            "total_labor": Decimal("150"),
            "grand_total": Decimal("300"),
        },
        {
            "source_index": 26,
            "parent_index": None,
            "wbs_level": 2,
            "item_no": None,
            "description": "TOTAL - 2",
            "qty": Decimal("0"),
            "unit": None,
            "material_unit_price": Decimal("0"),
            "labor_unit_price": Decimal("0"),
            "total_material": Decimal("5330"),
            "total_labor": Decimal("2570"),
            "grand_total": Decimal("7900"),
        },
    ]
    normalized = normalize_boq_hierarchy(rows, sheet_name="SN")
    by_description = {
        _normalize_text(item["description"]): item
        for item in normalized
    }
    by_source_index = {
        int(item["source_index"]): item
        for item in normalized
    }

    sheet_total = by_description["TOTAL - SN"]
    assert sheet_total["row_type"] == "TOTAL"
    assert sheet_total["display_wbs_level"] == 1
    assert sheet_total["parent_source_index"] is None

    section_total = by_description["TOTAL - 1"]
    assert section_total["row_type"] == "TOTAL"
    assert _normalize_text(by_source_index[section_total["parent_source_index"]]["description"]) == "ระบบน้ำเสีย (SIOL WATER)"

    wastewater_group = by_description["ท่อน้ำเสีย PVC CLASS 13.5"]
    assert wastewater_group["row_type"] == "GROUP"
    assert wastewater_group["display_wbs_level"] == 2
    assert _normalize_text(by_source_index[wastewater_group["parent_source_index"]]["description"]) == "ระบบน้ำเสีย (SIOL WATER)"

    valve_group = by_description["วาล์ว (VALVE) ทองเหลือง"]
    assert valve_group["row_type"] == "GROUP"
    assert valve_group["display_wbs_level"] == 2
    assert _normalize_text(by_source_index[valve_group["parent_source_index"]]["description"]) == "ระบบน้ำดี (COLD WATER)"

    stop_valve = by_description["STOP VALVE Æ 1/2\""]
    assert stop_valve["row_type"] == "ITEM"
    assert stop_valve["display_wbs_level"] == 3
    assert not stop_valve["item_no"]
    assert _normalize_text(by_source_index[stop_valve["parent_source_index"]]["description"]) == "วาล์ว (VALVE) ทองเหลือง"


def main() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    _contract_rows(contract["expected_tree"], rows=rows)

    normalized = normalize_boq_hierarchy(
        rows,
        sheet_name=contract["scope"]["sheet_name"],
    )
    _assert_summary(normalized)
    _assert_tree_matches(
        _tree_from_normalized(normalized),
        _expected_tree(contract["expected_tree"]),
    )
    _assert_sample_anomaly_regression()
    _assert_latest_sync_shape_regression()

    print("SN BOQ hierarchy contract passed.")


if __name__ == "__main__":
    main()
