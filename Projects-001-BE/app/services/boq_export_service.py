"""Render and persist Phase 3 quotation exports from immutable snapshots."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from openpyxl import Workbook
from openpyxl.cell import Cell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.boq_v2 import (
    BOQV2ExportArtifact,
    BOQV2RevisionSnapshot,
)
from app.schemas.boq_quotation_schema import (
    BOQV2ExportArtifactResponse,
    BOQV2ExportRequest,
)
from app.services.boq_document_service import (
    _begin_command,
    _complete_command,
    _revision_context,
)
from app.services.boq_domain_service import BOQDomainError
from app.services.gcs_storage_service import (
    generate_signed_url_for_storage_key,
    upload_boq_export_artifact,
)


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME = "application/pdf"
FORMULA_PREFIXES = ("=", "+", "-", "@")
THIN_GREY = Side(style="thin", color="D9E0E7")
HEADER_FILL = PatternFill("solid", fgColor="15324A")
SUBHEADER_FILL = PatternFill("solid", fgColor="E7EEF4")
TOTAL_FILL = PatternFill("solid", fgColor="EAF2EE")


def _now() -> datetime:
    return datetime.now(UTC)


def _timestamp(value: datetime | None) -> str:
    current = value or _now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _safe_text(value: object | None) -> str:
    """Keep spreadsheet text inert when opened by office applications."""

    text = str(value or "")
    if text.lstrip().startswith(FORMULA_PREFIXES):
        return f"'{text}"
    return text


def _decimal(value: object | None) -> Decimal:
    return Decimal(str(value or "0"))


def _number(value: object | None) -> float:
    return float(_decimal(value))


def _set_text(cell: Cell, value: object | None) -> None:
    cell.value = _safe_text(value)
    cell.data_type = "s"


def _payload(snapshot: BOQV2RevisionSnapshot, audience: str) -> dict[str, Any]:
    raw = snapshot.customer_payload if audience == "CUSTOMER" else snapshot.internal_payload
    if not isinstance(raw, dict):
        raise BOQDomainError(
            "EXPORT_SNAPSHOT_INVALID", "Quotation snapshot payload is invalid"
        )
    return dict(raw)


def _included_scope(payload: dict[str, Any]) -> list[dict[str, Any]]:
    scope = payload.get("scope") or []
    return [
        dict(node)
        for node in scope
        if isinstance(node, dict) and node.get("inclusion_state") != "EXCLUDED"
    ]


def _style_worksheet(sheet: Any, *, internal: bool) -> None:
    widths = [7, 14, 38, 34, 12, 12, 16, 16, 17]
    if internal:
        widths.extend([17, 17])
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A12"
    sheet.print_title_rows = "11:11"
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape" if internal else "portrait"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.outlinePr.summaryBelow = True
    sheet.oddFooter.center.text = "Page &P of &N"


def _write_workbook(payload: dict[str, Any], *, internal: bool) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Internal BOQ" if internal else "Quotation"
    _style_worksheet(sheet, internal=internal)

    document = dict(payload.get("document") or {})
    revision = dict(payload.get("revision") or {})
    project = dict(payload.get("project") or {})
    quotation = dict(payload.get("quotation") or {})
    calculation = dict(payload.get("calculation") or {})
    max_column = 11 if internal else 9

    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_column)
    _set_text(sheet.cell(1, 1), quotation.get("title") or "ใบเสนอราคา / Quotation")
    sheet.cell(1, 1).font = Font(size=18, bold=True, color="15324A")
    sheet.cell(1, 1).alignment = Alignment(horizontal="center")

    header_rows = [
        ("เลขที่ / No.", document.get("number"), "Revision", revision.get("number")),
        ("โครงการ / Project", project.get("name"), "วันที่ / Date", quotation.get("quotation_date")),
        ("ลูกค้า / Customer", quotation.get("customer_name"), "ใช้ได้ถึง / Valid until", quotation.get("valid_until")),
        ("ที่อยู่ / Address", quotation.get("customer_address"), "เลขประจำตัวผู้เสียภาษี", quotation.get("customer_tax_id")),
        ("ผู้ติดต่อ / Contact", quotation.get("customer_contact"), "สกุลเงิน / Currency", quotation.get("currency") or "THB"),
    ]
    for row_index, values in enumerate(header_rows, start=3):
        _set_text(sheet.cell(row_index, 1), values[0])
        _set_text(sheet.cell(row_index, 2), values[1])
        _set_text(sheet.cell(row_index, 6), values[2])
        _set_text(sheet.cell(row_index, 7), values[3])
        sheet.cell(row_index, 1).font = Font(bold=True)
        sheet.cell(row_index, 6).font = Font(bold=True)
        sheet.merge_cells(start_row=row_index, start_column=2, end_row=row_index, end_column=5)
        sheet.merge_cells(start_row=row_index, start_column=7, end_row=row_index, end_column=max_column)

    columns = [
        "ลำดับ",
        "รหัส",
        "รายละเอียด",
        "ข้อกำหนด",
        "จำนวน",
        "หน่วย",
        "ค่าวัสดุ/หน่วย",
        "ค่าแรง/หน่วย",
        "รวม",
    ]
    if internal:
        columns.extend(["ต้นทุนรวม", "กำไรขั้นต้น"])
    for column_index, label in enumerate(columns, start=1):
        cell = sheet.cell(11, column_index)
        _set_text(cell, label)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(bottom=THIN_GREY)
    sheet.row_dimensions[11].height = 32

    row_index = 12
    item_number = 0
    for node in _included_scope(payload):
        kind = str(node.get("node_kind") or "")
        if kind != "ITEM":
            sheet.merge_cells(
                start_row=row_index,
                start_column=1,
                end_row=row_index,
                end_column=max_column,
            )
            _set_text(sheet.cell(row_index, 1), node.get("description") or kind.title())
            sheet.cell(row_index, 1).font = Font(bold=True, color="15324A")
            sheet.cell(row_index, 1).fill = SUBHEADER_FILL
            sheet.cell(row_index, 1).alignment = Alignment(
                indent=min(int(node.get("depth") or 0), 6), wrap_text=True
            )
            row_index += 1
            continue

        item_number += 1
        sheet.cell(row_index, 1, item_number)
        _set_text(sheet.cell(row_index, 2), node.get("item_code"))
        _set_text(sheet.cell(row_index, 3), node.get("description"))
        _set_text(sheet.cell(row_index, 4), node.get("specification"))
        sheet.cell(row_index, 5, _number(node.get("quantity")))
        _set_text(sheet.cell(row_index, 6), node.get("unit"))
        sheet.cell(row_index, 7, _number(node.get("sell_material_unit_rate")))
        sheet.cell(row_index, 8, _number(node.get("sell_labor_unit_rate")))
        sheet.cell(row_index, 9, _number(node.get("sell_total")))
        if internal:
            cost_total = sum(
                _decimal(component.get("total"))
                for component in node.get("components") or []
                if isinstance(component, dict) and component.get("total") is not None
            )
            sheet.cell(row_index, 10, float(cost_total))
            sheet.cell(
                row_index,
                11,
                float(_decimal(node.get("sell_total")) - cost_total),
            )
        for column_index in range(1, max_column + 1):
            cell = sheet.cell(row_index, column_index)
            cell.border = Border(bottom=THIN_GREY)
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=column_index in {2, 3, 4, 6},
                horizontal="right" if column_index in {5, 7, 8, 9, 10, 11} else "left",
            )
        for column_index in range(5, max_column + 1):
            sheet.cell(row_index, column_index).number_format = "#,##0.00"
        row_index += 1

    total_start = row_index + 1
    totals = [
        ("รวมก่อนส่วนลด / Subtotal", calculation.get("subtotal")),
        ("ส่วนลด / Discount", calculation.get("discount_amount")),
        ("รวมก่อน VAT / Net", calculation.get("net_sell_ex_vat")),
        (f"VAT {calculation.get('vat_rate') or '0'}%", calculation.get("vat_amount")),
        ("ยอดรวมสุทธิ / Grand total", calculation.get("grand_total")),
    ]
    for offset, (label, value) in enumerate(totals):
        current = total_start + offset
        sheet.merge_cells(
            start_row=current,
            start_column=1,
            end_row=current,
            end_column=max_column - 1,
        )
        _set_text(sheet.cell(current, 1), label)
        sheet.cell(current, 1).alignment = Alignment(horizontal="right")
        sheet.cell(current, 1).font = Font(bold=offset == len(totals) - 1)
        sheet.cell(current, max_column, _number(value))
        sheet.cell(current, max_column).number_format = '#,##0.00 "THB"'
        if offset == len(totals) - 1:
            for column_index in range(1, max_column + 1):
                sheet.cell(current, column_index).fill = TOTAL_FILL
                sheet.cell(current, column_index).font = Font(bold=True)

    row_index = total_start + len(totals) + 2
    _set_text(sheet.cell(row_index, 1), "เงื่อนไขการชำระเงิน / Payment schedule")
    sheet.cell(row_index, 1).font = Font(bold=True, color="15324A")
    row_index += 1
    for schedule in quotation.get("payment_schedule") or []:
        if not isinstance(schedule, dict):
            continue
        _set_text(sheet.cell(row_index, 1), f"• {schedule.get('label') or ''}")
        sheet.merge_cells(
            start_row=row_index,
            start_column=1,
            end_row=row_index,
            end_column=max_column - 1,
        )
        sheet.cell(row_index, max_column, _number(schedule.get("amount")))
        sheet.cell(row_index, max_column).number_format = '#,##0.00 "THB"'
        row_index += 1

    row_index += 1
    _set_text(sheet.cell(row_index, 1), "เงื่อนไขการค้า / Commercial terms")
    sheet.cell(row_index, 1).font = Font(bold=True, color="15324A")
    row_index += 1
    for term in quotation.get("commercial_terms") or []:
        _set_text(sheet.cell(row_index, 1), f"• {term}")
        sheet.merge_cells(
            start_row=row_index,
            start_column=1,
            end_row=row_index,
            end_column=max_column,
        )
        sheet.cell(row_index, 1).alignment = Alignment(wrap_text=True, vertical="top")
        row_index += 1

    sheet.auto_filter.ref = f"A11:{get_column_letter(max_column)}{max(11, total_start - 2)}"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _font_candidates() -> list[Path]:
    configured = get_settings().boq_pdf_font_path
    paths: list[Path] = []
    if configured:
        paths.append(Path(configured))
    paths.extend(
        [
            Path("/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansThai-Regular.ttf"),
            Path.home() / "Library/Fonts/NotoSansThai-Regular.ttf",
        ]
    )
    return paths


def _register_pdf_font() -> str:
    font_name = "BOQNotoSansThai"
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    font_path = next((path for path in _font_candidates() if path.is_file()), None)
    if font_path is None:
        raise BOQDomainError(
            "PDF_THAI_FONT_UNAVAILABLE",
            "Noto Sans Thai is required for quotation PDF rendering",
        )
    pdfmetrics.registerFont(TTFont(font_name, str(font_path), shapable=True))
    return font_name


def _write_pdf(payload: dict[str, Any]) -> bytes:
    font_name = _register_pdf_font()
    output = BytesIO()
    document = dict(payload.get("document") or {})
    revision = dict(payload.get("revision") or {})
    project = dict(payload.get("project") or {})
    quotation = dict(payload.get("quotation") or {})
    calculation = dict(payload.get("calculation") or {})
    doc_number = _safe_text(document.get("number"))
    revision_number = revision.get("number") or 1
    pdf = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=17 * mm,
        title=f"Quotation {doc_number} R{revision_number}",
        author="Projects-001",
    )
    base = getSampleStyleSheet()["Normal"]
    normal = ParagraphStyle(
        "BOQNormal",
        parent=base,
        fontName=font_name,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#243746"),
        wordWrap="CJK",
        shaping=True,
    )
    small = ParagraphStyle("BOQSmall", parent=normal, fontSize=7.2, leading=9.5)
    heading = ParagraphStyle(
        "BOQHeading",
        parent=normal,
        fontSize=17,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#15324A"),
    )
    right = ParagraphStyle("BOQRight", parent=normal, alignment=TA_RIGHT)

    def paragraph(value: object | None, style: ParagraphStyle = normal) -> Paragraph:
        text = _safe_text(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(text or " ", style)

    story: list[Any] = [
        paragraph(quotation.get("title") or "ใบเสนอราคา / Quotation", heading),
        Spacer(1, 5 * mm),
    ]
    identity = [
        [paragraph("เลขที่ / No."), paragraph(doc_number), paragraph("Revision"), paragraph(revision_number)],
        [paragraph("โครงการ / Project"), paragraph(project.get("name")), paragraph("วันที่ / Date"), paragraph(quotation.get("quotation_date"))],
        [paragraph("ลูกค้า / Customer"), paragraph(quotation.get("customer_name")), paragraph("ใช้ได้ถึง / Valid until"), paragraph(quotation.get("valid_until"))],
        [paragraph("ที่อยู่ / Address"), paragraph(quotation.get("customer_address")), paragraph("เลขผู้เสียภาษี / Tax ID"), paragraph(quotation.get("customer_tax_id"))],
        [paragraph("ผู้ติดต่อ / Contact"), paragraph(quotation.get("customer_contact")), paragraph("Currency"), paragraph(quotation.get("currency") or "THB")],
    ]
    identity_table = Table(identity, colWidths=[28 * mm, 67 * mm, 31 * mm, 43 * mm])
    identity_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E7EEF4")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E7EEF4")),
                ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#C5D0D8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E0E7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([identity_table, Spacer(1, 6 * mm)])

    table_data: list[list[Any]] = [
        [
            paragraph("ลำดับ", small),
            paragraph("รายละเอียด", small),
            paragraph("จำนวน", small),
            paragraph("หน่วย", small),
            paragraph("วัสดุ/หน่วย", small),
            paragraph("แรง/หน่วย", small),
            paragraph("รวม", small),
        ]
    ]
    item_number = 0
    row_kinds: list[str] = []
    for node in _included_scope(payload):
        if node.get("node_kind") != "ITEM":
            table_data.append(
                [paragraph(node.get("description") or node.get("node_kind")), "", "", "", "", "", ""]
            )
            row_kinds.append("section")
            continue
        item_number += 1
        description = node.get("description") or ""
        specification = node.get("specification")
        if specification:
            description = f"{description} — {_safe_text(specification)}"
        table_data.append(
            [
                paragraph(item_number, small),
                paragraph(description, small),
                paragraph(f"{_decimal(node.get('quantity')):,.2f}", small),
                paragraph(node.get("unit"), small),
                paragraph(f"{_decimal(node.get('sell_material_unit_rate')):,.2f}", small),
                paragraph(f"{_decimal(node.get('sell_labor_unit_rate')):,.2f}", small),
                paragraph(f"{_decimal(node.get('sell_total')):,.2f}", small),
            ]
        )
        row_kinds.append("item")
    scope_table = Table(
        table_data,
        colWidths=[12 * mm, 67 * mm, 18 * mm, 15 * mm, 20 * mm, 20 * mm, 22 * mm],
        repeatRows=1,
        splitByRow=1,
    )
    scope_commands: list[tuple[Any, ...]] = [
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#15324A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#AEBBC5")),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#D9E0E7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for offset, kind in enumerate(row_kinds, start=1):
        if kind == "section":
            scope_commands.extend(
                [
                    ("SPAN", (0, offset), (-1, offset)),
                    ("BACKGROUND", (0, offset), (-1, offset), colors.HexColor("#E7EEF4")),
                ]
            )
    scope_table.setStyle(TableStyle(scope_commands))
    story.extend([scope_table, Spacer(1, 5 * mm)])

    totals = [
        ("รวมก่อนส่วนลด / Subtotal", calculation.get("subtotal")),
        ("ส่วนลด / Discount", calculation.get("discount_amount")),
        ("รวมก่อน VAT / Net", calculation.get("net_sell_ex_vat")),
        (f"VAT {calculation.get('vat_rate') or '0'}%", calculation.get("vat_amount")),
        ("ยอดรวมสุทธิ / Grand total", calculation.get("grand_total")),
    ]
    totals_table = Table(
        [[paragraph(label, right), paragraph(f"{_decimal(value):,.2f} THB", right)] for label, value in totals],
        colWidths=[120 * mm, 49 * mm],
        hAlign="RIGHT",
    )
    totals_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("LINEABOVE", (0, -1), (-1, -1), 0.7, colors.HexColor("#15324A")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAF2EE")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.extend([totals_table, Spacer(1, 5 * mm)])
    story.append(paragraph("เงื่อนไขการชำระเงิน / Payment schedule"))
    for schedule in quotation.get("payment_schedule") or []:
        if isinstance(schedule, dict):
            story.append(
                paragraph(
                    f"• {schedule.get('label') or ''}: {_decimal(schedule.get('amount')):,.2f} THB",
                    small,
                )
            )
    story.extend([Spacer(1, 3 * mm), paragraph("เงื่อนไขการค้า / Commercial terms")])
    for term in quotation.get("commercial_terms") or []:
        story.append(paragraph(f"• {term}", small))

    def footer(canvas: Any, _document: Any) -> None:
        canvas.saveState()
        canvas.setFont(font_name, 7)
        canvas.setFillColor(colors.HexColor("#5F6F7A"))
        canvas.drawString(14 * mm, 8 * mm, f"{doc_number} · R{revision_number}")
        canvas.drawRightString(A4[0] - 14 * mm, 8 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    pdf.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


def render_export_bytes(
    snapshot: BOQV2RevisionSnapshot,
    *,
    audience: str,
    file_format: str,
) -> bytes:
    payload = _payload(snapshot, audience)
    if file_format == "XLSX":
        return _write_workbook(payload, internal=audience == "INTERNAL")
    if file_format == "PDF" and audience == "CUSTOMER":
        return _write_pdf(payload)
    raise BOQDomainError(
        "EXPORT_FORMAT_NOT_SUPPORTED",
        "Phase 3 supports customer XLSX/PDF and internal XLSX only",
    )


def _artifact_response(
    artifact: BOQV2ExportArtifact,
    *,
    download_url: str | None = None,
    expires_in_minutes: int | None = None,
) -> BOQV2ExportArtifactResponse:
    return BOQV2ExportArtifactResponse(
        artifact_id=artifact.id,
        project_id=artifact.project_id,
        document_id=artifact.document_id,
        revision_id=artifact.revision_id,
        snapshot_id=artifact.snapshot_id,
        calculation_version=artifact.calculation_version,
        audience=artifact.audience,
        file_format=artifact.file_format,
        cost_plan_version=artifact.cost_plan_version,
        status=artifact.status,
        filename=artifact.filename,
        mime_type=artifact.mime_type,
        sha256=artifact.sha256,
        size_bytes=artifact.size_bytes,
        created_at=_timestamp(artifact.created_at),
        completed_at=_timestamp(artifact.completed_at) if artifact.completed_at else None,
        download_url=download_url,
        download_expires_in_minutes=expires_in_minutes,
    )


async def request_export(
    db: AsyncSession,
    *,
    revision_id: UUID,
    request: BOQV2ExportRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2ExportArtifact:
    revision, document, _ = await _revision_context(db, revision_id)
    snapshot = (
        await db.execute(
            select(BOQV2RevisionSnapshot).where(
                BOQV2RevisionSnapshot.id == request.snapshot_id,
                BOQV2RevisionSnapshot.revision_id == revision.id,
                BOQV2RevisionSnapshot.document_id == document.id,
                BOQV2RevisionSnapshot.project_id == revision.project_id,
            )
        )
    ).scalar_one_or_none()
    if snapshot is None:
        raise BOQDomainError(
            "QUOTATION_SNAPSHOT_NOT_FOUND",
            "Quotation snapshot does not belong to this revision",
        )
    command, prior_artifact_id = await _begin_command(
        db,
        actor=actor,
        project_id=revision.project_id,
        command_type="EXPORT_QUOTATION",
        idempotency_key=idempotency_key,
        payload={
            "revision_id": str(revision.id),
            "snapshot_id": str(snapshot.id),
            "audience": request.audience,
            "file_format": request.file_format,
        },
    )
    if prior_artifact_id is not None:
        artifact = (
            await db.execute(
                select(BOQV2ExportArtifact).where(
                    BOQV2ExportArtifact.id == prior_artifact_id,
                    BOQV2ExportArtifact.revision_id == revision.id,
                )
            )
        ).scalar_one_or_none()
        if artifact is None:
            raise BOQDomainError(
                "EXPORT_ARTIFACT_NOT_FOUND",
                "Idempotent export artifact is unavailable",
            )
        return artifact

    frozen_cost = (
        snapshot.internal_payload.get("cost", {})
        if isinstance(snapshot.internal_payload, dict)
        else {}
    )
    frozen_cost_plan_version = frozen_cost.get("plan_version")
    frozen_cost_plan_id = frozen_cost.get("plan_id")
    if request.audience == "INTERNAL" and (
        (frozen_cost_plan_id is None) != (frozen_cost_plan_version is None)
    ):
        raise BOQDomainError(
            "EXPORT_COST_PLAN_MISMATCH",
            "Frozen internal snapshot has an incomplete cost plan identity",
        )
    extension = request.file_format.lower()
    suffix = "customer" if request.audience == "CUSTOMER" else "internal"
    filename = f"{document.document_number}-R{revision.revision_number}-{suffix}.{extension}"
    artifact = BOQV2ExportArtifact(
        id=uuid4(),
        project_id=revision.project_id,
        document_id=document.id,
        revision_id=revision.id,
        snapshot_id=snapshot.id,
        calculation_version=snapshot.calculation_version,
        audience=request.audience,
        file_format=request.file_format,
        cost_plan_version=(
            int(frozen_cost_plan_version)
            if request.audience == "INTERNAL" and frozen_cost_plan_version is not None
            else None
        ),
        status="PENDING",
        filename=filename,
        mime_type=XLSX_MIME if request.file_format == "XLSX" else PDF_MIME,
        created_by=actor,
    )
    db.add(artifact)
    await db.flush()
    _complete_command(command, revision_id=artifact.id, version=snapshot.source_version)
    await db.flush()
    return artifact


async def load_export_artifact(
    db: AsyncSession,
    *,
    revision_id: UUID,
    artifact_id: UUID,
    for_update: bool = False,
) -> BOQV2ExportArtifact:
    await _revision_context(db, revision_id)
    statement = select(BOQV2ExportArtifact).where(
        BOQV2ExportArtifact.id == artifact_id,
        BOQV2ExportArtifact.revision_id == revision_id,
    )
    if for_update:
        statement = statement.with_for_update()
    artifact = (await db.execute(statement)).scalar_one_or_none()
    if artifact is None:
        raise BOQDomainError(
            "EXPORT_ARTIFACT_NOT_FOUND",
            "Export artifact does not belong to this revision",
        )
    return artifact


async def render_and_upload_export(
    db: AsyncSession,
    *,
    revision_id: UUID,
    artifact_id: UUID,
) -> BOQV2ExportArtifactResponse:
    artifact = await load_export_artifact(
        db, revision_id=revision_id, artifact_id=artifact_id, for_update=True
    )
    if artifact.status == "READY" and artifact.storage_key:
        return _artifact_response(artifact)
    snapshot = (
        await db.execute(
            select(BOQV2RevisionSnapshot).where(
                BOQV2RevisionSnapshot.id == artifact.snapshot_id,
                BOQV2RevisionSnapshot.revision_id == revision_id,
            )
        )
    ).scalar_one_or_none()
    if snapshot is None:
        artifact.status = "FAILED"
        artifact.error_code = "EXPORT_SNAPSHOT_MISSING"
        await db.flush()
        raise BOQDomainError(
            "EXPORT_SNAPSHOT_MISSING", "Immutable export snapshot is unavailable"
        )
    try:
        file_bytes = render_export_bytes(
            snapshot,
            audience=artifact.audience,
            file_format=artifact.file_format,
        )
        storage_key = await upload_boq_export_artifact(
            project_id=str(artifact.project_id),
            document_id=str(artifact.document_id),
            revision_id=str(artifact.revision_id),
            snapshot_id=str(artifact.snapshot_id),
            artifact_id=str(artifact.id),
            file_name=artifact.filename,
            file_bytes=file_bytes,
            content_type=artifact.mime_type,
        )
    except BOQDomainError as error:
        artifact.status = "FAILED"
        artifact.error_code = "EXPORT_RENDER_FAILED"
        artifact.completed_at = _now()
        await db.flush()
        raise BOQDomainError(
            "EXPORT_RENDER_FAILED", "Export could not be rendered; retry safely"
        ) from error
    except Exception as error:
        artifact.status = "FAILED"
        artifact.error_code = "EXPORT_STORAGE_FAILED"
        artifact.completed_at = _now()
        await db.flush()
        raise BOQDomainError(
            "EXPORT_STORAGE_FAILED", "Export could not be stored; retry safely"
        ) from error

    artifact.status = "READY"
    artifact.storage_key = storage_key
    artifact.sha256 = hashlib.sha256(file_bytes).hexdigest()
    artifact.size_bytes = len(file_bytes)
    artifact.error_code = None
    artifact.completed_at = _now()
    await db.flush()
    return _artifact_response(artifact)


async def load_export_response(
    db: AsyncSession,
    *,
    revision_id: UUID,
    artifact_id: UUID,
) -> BOQV2ExportArtifactResponse:
    artifact = await load_export_artifact(
        db, revision_id=revision_id, artifact_id=artifact_id
    )
    return _artifact_response(artifact)


async def create_export_download(
    db: AsyncSession,
    *,
    revision_id: UUID,
    artifact_id: UUID,
    expires_in_minutes: int = 15,
) -> BOQV2ExportArtifactResponse:
    artifact = await load_export_artifact(
        db, revision_id=revision_id, artifact_id=artifact_id
    )
    if artifact.status != "READY" or not artifact.storage_key:
        raise BOQDomainError(
            "EXPORT_NOT_READY", "Export artifact is not ready for download"
        )
    url = await generate_signed_url_for_storage_key(
        storage_key=artifact.storage_key,
        expires_in_minutes=expires_in_minutes,
    )
    return _artifact_response(
        artifact,
        download_url=url,
        expires_in_minutes=expires_in_minutes,
    )
