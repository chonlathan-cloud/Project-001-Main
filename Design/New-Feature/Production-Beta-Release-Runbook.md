# Production Beta Release Runbook

Last updated: 2026-07-01

Project: `project001-489710`

This runbook defines how to release the same application version to the current demo environment and the clean production beta environment.

Do not print, paste, or commit secret payloads while using this runbook.

## Environment Map

| Area | Demo | Production beta |
| --- | --- | --- |
| Environment key | `demo` | `prod-beta` |
| Backend Cloud Run | `projects-001-be` | `projects-001-be-beta` |
| Frontend Cloud Run | `projects-001-fe` | `projects-001-fe-beta` |
| Cloud SQL | Current demo instance | `project-001-beta` |
| Cloud SQL connection | Current demo connection | `project001-489710:asia-southeast1:project-001-beta` |
| Firestore | `(default)` | `prod-beta` |
| Identity Platform tenant | Default/current auth context | `beta-company-001-bswmk` |
| Main GCS bucket | Current demo bucket | `kyc_id_cards-beta` |
| Inspection GCS bucket | Current demo inspection bucket | `project001-489710-work-inspection-beta` |
| Runtime service account | Current demo runtime identity | `backend-runtime@project001-489710.iam.gserviceaccount.com` |

Excluded resources:

- Cloud Run: `project-saas-001-be`
- Cloud Run: `project-saas-001-fe`
- Cloud SQL: `project-001-saas`
- Cloud SQL: `project-001-saas-restore-test`

These belong to the separate SaaS platform/repository and must not be attached to this beta release path.

## Release Rule

Demo and production beta must run the same code and schema, but never share customer data, demo data, uploaded files, auth users, or secret values.

Required release parity:

- Same Git commit.
- Same backend source version.
- Same frontend source version.
- Same database schema revision.
- Same default feature behavior unless an environment override is explicitly documented.
- Different database, Firestore database, GCS buckets, Identity Platform tenant, and secrets.

## Pre-Deploy Safety Gates

Complete these before deploying production beta:

- Confirm the intended Git commit or branch.
- Confirm the release was tested locally or in demo first.
- Confirm no `.env` files, service account keys, or secret payloads are staged.
- Confirm production beta backend config uses:

```text
APP_ENV=prod-beta
FIRESTORE_DATABASE_ID=prod-beta
IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk
GCS_BUCKET_NAME=kyc_id_cards-beta
INSPECTION_GCS_BUCKET=project001-489710-work-inspection-beta
FLOWACCOUNT_ENABLED=false
```

- Confirm production beta frontend build config uses:

```text
VITE_APP_ENV=prod-beta
VITE_IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk
VITE_API_BASE_URL=https://projects-001-be-beta-678310400174.asia-southeast1.run.app
```

- Confirm production beta Cloud SQL points only to:

```text
project001-489710:asia-southeast1:project-001-beta
```

- Confirm beta Secret Manager versions exist for required secrets without reading the payloads.
- Confirm FlowAccount remains disabled until beta FlowAccount credentials are intentionally configured.
- Confirm no demo seed script is run against production beta.

## Recommended Verification Commands

Use these commands to verify metadata only. They must not print secret payloads.

```bash
gcloud run services describe projects-001-be-beta \
  --project project001-489710 \
  --region asia-southeast1 \
  --format="value(status.url)"
```

```bash
gcloud run services describe projects-001-fe-beta \
  --project project001-489710 \
  --region asia-southeast1 \
  --format="value(status.url)"
```

```bash
gcloud sql instances describe project-001-beta \
  --project project001-489710 \
  --format="table(name,state,connectionName)"
```

```bash
gcloud firestore databases describe prod-beta \
  --project project001-489710
```

```bash
gcloud identity-platform tenants describe beta-company-001-bswmk \
  --project project001-489710
```

## Deploy Production Beta

Use the beta shared deploy config:

```bash
DEPLOY_SHARED_CONFIG=cloudrun-beta.env ./deploy_backend.sh
```

```bash
DEPLOY_SHARED_CONFIG=cloudrun-beta.env ./deploy_frontend.sh
```

Expected services:

```text
Backend: projects-001-be-beta
Frontend: projects-001-fe-beta
```

The default deploy scripts without `DEPLOY_SHARED_CONFIG=cloudrun-beta.env` are for the normal/current environment path. Do not assume they deploy beta unless the shared config is explicitly supplied.

## Post-Deploy Checks

After every production beta deploy, verify:

- Backend service is ready.
- Frontend service is ready.
- Backend is attached only to `project001-489710:asia-southeast1:project-001-beta`.
- Backend environment is `prod-beta`.
- Backend Firestore database is `prod-beta`.
- Backend Identity Platform tenant is `beta-company-001-bswmk`.
- Backend GCS buckets are the beta buckets.
- Backend Secret Manager references use beta secret names.
- Backend `/health` returns HTTP 200 and `{"status":"ok"}`.
- Frontend root URL returns HTTP 200.
- A protected API endpoint returns HTTP 401 when unauthenticated.
- Recent Cloud Run logs have no new `ERROR` entries for the beta services.

## Manual Smoke Test

Run this after the metadata checks:

- Login with a production beta tenant user.
- Confirm login is tenant-scoped to `beta-company-001-bswmk`.
- Confirm demo/default auth users cannot access production beta.
- Confirm production beta starts with zero or bootstrap-only business records.
- Open the main pages used by the beta company.
- Create one controlled test business record only if the beta owner approves it.
- Upload one controlled test file if upload verification is required.
- Confirm writes land in production beta PostgreSQL, Firestore `prod-beta`, and beta GCS buckets.
- Confirm no writes land in demo resources.

Record the result in `Design/New-Feature/Production-Beta-Environment-Verification.md`.

## Rollback

Cloud Run rollback is traffic-based. Prefer rolling back the smallest broken surface.

List revisions:

```bash
gcloud run revisions list \
  --service projects-001-be-beta \
  --project project001-489710 \
  --region asia-southeast1
```

```bash
gcloud run revisions list \
  --service projects-001-fe-beta \
  --project project001-489710 \
  --region asia-southeast1
```

Send traffic to the previous known-good backend revision:

```bash
gcloud run services update-traffic projects-001-be-beta \
  --to-revisions PREVIOUS_BACKEND_REVISION=100 \
  --project project001-489710 \
  --region asia-southeast1
```

Send traffic to the previous known-good frontend revision:

```bash
gcloud run services update-traffic projects-001-fe-beta \
  --to-revisions PREVIOUS_FRONTEND_REVISION=100 \
  --project project001-489710 \
  --region asia-southeast1
```

Do not casually roll back database schema after a migration. If a migration changed data or removed columns, stop and create a database recovery plan before taking action.

## Current Known Decisions

- Production beta uses a separate Cloud SQL instance: `project-001-beta`.
- Production beta uses Firestore database `prod-beta`.
- Production beta uses Identity Platform tenant `beta-company-001-bswmk`.
- Production beta currently uses `backend-runtime@project001-489710.iam.gserviceaccount.com` because organization policy blocks new service account creation.
- FlowAccount remains disabled for production beta until beta credentials are added.
- Demo remains as-is and is not rebuilt as part of beta setup.

