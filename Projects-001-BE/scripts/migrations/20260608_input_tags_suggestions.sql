-- Add first-class Input request tags and global Input suggestion sources.
-- Run this once against the target PostgreSQL database before deploying the
-- matching backend code.

ALTER TABLE input_requests
    ADD COLUMN IF NOT EXISTS tags JSON DEFAULT '[]'::json;

UPDATE input_requests
SET tags = '[]'::json
WHERE tags IS NULL;

ALTER TABLE input_requests
    ALTER COLUMN tags SET DEFAULT '[]'::json,
    ALTER COLUMN tags SET NOT NULL;

CREATE TABLE IF NOT EXISTS input_option_suggestions (
    option_type VARCHAR NOT NULL,
    value VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (option_type, value)
);

INSERT INTO input_option_suggestions (option_type, value)
VALUES
    ('WORK_TYPE', 'งานโครงสร้าง'),
    ('WORK_TYPE', 'งานสถาปัตย์'),
    ('WORK_TYPE', 'งานระบบ'),
    ('WORK_TYPE', 'งานบริหารโครงการ'),
    ('WORK_TYPE', 'งานตกแต่ง (Build in)')
ON CONFLICT (option_type, value) DO NOTHING;

INSERT INTO projects (
    id,
    name,
    project_type,
    overhead_percent,
    profit_percent,
    vat_percent,
    contingency_budget,
    status
)
SELECT
    '11111111-1111-4111-8111-111111111111'::uuid,
    'โครงการบริษัท',
    'INTERNAL',
    0,
    0,
    7.00,
    0,
    'ACTIVE'
WHERE NOT EXISTS (
    SELECT 1
    FROM projects
    WHERE name = 'โครงการบริษัท'
);

UPDATE projects
SET project_type = 'INTERNAL',
    status = 'ACTIVE'
WHERE name = 'โครงการบริษัท';
