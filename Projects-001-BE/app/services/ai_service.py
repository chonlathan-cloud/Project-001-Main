"""
AI Service — Gemini Integration via google-genai on Vertex AI.

Implements:
  - BOQ Sheet parsing via Gemini  (LLD §3.1, BRD §4.1)
  - Receipt OCR extraction via Gemini
  - Vector embedding generation   (BRD §5.1)
  - Strategic RAG chat             (LLD §3.2)

Uses google-genai SDK in Vertex AI mode.
"""

import json
import logging
import os
from datetime import datetime
from time import perf_counter

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GenAI Initialisation
# ---------------------------------------------------------------------------
_GCP_PROJECT = os.getenv("GCP_PROJECT_ID")
_GCP_LOCATION = os.getenv("GCP_LOCATION", "asia-southeast1")
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

_client: genai.Client | None = None


def _normalize_receipt_date(value: object) -> str | None:
    cleaned = str(value or "").strip()
    if not cleaned:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue

    if "T" in cleaned:
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return None

    return None


def _to_receipt_number(value: object) -> float:
    if value in (None, ""):
        return 0.0
    try:
        cleaned = str(value).replace(",", "").strip()
        return round(float(cleaned or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _to_receipt_bool(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    cleaned = str(value).strip().lower()
    if cleaned in {"true", "1", "yes", "y", "complete", "completed"}:
        return True
    if cleaned in {"false", "0", "no", "n", "partial", "incomplete"}:
        return False
    return default


def _normalize_receipt_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    for item in value:
        cleaned = str(item or "").strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _clean_receipt_text(value: object) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _normalize_vendor_tax_id(value: object) -> str | None:
    cleaned = "".join(character for character in str(value or "") if character.isdigit())
    return cleaned or None


def _normalize_accounting_vat_mode(value: object) -> str | None:
    cleaned = str(value or "").strip().lower()
    if cleaned in {"no_vat", "vat_inclusive", "vat_exclusive"}:
        return cleaned
    return None


def _get_client() -> genai.Client:
    """Lazy-initialise the GenAI client (once per cold start)."""
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=_GCP_PROJECT,
            location=_GCP_LOCATION,
        )
    return _client


RECEIPT_OCR_PROMPT = """\
You are an OCR and invoice understanding assistant for construction finance workflows.
Read the uploaded receipt, invoice, tax invoice, bank bill image, or PDF and extract only the
fields requested below.

The uploaded document may be in Thai, English, or mixed Thai-English.

Return data for the following JSON object:
- suggested_entry_type: "EXPENSE" or "INCOME"
- vendor_name: merchant, vendor, company, store, or payee/payer name if visible
- vendor_tax_id: Thai supplier tax ID if visible, digits only, otherwise null
- vendor_branch: supplier branch if visible such as "สำนักงานใหญ่" or branch code, otherwise null
- vendor_address: supplier address if visible, otherwise null
- receipt_no: receipt number, invoice number, tax invoice number, document number, or reference number
- document_date: document date in YYYY-MM-DD if a reliable date is visible, otherwise null
- suggested_request_type: one of ["ค่าวัสดุ", "ค่าแรง", "ค่าเบิกล่วงหน้า", "ค่าใช้จ่ายทั่วไป"] or null
- suggested_accounting_vat_mode: one of ["no_vat", "vat_inclusive", "vat_exclusive"] or null
- total_amount: final payable/received amount as number if visible, otherwise 0
- subtotal_amount: subtotal before VAT if visible, otherwise 0
- vat_amount: VAT amount if visible, otherwise 0
- vat_rate: VAT percent if visible, otherwise 0
- line_items_complete: true only when every visible product/service/discount line from every page was extracted
- page_count: number of pages/sheets visible in the uploaded document if known, otherwise 0
- items: all visible line items from every page with description, qty, price, amount
- warnings: short Thai warnings for anything the user should verify before submit
- low_confidence_fields: list of field names that are visible but uncertain. Use only these names:
  ["suggested_entry_type", "vendor_name", "vendor_tax_id", "vendor_branch", "vendor_address", "receipt_no", "document_date", "suggested_request_type", "suggested_accounting_vat_mode", "total_amount", "subtotal_amount", "vat_amount", "vat_rate", "items", "line_items_complete"]
- message: short Thai message summarising whether the extraction is complete or partial

Rules:
- Prefer accuracy over guessing. If a field is unclear, return null.
- For suggested_request_type:
  - construction materials / hardware / store purchases => "ค่าวัสดุ"
  - labor / wages / manpower / subcontract labor => "ค่าแรง"
  - deposit / advance / prepayment / mobilization => "ค่าเบิกล่วงหน้า"
  - utilities / transport / food / admin / other overhead => "ค่าใช้จ่ายทั่วไป"
- If the document looks like a purchase or expense receipt, set suggested_entry_type to "EXPENSE".
- If it clearly shows money received by the user/company, set suggested_entry_type to "INCOME".
- total_amount must be the final payable/paid/received amount, not the sum of a partial item list.
- For Thai tax invoices, separate VAT into vat_amount/vat_rate. Keep total_amount as the final gross payable amount.
- For Thai tax invoices/receipts, extract supplier tax ID, branch, and address from the seller/merchant header.
- Do not use buyer/customer tax details for vendor_tax_id/vendor_branch/vendor_address.
- If the document says VAT included or prices include VAT, set suggested_accounting_vat_mode="vat_inclusive".
- If VAT is added on top of a pre-VAT subtotal, set suggested_accounting_vat_mode="vat_exclusive".
- If VAT is absent, exempt, or not shown, set suggested_accounting_vat_mode="no_vat".
- For Makro, Thai Watsadu, HomePro, and construction-material store receipts, extract every item row across all pages/sheets.
- For bank transfer slips, items may be empty; use total_amount for the transfer amount and receipt_no for the reference if visible.
- Numeric fields must use numbers only, with no currency symbols.
- items[].qty, items[].price, and items[].amount must be numeric when available; otherwise use 0.
- If a line total is visible, set items[].amount to that line total. If only qty and unit price are visible, set amount = qty * price.
- Include visible discount or surcharge rows as items with qty 1 and negative/positive amount when they affect the payable amount.
- Do not include VAT summary rows as items unless they are presented as ordinary charge rows. Use vat_amount for VAT summary.
- If you cannot confidently extract all lines from a long receipt, return every line you can read, set line_items_complete=false, and add a warning.
- If a field is missing entirely, keep it null/0 and do not include it in low_confidence_fields.
- Return only valid JSON. No markdown.
"""

RECEIPT_OCR_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "suggested_entry_type": {"type": "STRING", "nullable": True},
        "vendor_name": {"type": "STRING", "nullable": True},
        "vendor_tax_id": {"type": "STRING", "nullable": True},
        "vendor_branch": {"type": "STRING", "nullable": True},
        "vendor_address": {"type": "STRING", "nullable": True},
        "receipt_no": {"type": "STRING", "nullable": True},
        "document_date": {"type": "STRING", "nullable": True},
        "suggested_request_type": {"type": "STRING", "nullable": True},
        "suggested_accounting_vat_mode": {"type": "STRING", "nullable": True},
        "total_amount": {"type": "NUMBER", "nullable": True},
        "subtotal_amount": {"type": "NUMBER", "nullable": True},
        "vat_amount": {"type": "NUMBER", "nullable": True},
        "vat_rate": {"type": "NUMBER", "nullable": True},
        "line_items_complete": {"type": "BOOLEAN", "nullable": True},
        "page_count": {"type": "INTEGER", "nullable": True},
        "items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "description": {"type": "STRING"},
                    "qty": {"type": "NUMBER", "nullable": True},
                    "price": {"type": "NUMBER", "nullable": True},
                    "amount": {"type": "NUMBER", "nullable": True},
                },
                "required": ["description"],
            },
        },
        "low_confidence_fields": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "warnings": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "message": {"type": "STRING", "nullable": True},
    },
}


