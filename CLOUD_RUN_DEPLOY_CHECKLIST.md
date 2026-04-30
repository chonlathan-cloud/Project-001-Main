# Cloud Run Deploy Checklist

This project is intended to run as two separate Cloud Run services:

- `Projects-001-BE`
- `Projects-001-FE`

## Backend

Use [Projects-001-BE/Dockerfile](/Users/chonlathansongsri/Documents/Manee-son/Projects-001/Projects-001-BE/Dockerfile)

Required runtime env vars:

- `APP_ENV=production`
- `CORS_ORIGINS=https://<frontend-cloud-run-url>`
- `DATABASE_URL=<postgresql+asyncpg url>`
- `GCP_PROJECT_ID`
- `GCP_LOCATION`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_WEB_API_KEY`
- `FIREBASE_STORAGE_BUCKET`
- `LINE_CHANNEL_ID`
- `LINE_CHANNEL_SECRET`
- `LINE_LIFF_ID`
- `LINE_REDIRECT_URI=https://<frontend-cloud-run-url>/auth/line/callback`
- `JWT_SECRET_KEY`
- `GCS_BUCKET_NAME`
- `GCS_KYC_PREFIX`
- `GCS_PROFILE_PREFIX`
- `GCS_TEMP_BILLS_PREFIX`
- `GCS_PERM_BILLS_PREFIX`
- `SIGNED_URL_EXPIRES_MINUTES`
- `GEMINI_MODEL`
- `EMBEDDING_MODEL`
- `ADMIN_EMAIL_DOMAIN` or `ADMIN_EMAILS`

Notes:

- On Cloud Run, prefer service-account ADC. Leave `GOOGLE_APPLICATION_CREDENTIALS` unset unless you explicitly mount a JSON key file.
- The database must support the `vector` extension because the backend uses `pgvector`.
- Before first production run, create tables and missing columns. Current helper script is [Projects-001-BE/scripts/create_missing_tables.py](/Users/chonlathansongsri/Documents/Manee-son/Projects-001/Projects-001-BE/scripts/create_missing_tables.py).
- Health endpoint: `/health`

## Frontend

Use [Projects-001-FE/Dockerfile](/Users/chonlathansongsri/Documents/Manee-son/Projects-001/Projects-001-FE/Dockerfile)

Build-time args required:

- `VITE_API_BASE_URL=https://<backend-cloud-run-url>`
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_APP_ID`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_LINE_LIFF_ID`
- `VITE_BOQ_BATCH_SYNC_MAX_TABS`

Notes:

- Frontend is a static SPA served by nginx with fallback routing via [Projects-001-FE/nginx.conf.template](/Users/chonlathansongsri/Documents/Manee-son/Projects-001/Projects-001-FE/nginx.conf.template).
- Health endpoint: `/health`

## External Console Updates

Before go-live, update these external settings:

- Firebase Authentication `Authorized domains` must include the frontend Cloud Run host.
- LINE LIFF `Endpoint URL` should point to `https://<frontend-cloud-run-url>/login`
- LINE callback should resolve to `https://<frontend-cloud-run-url>/auth/line/callback`
- Backend `CORS_ORIGINS` must include the frontend Cloud Run host exactly.

## Validated Locally

Validated in this workspace:

- backend python compile checks passed
- frontend eslint checks passed on touched files
- frontend production build passed

Not validated here:

- Docker image build, because Docker daemon was not running on this machine
- Cloud SQL connectivity
- production Firebase / LINE console settings
