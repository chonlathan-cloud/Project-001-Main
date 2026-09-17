from __future__ import annotations

import subprocess
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from app.services.boq_domain_service import BOQDomainError
from app.services.boq_export_service import render_export_bytes


def _snapshot(*, rows: int = 3) -> SimpleNamespace:
    scope = [
        {
            "id": str(index),
            "logical_id": str(index),
            "parent_logical_id": None,
            "node_kind": "ITEM",
            "inclusion_state": "REQUIRED",
            "position": index,
            "depth": 0,
            "item_code": f"=HYPERLINK(\"https://invalid/{index}\")",
            "description": f"งานก่อสร้างภาษาไทยลำดับที่ {index + 1}",
            "specification": "ข้อกำหนดและรายละเอียดวัสดุภาษาไทย",
            "quantity": "2.0000",
            "unit": "งาน",
            "sell_material_unit_rate": "100.0000",
            "sell_labor_unit_rate": "50.0000",
            "sell_total": "300.00",
            "components": [
                {"component_type": "MATERIAL", "total": "180.00"},
                {"component_type": "LABOR", "total": "80.00"},
            ],
        }
        for index in range(rows)
    ]
    common = {
        "document": {"number": "QT-2026-000001"},
        "revision": {"number": 3},
        "project": {"name": "โครงการทดสอบ"},
        "quotation": {
            "title": "ใบเสนอราคา",
            "customer_name": "บริษัท ลูกค้าทดสอบ จำกัด",
            "customer_address": "กรุงเทพมหานคร",
            "customer_tax_id": "0105559999999",
            "customer_contact": "คุณทดสอบ",
            "quotation_date": "2026-09-17",
            "valid_until": "2026-10-17",
            "currency": "THB",
            "payment_schedule": [
                {"label": "มัดจำ", "amount": "321.00"},
                {"label": "ส่งมอบ", "amount": "321.00"},
            ],
            "commercial_terms": ["ราคานี้รวมภาษีมูลค่าเพิ่มตามที่ระบุ"],
        },
        "calculation": {
            "subtotal": "600.00",
            "discount_amount": "0.00",
            "net_sell_ex_vat": "600.00",
            "vat_rate": "7.0000",
            "vat_amount": "42.00",
            "grand_total": "642.00",
        },
        "scope": scope,
    }
    return SimpleNamespace(
        customer_payload=common,
        internal_payload={
            **common,
            "cost": {
                "forecast_cost": "520.00",
                "forecast_margin": "80.00",
                "secret_internal_note": "never-customer",
            },
        },
    )


def test_customer_xlsx_is_real_numeric_thai_safe_and_confidential() -> None:
    artifact = render_export_bytes(
        _snapshot(), audience="CUSTOMER", file_format="XLSX"
    )
    assert artifact.startswith(b"PK")
    workbook = load_workbook(BytesIO(artifact), data_only=False)
    sheet = workbook["Quotation"]
    assert sheet["B12"].value.startswith("'=")
    assert sheet["E12"].data_type == "n"
    assert sheet["I12"].data_type == "n"
    assert "งานก่อสร้างภาษาไทย" in sheet["C12"].value
    assert str(sheet.page_setup.paperSize) == str(sheet.PAPERSIZE_A4)
    assert sheet.print_title_rows == "$11:$11"
    serialized = " ".join(
        str(cell.value or "") for row in sheet.iter_rows() for cell in row
    )
    assert "never-customer" not in serialized
    assert "forecast_margin" not in serialized
    assert "ต้นทุนรวม" not in serialized


def test_internal_xlsx_has_frozen_cost_and_pdf_is_a4_multipage(
    tmp_path,
) -> None:
    snapshot = _snapshot(rows=120)

    internal = render_export_bytes(
        snapshot, audience="INTERNAL", file_format="XLSX"
    )
    internal_sheet = load_workbook(BytesIO(internal), data_only=False)["Internal BOQ"]
    assert internal_sheet["J11"].value == "ต้นทุนรวม"
    assert internal_sheet["J12"].data_type == "n"
    assert internal_sheet["J12"].value == 260
    assert internal_sheet["K12"].value == 40

    with pytest.raises(BOQDomainError):
        render_export_bytes(snapshot, audience="INTERNAL", file_format="PDF")

    customer_pdf = render_export_bytes(
        snapshot, audience="CUSTOMER", file_format="PDF"
    )
    assert customer_pdf.startswith(b"%PDF-")
    pdf_path = tmp_path / "quotation.pdf"
    pdf_path.write_bytes(customer_pdf)
    result = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = result.stdout
    pages_line = next(line for line in metadata.splitlines() if line.startswith("Pages:"))
    assert int(pages_line.split(":", 1)[1].strip()) >= 3
    assert "A4" in metadata
    extracted = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "QT-2026-000001" in extracted
    assert "R3" in extracted
    assert "ใบเสนอราคา" in extracted
    render_prefix = tmp_path / "quotation-page"
    subprocess.run(
        [
            "pdftoppm",
            "-f",
            "1",
            "-singlefile",
            "-png",
            str(pdf_path),
            str(render_prefix),
        ],
        check=True,
        capture_output=True,
    )
    assert render_prefix.with_suffix(".png").stat().st_size > 10_000