# ---------------------------------------------------------------------------
# BOQ Sheet Parsing with Gemini  (LLD §3.1, BRD §4.1)
# ---------------------------------------------------------------------------
BOQ_PARSE_PROMPT = """\
You are an Expert Construction Quantity Surveyor AI.
I will provide you with raw data from a Google Sheet tab named "{sheet_name}".
This data represents a Bill of Quantities (BOQ) for a construction project.

## YOUR TASKS:
1. **Identify the WBS Hierarchy** (Work Breakdown Structure):
   - Level 1 = Main Category  (e.g. "Electrical and Communication System")
   - Level 2 = Sub-Category   (e.g. "LIGHTING FIXTURE")
   - Level 3 = Line Item      (e.g. "Recessed Downlight")
   - Assign a `parent_index` that references the index of the parent row (null for Level 1).

2. **Split Material vs Labor costs**:
   - Identify which cost columns are Materials and which are Labor.
   - If a row has only one price column, classify it based on the item description.

3. **Extract all item details**: item_no, description, qty, unit, material_unit_price, labor_unit_price, total_material, total_labor, grand_total.

## OUTPUT FORMAT:
Return ONLY a valid JSON array. No markdown, no explanation.
Each element must have these exact keys:
```json
[
  {{
    "index": 0,
    "wbs_level": 1,
    "parent_index": null,
    "item_no": "1",
    "description": "Main Category Name",
    "qty": null,
    "unit": null,
    "material_unit_price": 0,
    "labor_unit_price": 0,
    "total_material": 189130.00,
    "total_labor": 124200.00,
    "grand_total": 313330.00
  }}
]
```

## RULES:
- If confidence in a mapping is below 80%, set the field value to null and add a key "low_confidence": true.
- Preserve the original row order.
- All monetary values must be numbers (not strings).

## RAW DATA:
{raw_data}
"""


