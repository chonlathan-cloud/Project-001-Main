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
from app.models import (  # noqa: F401
    BOQItem,
    ChatHistory,
    FundAllocation,
    FundAuditEvent,
    FundBucket,
    FundLedgerEntry,
    InputOptionSuggestion,
    InputRequest,
    InputRequestLineItem,
    Installment,
    Project,
    Transaction,
)


async def main() -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS projects
                ADD COLUMN IF NOT EXISTS system_key VARCHAR
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_system_key
                ON projects(system_key)
                WHERE system_key IS NOT NULL
                """
            )
        )
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
                DO $$
                DECLARE operations_id UUID;
                BEGIN
                    SELECT id INTO operations_id
                    FROM projects
                    WHERE id = '11111111-1111-4111-8111-111111111111'::uuid
                       OR system_key = 'OPERATIONS'
                    ORDER BY CASE
                        WHEN id = '11111111-1111-4111-8111-111111111111'::uuid THEN 0
                        ELSE 1
                    END
                    LIMIT 1;

                    IF operations_id IS NULL THEN
                        SELECT id INTO operations_id
                        FROM projects
                        WHERE name = 'โครงการบริษัท'
                          AND UPPER(project_type) = 'INTERNAL'
                        ORDER BY id
                        LIMIT 1;
                    END IF;

                    IF operations_id IS NULL THEN
                        RAISE EXCEPTION 'Operations bootstrap source Project was not found.';
                    END IF;

                    UPDATE projects
                    SET system_key = 'OPERATIONS',
                        name = CASE
                            WHEN system_key IS NULL OR name = 'โครงการบริษัท'
                                THEN 'Company Operations / ค่าใช้จ่ายส่วนกลาง'
                            ELSE name
                        END,
                        project_type = 'INTERNAL',
                        status = 'ACTIVE'
                    WHERE id = operations_id;
                END $$
                """
            )
        )
        await conn.execute(
            text(
                """
                INSERT INTO fund_buckets (
                    id, project_id, bucket_type, currency, protected_reserve, status
                )
                SELECT
                    md5('fund-bucket:' || projects.id::text)::uuid,
                    projects.id,
                    CASE WHEN projects.system_key = 'OPERATIONS' THEN 'OPERATIONS' ELSE 'PROJECT' END,
                    'THB',
                    0,
                    CASE WHEN projects.system_key = 'OPERATIONS' THEN 'SETUP' ELSE 'ACTIVE' END
                FROM projects
                ON CONFLICT (project_id) DO NOTHING
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE fund_buckets AS bucket
                SET bucket_type = 'OPERATIONS', currency = 'THB', updated_at = NOW()
                FROM projects
                WHERE bucket.project_id = projects.id
                  AND projects.system_key = 'OPERATIONS'
                """
            )
        )
        await conn.execute(
            text(
                """
                INSERT INTO fund_audit_events (
                    id, event_type, bucket_id, actor, detail
                )
                SELECT
                    md5('operations-bootstrap:' || bucket.id::text)::uuid,
                    'operations_bucket.bootstrap_completed',
                    bucket.id,
                    'create-missing-tables',
                    json_build_object('project_id', project.id::text)
                FROM fund_buckets AS bucket
                JOIN projects AS project ON project.id = bucket.project_id
                WHERE project.system_key = 'OPERATIONS'
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_fund_ledger_opening_balance_per_bucket
                ON fund_ledger_entries(bucket_id)
                WHERE entry_type = 'OPENING_BALANCE'
                """
            )
        )
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
                ADD COLUMN IF NOT EXISTS accounting_readiness_errors JSON DEFAULT '[]'::json,
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
                    accounting_readiness_errors = COALESCE(accounting_readiness_errors, '[]'::json),
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
