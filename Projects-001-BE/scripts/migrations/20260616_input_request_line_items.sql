-- Add first-class editable line items for Input requests.
-- Existing requests stay valid because the request header still stores amount/note.

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
);

CREATE INDEX IF NOT EXISTS ix_input_request_line_items_input_request_id
ON input_request_line_items(input_request_id);