async def parse_boq_sheet_with_gemini(
    sheet_name: str,
    raw_data: list,
) -> list[dict]:
    """
    Send raw Google Sheet rows to Gemini 2.0 Flash for semantic BOQ parsing.

    Args:
        sheet_name: Name of the sheet tab (e.g. 'AC', 'EE', 'SN').
        raw_data:   List of rows (each row is a list of cell values).

    Returns:
        A list of dicts representing parsed BOQ items with WBS hierarchy.

    Raises:
        ValueError: If Gemini returns invalid / unparseable JSON.
        Exception:  On GenAI / Vertex AI API errors.
    """
    try:
        client = _get_client()
        started_at = perf_counter()

        prompt = BOQ_PARSE_PROMPT.format(
            sheet_name=sheet_name,
            raw_data=json.dumps(raw_data, ensure_ascii=False, default=str),
        )

        response = await client.aio.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                responseMimeType="application/json",
            ),
        )
        response_text = (response.text or "").strip()

        # Strip markdown code fences if present
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
        if response_text.endswith("```"):
            response_text = response_text.rsplit("```", 1)[0]
        response_text = response_text.strip()

        parsed_items: list[dict] = json.loads(response_text)

        if not isinstance(parsed_items, list):
            raise ValueError("Gemini did not return a JSON array.")

        logger.info(
            "Parsed %d BOQ items from sheet '%s' raw_rows=%d prompt_chars=%d elapsed_ms=%.1f",
            len(parsed_items),
            sheet_name,
            len(raw_data),
            len(prompt),
            (perf_counter() - started_at) * 1000,
        )
        return parsed_items

    except json.JSONDecodeError as exc:
        logger.error("Gemini returned invalid JSON for sheet '%s': %s", sheet_name, exc)
        raise ValueError(f"AI returned invalid JSON for sheet '{sheet_name}'.") from exc

    except Exception as exc:
        logger.exception("GenAI call failed for sheet '%s'", sheet_name)
        raise


