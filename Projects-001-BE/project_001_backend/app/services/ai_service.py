"""
AI Service — Gemini Integration via google-genai on Vertex AI.

Implements:
  - BOQ Sheet parsing via Gemini  (LLD §3.1, BRD §4.1)
  - Vector embedding generation   (BRD §5.1)
  - Strategic RAG chat             (LLD §3.2)

Uses google-genai SDK in Vertex AI mode.
"""

import json
import logging
import os
from time import perf_counter

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GenAI Initialisation
# ---------------------------------------------------------------------------
_GCP_PROJECT = os.getenv("GCP_PROJECT_ID")
_GCP_LOCATION = os.getenv("GCP_LOCATION", "asia-southeast1")
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

_client: genai.Client | None = None


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
