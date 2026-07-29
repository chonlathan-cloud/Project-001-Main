BEGIN;

ALTER TABLE IF EXISTS input_requests
    ADD COLUMN IF NOT EXISTS external_ai_blocked BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN input_requests.external_ai_blocked IS
    'Owner-controlled deny flag for external AI document-body access.';

COMMIT;
