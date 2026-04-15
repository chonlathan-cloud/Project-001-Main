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
- receipt_no: receipt number, invoice number, tax invoice number, document number, or reference number
- document_date: document date in YYYY-MM-DD if a reliable date is visible, otherwise null
- suggested_request_type: one of ["ค่าวัสดุ", "ค่าแรง", "ค่าเบิกล่วงหน้า", "ค่าใช้จ่ายทั่วไป"] or null
- total_amount: final payable/received amount as number if visible, otherwise 0
- items: up to 10 line items with description, qty, price
- low_confidence_fields: list of field names that are visible but uncertain. Use only these names:
  ["suggested_entry_type", "vendor_name", "receipt_no", "document_date", "suggested_request_type", "total_amount", "items"]
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
- total_amount must be numeric only, with no currency symbols.
- items[].qty and items[].price must be numeric when available; otherwise use 0.
- If a field is missing entirely, keep it null/0 and do not include it in low_confidence_fields.
- Return only valid JSON. No markdown.
"""

RECEIPT_OCR_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "suggested_entry_type": {"type": "STRING", "nullable": True},
        "vendor_name": {"type": "STRING", "nullable": True},
        "receipt_no": {"type": "STRING", "nullable": True},
        "document_date": {"type": "STRING", "nullable": True},
        "suggested_request_type": {"type": "STRING", "nullable": True},
        "total_amount": {"type": "NUMBER", "nullable": True},
        "items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "description": {"type": "STRING"},
                    "qty": {"type": "NUMBER", "nullable": True},
                    "price": {"type": "NUMBER", "nullable": True},
                },
                "required": ["description"],
            },
        },
        "low_confidence_fields": {
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
            price = item.get("price")
            normalized_items.append(
                {
                    "description": description,
                    "qty": float(qty) if qty is not None else 0,
                    "price": float(price) if price is not None else 0,
                }
            )

        low_confidence_fields: list[str] = []
        for field_name in extracted.get("low_confidence_fields") or []:
            cleaned = str(field_name or "").strip()
            if cleaned and cleaned not in low_confidence_fields:
                low_confidence_fields.append(cleaned)

        normalized_document_date = _normalize_receipt_date(extracted.get("document_date"))
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
            "total_amount": float(extracted.get("total_amount") or 0),
            "items": normalized_items[:10],
            "ocr_raw_json": extracted,
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