async def extract_receipt_data_with_gemini(
    *,
    file_bytes: bytes,
    mime_type: str,
    file_name: str | None = None,
) -> dict:
    """
    Run OCR + field extraction on a receipt-like image or PDF using Gemini 2.5 Flash.

    Returns a dict matching the Input page receipt extract contract.
    """
    try:
        client = _get_client()
        started_at = perf_counter()

        response = await client.aio.models.generate_content(
            model=_GEMINI_MODEL,
            contents=[
                RECEIPT_OCR_PROMPT,
                genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            ],
            config=genai_types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=RECEIPT_OCR_RESPONSE_SCHEMA,
            ),
        )

        response_text = (response.text or "").strip()
        extracted = json.loads(response_text) if response_text else {}
        if not isinstance(extracted, dict):
            raise ValueError("Gemini did not return a JSON object for receipt OCR.")

        normalized_items = []
        for item in extracted.get("items") or []:
            if not isinstance(item, dict):
                continue
            description = str(item.get("description") or "").strip()
            if not description:
                continue
            qty = item.get("qty")
            price = item.get("price", item.get("unit_price"))
            amount = item.get("amount")
            normalized_qty = _to_receipt_number(qty) if qty is not None else 0
            normalized_price = _to_receipt_number(price) if price is not None else 0
            normalized_amount = (
                _to_receipt_number(amount)
                if amount is not None
                else round(normalized_qty * normalized_price, 2)
            )
            normalized_items.append(
                {
                    "description": description,
                    "qty": normalized_qty,
                    "price": normalized_price,
                    "amount": normalized_amount,
                }
            )

        low_confidence_fields = _normalize_receipt_string_list(
            extracted.get("low_confidence_fields")
        )
        warnings = _normalize_receipt_string_list(extracted.get("warnings"))

        total_amount = _to_receipt_number(extracted.get("total_amount"))
        subtotal_amount = _to_receipt_number(extracted.get("subtotal_amount"))
        vat_amount = _to_receipt_number(extracted.get("vat_amount"))
        vat_rate = _to_receipt_number(extracted.get("vat_rate"))
        vendor_tax_id = _normalize_vendor_tax_id(extracted.get("vendor_tax_id"))
        vendor_branch = _clean_receipt_text(extracted.get("vendor_branch"))
        vendor_address = _clean_receipt_text(extracted.get("vendor_address"))
        suggested_accounting_vat_mode = _normalize_accounting_vat_mode(
            extracted.get("suggested_accounting_vat_mode")
        )
        if not suggested_accounting_vat_mode:
            suggested_accounting_vat_mode = "vat_inclusive" if vat_amount > 0 or vat_rate > 0 else "no_vat"
        page_count = int(_to_receipt_number(extracted.get("page_count")))
        line_items_total = round(sum(item["amount"] for item in normalized_items), 2)
        line_items_complete = _to_receipt_bool(
            extracted.get("line_items_complete"),
            default=True,
        )

        if total_amount <= 0:
            warnings.append("OCR ยังไม่พบยอดชำระจริง กรุณาตรวจยอดก่อนส่ง")
            low_confidence_fields.append("total_amount")

        if vendor_tax_id and len(vendor_tax_id) != 13:
            warnings.append("OCR อ่านเลขผู้เสียภาษีได้ไม่ครบ 13 หลัก กรุณาตรวจสอบก่อนส่ง")
            low_confidence_fields.append("vendor_tax_id")

        if suggested_accounting_vat_mode != "no_vat":
            missing_tax_fields = []
            if not vendor_tax_id:
                missing_tax_fields.append("เลขผู้เสียภาษี")
            if not vendor_branch:
                missing_tax_fields.append("สาขา")
            if not vendor_address:
                missing_tax_fields.append("ที่อยู่ผู้ขาย")
            if missing_tax_fields:
                warnings.append(
                    "เอกสารมี VAT แต่ OCR ยังอ่านข้อมูลภาษีผู้ขายไม่ครบ: "
                    + ", ".join(missing_tax_fields)
                )

        if normalized_items and not line_items_complete:
            warnings.append("OCR อาจอ่านรายการสินค้า/บริการไม่ครบทุกบรรทัด กรุณาตรวจรายการก่อนส่ง")
            low_confidence_fields.append("items")
            low_confidence_fields.append("line_items_complete")

        if total_amount > 0 and line_items_total:
            reconcile_candidates = [line_items_total]
            if vat_amount:
                reconcile_candidates.append(round(line_items_total + vat_amount, 2))
            if subtotal_amount:
                reconcile_candidates.append(round(subtotal_amount + vat_amount, 2))
                reconcile_candidates.append(subtotal_amount)
            if all(abs(total_amount - candidate) > 0.05 for candidate in reconcile_candidates):
                warnings.append(
                    "ยอดรวมรายการไม่ตรงกับยอดชำระจริง อาจมีส่วนลด VAT หรือรายการที่ OCR อ่านไม่ครบ"
                )
                low_confidence_fields.append("items")

        low_confidence_fields = list(dict.fromkeys(low_confidence_fields))
        warnings = list(dict.fromkeys(warnings))

        normalized_document_date = _normalize_receipt_date(extracted.get("document_date"))
        ocr_raw_json = {
            **extracted,
            "normalized": {
                "vendor_tax_id": vendor_tax_id,
                "vendor_branch": vendor_branch,
                "vendor_address": vendor_address,
                "suggested_accounting_vat_mode": suggested_accounting_vat_mode,
                "total_amount": total_amount,
                "subtotal_amount": subtotal_amount,
                "vat_amount": vat_amount,
                "vat_rate": vat_rate,
                "line_items_total": line_items_total,
                "line_items_count": len(normalized_items),
                "line_items_complete": line_items_complete,
                "page_count": page_count,
                "warnings": warnings,
            },
        }
        result = {
            "file_name": file_name or "uploaded-receipt",
            "content_type": mime_type,
            "suggested_entry_type": str(
                extracted.get("suggested_entry_type") or "EXPENSE"
            ).strip()
            or "EXPENSE",
            "vendor_name": (
                str(extracted.get("vendor_name")).strip()
                if extracted.get("vendor_name") is not None
                else None
            ),
            "vendor_tax_id": vendor_tax_id,
            "vendor_branch": vendor_branch,
            "vendor_address": vendor_address,
            "receipt_no": (
                str(extracted.get("receipt_no")).strip()
                if extracted.get("receipt_no") is not None
                else None
            ),
            "document_date": normalized_document_date,
            "suggested_request_type": (
                str(extracted.get("suggested_request_type")).strip()
                if extracted.get("suggested_request_type") is not None
                else None
            ),
            "suggested_accounting_vat_mode": suggested_accounting_vat_mode,
            "total_amount": total_amount,
            "subtotal_amount": subtotal_amount,
            "vat_amount": vat_amount,
            "vat_rate": vat_rate,
            "line_items_total": line_items_total,
            "line_items_complete": line_items_complete,
            "page_count": page_count,
            "warnings": warnings,
            "items": normalized_items,
            "ocr_raw_json": ocr_raw_json,
            "low_confidence_fields": low_confidence_fields,
            "message": (
                str(extracted.get("message")).strip()
                if extracted.get("message") is not None
                else "OCR completed."
            ),
        }

        if extracted.get("document_date") and not normalized_document_date:
            result["low_confidence_fields"] = list(
                dict.fromkeys([*result["low_confidence_fields"], "document_date"])
            )

        logger.info(
            "Receipt OCR completed file=%s mime_type=%s items=%d elapsed_ms=%.1f",
            file_name or "uploaded-receipt",
            mime_type,
            len(result["items"]),
            (perf_counter() - started_at) * 1000,
        )
        return result

    except json.JSONDecodeError as exc:
        logger.error("Gemini returned invalid JSON for receipt OCR: %s", exc)
        raise ValueError("AI returned invalid JSON for receipt OCR.") from exc
    except Exception:
        logger.exception("Receipt OCR extraction failed for file '%s'", file_name)
        raise


