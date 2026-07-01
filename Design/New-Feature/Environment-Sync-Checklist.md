# Environment Sync Checklist

Last updated: 2026-07-01

Purpose: keep the demo environment and production beta environment identical in code, schema, and behavior while keeping their data and secrets isolated.

## Sync Principle

Use this rule for every release:

```text
Same code + same schema + same behavior
Different data + different secrets + different auth tenant + different storage
```

## Every Release Checklist

Before release:

- Record the Git commit.
- Confirm the release target includes both demo and production beta unless intentionally documented otherwise.
- Run frontend lint/build checks where applicable.
- Run backend startup or focused backend checks where applicable.
- Review database migrations before applying them.
- Confirm migrations are idempotent or have a clear rollback/recovery plan.
- Confirm demo seed scripts are not run against production beta.
- Confirm no real secrets or service account keys are staged in Git.

Deploy sequence:

1. Apply schema changes to demo.
2. Deploy demo backend.
3. Deploy demo frontend.
4. Run demo smoke tests.
5. Apply the same schema changes to production beta.
6. Deploy production beta backend.
7. Deploy production beta frontend.
8. Run production beta smoke tests.
9. Record the release result.

If demo smoke tests fail, do not continue to production beta until the failure is understood and fixed.

## Environment Parity Matrix

| Area | Demo expected value | Production beta expected value |
| --- | --- | --- |
| App environment | `demo` | `prod-beta` |
| Backend Cloud Run | `projects-001-be` | `projects-001-be-beta` |
| Frontend Cloud Run | `projects-001-fe` | `projects-001-fe-beta` |
| Firestore database | `(default)` | `prod-beta` |
| Identity tenant | Default/current auth context | `beta-company-001-bswmk` |
| Cloud SQL | Current demo database | `project-001-beta` |
| Main GCS bucket | Current demo bucket | `kyc_id_cards-beta` |
| Inspection GCS bucket | Current demo inspection bucket | `project001-489710-work-inspection-beta` |
| FlowAccount | Demo setting | `false` until beta credentials are configured |

## Config Isolation Checks

Production beta backend must use:

```text
APP_ENV=prod-beta
FIRESTORE_DATABASE_ID=prod-beta
IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk
GCS_BUCKET_NAME=kyc_id_cards-beta
INSPECTION_GCS_BUCKET=project001-489710-work-inspection-beta
FLOWACCOUNT_ENABLED=false
```

Production beta frontend must use:

```text
VITE_APP_ENV=prod-beta
VITE_IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk
VITE_API_BASE_URL=https://projects-001-be-beta-678310400174.asia-southeast1.run.app
```

Production beta Cloud Run must not reference:

- Demo Cloud SQL connections.
- Demo GCS buckets.
- Demo Secret Manager secrets.
- SaaS resources named `project-saas-001-be`, `project-saas-001-fe`, `project-001-saas`, or `project-001-saas-restore-test`.

## Data Isolation Checks

Demo:

- May contain test data and prospect trial data.
- May use demo seed data.
- Must not connect to production beta database, Firestore, or buckets.

Production beta:

- Starts with clean data.
- May contain only real beta company data and required bootstrap records.
- Must not contain demo seed records.
- Must not read or write demo Firestore, demo PostgreSQL, or demo GCS buckets.

## Smoke Test Checklist

Demo smoke test:

- Login as a demo Owner/Admin.
- Open the dashboard.
- Open project and approval flows.
- Upload a controlled demo file if upload behavior changed.
- Confirm demo test data remains available.
- Confirm no beta resources receive writes.

Production beta smoke test:

- Login as a production beta tenant user.
- Confirm beta tenant auth works.
- Confirm demo/default auth cannot access production beta.
- Confirm zero or bootstrap-only data before creating records.
- Open the main beta company workflow pages.
- Create a controlled test record only when appropriate.
- Confirm database writes land in `project-001-beta`.
- Confirm Firestore writes land in `prod-beta`.
- Confirm files land in beta GCS buckets.

## Release Log Template

Copy this block into the verification document for each release:

```text
Release date:
Git commit:
Backend service/revision:
Frontend service/revision:
Schema migration applied:
Demo smoke test result:
Production beta smoke test result:
Known issues:
Rollback revision:
Operator:
```

## Non-Negotiables

- Never run demo seed scripts against production beta.
- Never commit `.env` files, service account keys, or secret payloads.
- Never document secret payloads.
- Never attach production beta Cloud Run services to excluded SaaS resources.
- Never deploy a beta frontend that points to the demo backend.
- Never deploy a beta backend that accepts the wrong Identity Platform tenant.

