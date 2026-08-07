BEGIN;

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS system_key VARCHAR;

CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_system_key
    ON projects(system_key)
    WHERE system_key IS NOT NULL;

DO $$
DECLARE
    operations_id UUID;
BEGIN
    SELECT id
    INTO operations_id
    FROM projects
    WHERE id = '11111111-1111-4111-8111-111111111111'::uuid
       OR system_key = 'OPERATIONS'
    ORDER BY
        CASE WHEN id = '11111111-1111-4111-8111-111111111111'::uuid THEN 0 ELSE 1 END
    LIMIT 1;

    IF operations_id IS NULL THEN
        SELECT id
        INTO operations_id
        FROM projects
        WHERE name = 'โครงการบริษัท'
          AND UPPER(project_type) = 'INTERNAL'
        ORDER BY id
        LIMIT 1;
    END IF;

    IF operations_id IS NULL THEN
        RAISE EXCEPTION
            'Operations bootstrap failed: expected fixed UUID or legacy โครงการบริษัท/INTERNAL project.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM projects
        WHERE system_key = 'OPERATIONS'
          AND id <> operations_id
    ) THEN
        RAISE EXCEPTION 'Operations bootstrap failed: duplicate OPERATIONS system key detected.';
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
END $$;

CREATE TABLE IF NOT EXISTS fund_buckets (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL UNIQUE REFERENCES projects(id),
    bucket_type VARCHAR NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'THB',
    balance_start_date DATE,
    protected_reserve NUMERIC(15, 2) NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_fund_bucket_type CHECK (bucket_type IN ('PROJECT', 'OPERATIONS')),
    CONSTRAINT ck_fund_bucket_currency CHECK (currency = 'THB'),
    CONSTRAINT ck_fund_bucket_status CHECK (status IN ('SETUP', 'ACTIVE', 'LOCKED')),
    CONSTRAINT ck_fund_bucket_reserve CHECK (protected_reserve >= 0),
    CONSTRAINT ck_fund_bucket_start_month CHECK (
        balance_start_date IS NULL
        OR EXTRACT(DAY FROM balance_start_date) = 1
    )
);

CREATE INDEX IF NOT EXISTS ix_fund_buckets_project_id
    ON fund_buckets(project_id);

CREATE TABLE IF NOT EXISTS fund_allocations (
    id UUID PRIMARY KEY,
    reference_no VARCHAR NOT NULL UNIQUE,
    source_bucket_id UUID NOT NULL REFERENCES fund_buckets(id),
    target_bucket_id UUID NOT NULL REFERENCES fund_buckets(id),
    amount NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'THB',
    reason TEXT NOT NULL,
    note TEXT,
    status VARCHAR NOT NULL DEFAULT 'POSTED',
    reversal_of UUID UNIQUE REFERENCES fund_allocations(id),
    idempotency_key VARCHAR NOT NULL UNIQUE,
    created_by VARCHAR NOT NULL,
    source_balance_before NUMERIC(15, 2) NOT NULL,
    source_balance_after NUMERIC(15, 2) NOT NULL,
    target_balance_before NUMERIC(15, 2) NOT NULL,
    target_balance_after NUMERIC(15, 2) NOT NULL,
    source_balance_version VARCHAR NOT NULL,
    target_balance_version VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_fund_allocation_positive_amount CHECK (amount > 0),
    CONSTRAINT ck_fund_allocation_distinct_buckets CHECK (source_bucket_id <> target_bucket_id),
    CONSTRAINT ck_fund_allocation_currency CHECK (currency = 'THB'),
    CONSTRAINT ck_fund_allocation_status CHECK (status IN ('POSTED', 'REVERSED'))
);

CREATE INDEX IF NOT EXISTS ix_fund_allocations_source_bucket_id
    ON fund_allocations(source_bucket_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_fund_allocations_target_bucket_id
    ON fund_allocations(target_bucket_id, created_at DESC, id DESC);

CREATE TABLE IF NOT EXISTS fund_ledger_entries (
    id UUID PRIMARY KEY,
    allocation_id UUID REFERENCES fund_allocations(id),
    bucket_id UUID NOT NULL REFERENCES fund_buckets(id),
    direction VARCHAR NOT NULL,
    entry_type VARCHAR NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    effective_date DATE NOT NULL,
    reason TEXT NOT NULL,
    created_by VARCHAR NOT NULL,
    idempotency_key VARCHAR UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_fund_ledger_direction CHECK (direction IN ('DEBIT', 'CREDIT')),
    CONSTRAINT ck_fund_ledger_entry_type CHECK (
        entry_type IN ('ALLOCATION', 'REVERSAL', 'OPENING_BALANCE', 'ADJUSTMENT')
    ),
    CONSTRAINT ck_fund_ledger_nonnegative_amount CHECK (amount >= 0)
);

CREATE INDEX IF NOT EXISTS ix_fund_ledger_entries_allocation_id
    ON fund_ledger_entries(allocation_id);
CREATE INDEX IF NOT EXISTS ix_fund_ledger_entries_bucket_id
    ON fund_ledger_entries(bucket_id, effective_date, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_fund_ledger_opening_balance_per_bucket
    ON fund_ledger_entries(bucket_id)
    WHERE entry_type = 'OPENING_BALANCE';

CREATE TABLE IF NOT EXISTS fund_audit_events (
    id UUID PRIMARY KEY,
    event_type VARCHAR NOT NULL,
    allocation_id UUID REFERENCES fund_allocations(id),
    bucket_id UUID REFERENCES fund_buckets(id),
    actor VARCHAR NOT NULL,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_fund_audit_events_event_type
    ON fund_audit_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_fund_audit_events_allocation_id
    ON fund_audit_events(allocation_id);
CREATE INDEX IF NOT EXISTS ix_fund_audit_events_bucket_id
    ON fund_audit_events(bucket_id);

INSERT INTO fund_buckets (
    id,
    project_id,
    bucket_type,
    currency,
    protected_reserve,
    status
)
SELECT
    md5('fund-bucket:' || projects.id::text)::uuid,
    projects.id,
    CASE WHEN projects.system_key = 'OPERATIONS' THEN 'OPERATIONS' ELSE 'PROJECT' END,
    'THB',
    0,
    CASE WHEN projects.system_key = 'OPERATIONS' THEN 'SETUP' ELSE 'ACTIVE' END
FROM projects
ON CONFLICT (project_id) DO NOTHING;

UPDATE fund_buckets AS bucket
SET bucket_type = 'OPERATIONS',
    currency = 'THB',
    updated_at = NOW()
FROM projects
WHERE bucket.project_id = projects.id
  AND projects.system_key = 'OPERATIONS';

INSERT INTO fund_audit_events (
    id,
    event_type,
    bucket_id,
    actor,
    detail
)
SELECT
    md5('operations-bootstrap:' || bucket.id::text)::uuid,
    'operations_bucket.bootstrap_completed',
    bucket.id,
    'database-migration',
    jsonb_build_object('project_id', project.id::text, 'system_key', project.system_key)
FROM fund_buckets AS bucket
JOIN projects AS project ON project.id = bucket.project_id
WHERE project.system_key = 'OPERATIONS'
ON CONFLICT (id) DO NOTHING;

COMMIT;
