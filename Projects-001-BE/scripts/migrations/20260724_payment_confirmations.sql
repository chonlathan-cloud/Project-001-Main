BEGIN;

CREATE TABLE IF NOT EXISTS input_payment_reference_counters (
    reference_date DATE NOT NULL,
    entry_type VARCHAR NOT NULL,
    last_sequence INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (reference_date, entry_type),
    CONSTRAINT ck_input_payment_reference_counter_entry_type
        CHECK (entry_type IN ('EXPENSE', 'INCOME')),
    CONSTRAINT ck_input_payment_reference_counter_sequence
        CHECK (last_sequence >= 0)
);

CREATE TABLE IF NOT EXISTS input_payments (
    id UUID PRIMARY KEY,
    input_request_id UUID NOT NULL
        REFERENCES input_requests(id) ON DELETE CASCADE,
    internal_reference VARCHAR NOT NULL,
    sequence_number INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    bank_transfer_reference VARCHAR NULL,
    paid_storage_prefix VARCHAR NOT NULL,
    recorded_by VARCHAR NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_input_payments_input_request_id UNIQUE (input_request_id),
    CONSTRAINT uq_input_payments_internal_reference UNIQUE (internal_reference),
    CONSTRAINT ck_input_payments_sequence CHECK (sequence_number > 0),
    CONSTRAINT ck_input_payments_amount CHECK (amount > 0)
);

CREATE INDEX IF NOT EXISTS ix_input_payments_input_request_id
    ON input_payments (input_request_id);
CREATE INDEX IF NOT EXISTS ix_input_payments_internal_reference
    ON input_payments (internal_reference);
CREATE INDEX IF NOT EXISTS ix_input_payments_payment_date
    ON input_payments (payment_date);

CREATE TABLE IF NOT EXISTS input_payment_confirmations (
    id UUID PRIMARY KEY,
    payment_id UUID NOT NULL
        REFERENCES input_payments(id) ON DELETE CASCADE,
    subcontractor_id VARCHAR NOT NULL,
    idempotency_key VARCHAR NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR NOT NULL DEFAULT 'SUBMITTED',
    received_date DATE NOT NULL,
    received_full_amount BOOLEAN NOT NULL DEFAULT TRUE,
    note TEXT NULL,
    file_name VARCHAR NOT NULL,
    content_type VARCHAR NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_key VARCHAR NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verified_at TIMESTAMPTZ NULL,
    verified_by VARCHAR NULL,
    verification_note TEXT NULL,
    superseded_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_input_payment_confirmation_version CHECK (version > 0),
    CONSTRAINT ck_input_payment_confirmation_size CHECK (size_bytes > 0),
    CONSTRAINT ck_input_payment_confirmation_status
        CHECK (status IN ('SUBMITTED', 'VERIFIED', 'CHANGES_REQUESTED', 'SUPERSEDED')),
    CONSTRAINT uq_input_payment_confirmations_idempotency
        UNIQUE (payment_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_input_payment_confirmations_payment_id
    ON input_payment_confirmations (payment_id);
CREATE INDEX IF NOT EXISTS ix_input_payment_confirmations_subcontractor_id
    ON input_payment_confirmations (subcontractor_id);

COMMIT;
