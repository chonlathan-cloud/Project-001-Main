"""
Create any missing database tables without dropping existing data.

Usage:
  python scripts/create_missing_tables.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from app.core.database import engine, Base
from app.models import BOQItem, ChatHistory, InputOptionSuggestion, InputRequest, InputRequestLineItem, Installment, Project, Transaction  # noqa: F401


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS input_requests
                ADD COLUMN IF NOT EXISTS subcontractor_id VARCHAR,
                ADD COLUMN IF NOT EXISTS approved_amount NUMERIC(15, 2),
                ADD COLUMN IF NOT EXISTS review_note TEXT,
                ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS vendor_name VARCHAR,
                ADD COLUMN IF NOT EXISTS vendor_tax_id VARCHAR,
                ADD COLUMN IF NOT EXISTS vendor_branch VARCHAR,
                ADD COLUMN IF NOT EXISTS vendor_address TEXT,
                ADD COLUMN IF NOT EXISTS receipt_no VARCHAR,
                ADD COLUMN IF NOT EXISTS document_date DATE,
                ADD COLUMN IF NOT EXISTS accounting_vat_mode VARCHAR,
                ADD COLUMN IF NOT EXISTS accounting_wht_rate NUMERIC(5, 2),
                ADD COLUMN IF NOT EXISTS ocr_raw_json JSONB,
                ADD COLUMN IF NOT EXISTS ocr_low_confidence_fields JSONB,
                ADD COLUMN IF NOT EXISTS is_duplicate_flag BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS duplicate_reason TEXT,
                ADD COLUMN IF NOT EXISTS duplicate_of_request_id UUID,
                ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS payment_reference VARCHAR,
                ADD COLUMN IF NOT EXISTS accounting_ready BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS accounting_readiness_errors JSONB DEFAULT '[]'::jsonb,
                ADD COLUMN IF NOT EXISTS flowaccount_sync_status VARCHAR DEFAULT 'NOT_READY',
                ADD COLUMN IF NOT EXISTS flowaccount_expense_id VARCHAR,
                ADD COLUMN IF NOT EXISTS flowaccount_document_no VARCHAR,
                ADD COLUMN IF NOT EXISTS flowaccount_external_document_id VARCHAR,
                ADD COLUMN IF NOT EXISTS flowaccount_synced_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS flowaccount_sync_error TEXT,
                ADD COLUMN IF NOT EXISTS flowaccount_attachment_status VARCHAR DEFAULT 'NOT_READY',
                ADD COLUMN IF NOT EXISTS flowaccount_attachment_error TEXT,
                ADD COLUMN IF NOT EXISTS flowaccount_attachment_synced_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS flowaccount_supplier_invoice_status VARCHAR DEFAULT 'NOT_READY',
                ADD COLUMN IF NOT EXISTS flowaccount_supplier_invoice_error TEXT,
                ADD COLUMN IF NOT EXISTS flowaccount_supplier_invoice_id VARCHAR,
                ADD COLUMN IF NOT EXISTS flowaccount_supplier_invoice_synced_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS flowaccount_payment_status VARCHAR DEFAULT 'NOT_READY',
                ADD COLUMN IF NOT EXISTS flowaccount_payment_error TEXT,
                ADD COLUMN IF NOT EXISTS flowaccount_payment_synced_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS flowaccount_linked_manually BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS flowaccount_duplicate_override_reason TEXT,
                ADD COLUMN IF NOT EXISTS tags JSON DEFAULT '[]'::json
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE input_requests
                SET
                    tags = COALESCE(tags, '[]'::json),
                    accounting_ready = COALESCE(accounting_ready, FALSE),
                    accounting_readiness_errors = COALESCE(accounting_readiness_errors, '[]'::jsonb),
                    flowaccount_sync_status = COALESCE(flowaccount_sync_status, 'NOT_READY'),
                    flowaccount_attachment_status = COALESCE(flowaccount_attachment_status, 'NOT_READY'),
                    flowaccount_supplier_invoice_status = COALESCE(flowaccount_supplier_invoice_status, 'NOT_READY'),
                    flowaccount_payment_status = COALESCE(flowaccount_payment_status, 'NOT_READY'),
                    flowaccount_linked_manually = COALESCE(flowaccount_linked_manually, FALSE)
                WHERE tags IS NULL
                   OR accounting_ready IS NULL
                   OR accounting_readiness_errors IS NULL
                   OR flowaccount_sync_status IS NULL
                   OR flowaccount_attachment_status IS NULL
                   OR flowaccount_supplier_invoice_status IS NULL
                   OR flowaccount_payment_status IS NULL
                   OR flowaccount_linked_manually IS NULL
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS input_request_line_items (
                    id UUID PRIMARY KEY,
                    input_request_id UUID NOT NULL REFERENCES input_requests(id) ON DELETE CASCADE,
                    line_no INTEGER NOT NULL DEFAULT 1,
                    description TEXT NOT NULL,
                    qty NUMERIC(15, 4) NOT NULL DEFAULT 1,
                    unit_price NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    work_type VARCHAR,
                    request_type VARCHAR,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_input_request_line_items_input_request_id
                ON input_request_line_items(input_request_id)
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS installments
                ADD COLUMN IF NOT EXISTS subcontractor_id VARCHAR
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS transactions
                ADD COLUMN IF NOT EXISTS subcontractor_id VARCHAR
                """
            )
        )
    print("create_all completed. Missing tables have been created if needed.")


if __name__ == "__main__":
    asyncio.run(main())