# ---------------------------------------------------------------------------
# Vector Embedding Generation  (BRD §5.1)
# ---------------------------------------------------------------------------
async def generate_embedding(text: str) -> list[float]:
    """
    Generate an embedding vector for a text string using google-genai
    in Vertex AI mode.

    Args:
        text: The text to embed (e.g. a BOQ item description).

    Returns:
        A list of floats.
    """
    try:
        client = _get_client()
        response = await client.aio.models.embed_content(
            model=_EMBEDDING_MODEL,
            contents=text,
        )
        vector = response.embeddings[0].values

        logger.debug("Generated embedding for: %.50s… (%d dims)", text, len(vector))
        return vector

    except Exception as exc:
        logger.exception("Embedding generation failed for text: %.50s…", text)
        raise


# ---------------------------------------------------------------------------
# Strategic AI Chat — RAG  (LLD §3.2, BRD §5.2)
# ---------------------------------------------------------------------------
async def ask_strategic_question(
    question: str,
    context_data: dict | list,
    project_name: str | None = None,
) -> dict:
    """
    Answer a strategic question using RAG — context data is retrieved from
    the database (pgvector similarity + aggregation) BEFORE calling Gemini,
    to prevent token overflow and reduce hallucinations.

    Args:
        question:     The executive's natural-language question.
        context_data: Pre-aggregated financial data from the database.
        project_name: Optional project scope for the answer.

    Returns:
        dict with "reply" (str) and "sources" (list[str]).
    """
    try:
        client = _get_client()

        scope = f"for project '{project_name}'" if project_name else "across all projects"

        prompt = f"""\
You are a Principal Construction Analyst. Answer the user's question based
ONLY on the provided context data. Do not fabricate numbers.

## Scope
Analysing data {scope}.

## Context Data (aggregated from the database)
{json.dumps(context_data, ensure_ascii=False, default=str)}

## User Question
{question}

## Response Rules
- Be concise and data-driven.
- Cite specific items or subcontractors when relevant.
- If the data is insufficient, say so honestly.
"""

        response = await client.aio.models.generate_content(
            model=_GEMINI_MODEL,
            contents=prompt,
        )

        return {
            "reply": (response.text or "").strip(),
            "sources": (
                [item.get("description", "") for item in context_data]
                if isinstance(context_data, list)
                else []
            ),
        }

    except Exception as exc:
        logger.exception("Strategic AI chat failed")
        raise
