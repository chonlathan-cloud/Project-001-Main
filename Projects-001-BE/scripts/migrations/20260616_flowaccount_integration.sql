ALTER TABLE IF EXISTS input_requests
    ADD COLUMN IF NOT EXISTS vendor_tax_id VARCHAR,
    ADD COLUMN IF NOT EXISTS vendor_branch VARCHAR,
    ADD COLUMN IF NOT EXISTS vendor_address TEXT,
    ADD COLUMN IF NOT EXISTS accounting_vat_mode VARCHAR,
    ADD COLUMN IF NOT EXISTS accounting_wht_rate NUMERIC(5, 2),
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
    ADD COLUMN IF NOT EXISTS flowaccount_duplicate_override_reason TEXT;

UPDATE input_requests
SET
    accounting_ready = COALESCE(accounting_ready, FALSE),
    accounting_readiness_errors = COALESCE(accounting_readiness_errors, '[]'::jsonb),
    flowaccount_sync_status = COALESCE(flowaccount_sync_status, 'NOT_READY'),
    flowaccount_attachment_status = COALESCE(flowaccount_attachment_status, 'NOT_READY'),
    flowaccount_supplier_invoice_status = COALESCE(flowaccount_supplier_invoice_status, 'NOT_READY'),
    flowaccount_payment_status = COALESCE(flowaccount_payment_status, 'NOT_READY'),
    flowaccount_linked_manually = COALESCE(flowaccount_linked_manually, FALSE)
WHERE accounting_ready IS NULL
   OR accounting_readiness_errors IS NULL
   OR flowaccount_sync_status IS NULL
   OR flowaccount_attachment_status IS NULL
   OR flowaccount_supplier_invoice_status IS NULL
   OR flowaccount_payment_status IS NULL
   OR flowaccount_linked_manually IS NULL;
