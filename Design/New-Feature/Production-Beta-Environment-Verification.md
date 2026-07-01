# Production Beta Environment Verification

Verification date: 2026-06-30

Project: `project001-489710`

No secret payloads were printed or recorded.

Related operational docs:

- `Design/New-Feature/Production-Beta-Release-Runbook.md`
- `Design/New-Feature/Environment-Sync-Checklist.md`

## Summary

The production beta data-plane resources now exist inside the same GCP project while the current demo resources remain unchanged.

Ready:

- Identity Platform tenant exists and Google sign-in is enabled for the tenant.
- Firestore `prod-beta` database exists.
- Cloud SQL `project-001-beta` instance exists and is runnable.
- Production beta database schema has been bootstrapped with zero business rows.
- Production beta GCS buckets exist.
- Production beta Secret Manager placeholders exist.
- Identity Platform authorized domains include the expected beta Cloud Run frontend domains.
- Production beta Cloud Run services are deployed and ready.

Known limitations:

- Dedicated beta service accounts could not be created because the project has org policy `constraints/iam.disableServiceAccountCreation`.
- Production beta FlowAccount secrets have no values yet; keep `FLOWACCOUNT_ENABLED=false` until they are set.
- Email/password auth is enabled in Identity Platform, but the current app UI only exposes Google and LINE login.

## Demo Environment

Current demo resources remain in place:

| Area | Demo resource |
| --- | --- |
| Backend Cloud Run | `projects-001-be` |
| Frontend Cloud Run | `projects-001-fe` |
| Cloud SQL | `project-001` |
| Firestore | `(default)` |
| Main GCS bucket | `kyc_id_cards` |
| Inspection GCS bucket | `project001-489710-work-inspection` |
| Auth context | Project/default Identity Platform context |

Excluded SaaS resources remain excluded from this project plan:

- Cloud Run: `project-saas-001-be`
- Cloud Run: `project-saas-001-fe`
- Cloud SQL: `project-001-saas`
- Cloud SQL: `project-001-saas-restore-test`

## Production Beta Resources

### Identity Platform

| Item | Status |
| --- | --- |
| Multi-tenancy | Enabled |
| Tenant display name | `beta-company-001` |
| Tenant ID | `beta-company-001-bswmk` |
| Google provider | Enabled for tenant |
| Authorized beta domains | Added |

Authorized beta domains added:

- `projects-001-fe-beta-678310400174.asia-southeast1.run.app`
- `projects-001-fe-beta-bsrqi3xjcq-as.a.run.app`

### Firestore

| Database | Location | Delete protection | PITR |
| --- | --- | --- | --- |
| `prod-beta` | `asia-southeast1` | Enabled | Enabled |

Backend config value:

```text
FIRESTORE_DATABASE_ID=prod-beta
```

### Cloud SQL

| Item | Value |
| --- | --- |
| Instance | `project-001-beta` |
| Connection name | `project001-489710:asia-southeast1:project-001-beta` |
| Version | `POSTGRES_18` |
| Region | `asia-southeast1` |
| State | `RUNNABLE` |
| Database | `project-001-beta` |
| App user | `app_prod_beta_user` |
| Backups | Enabled |
| PITR | Enabled |
| Deletion protection | Enabled |

Schema bootstrap result:

| Check | Result |
| --- | --- |
| `vector` extension | Enabled |
| Public tables | `8` |
| `projects` rows | `0` |
| `input_requests` rows | `0` |

`DATABASE_URL-beta` exists in Secret Manager and the latest version points to this beta database.

### Cloud Storage

| Bucket | Location | Public access prevention | Uniform access |
| --- | --- | --- | --- |
| `kyc_id_cards-beta` | `ASIA-SOUTHEAST1` | Enforced | Enabled |
| `temp_bills-beta` | `ASIA-SOUTHEAST1` | Enforced | Enabled |
| `perm_bills-beta` | `ASIA-SOUTHEAST3` | Enforced | Enabled |
| `project001-489710-work-inspection-beta` | `ASIA-SOUTHEAST3` | Enforced | Enabled |

Recommended backend deployment values:

```text
GCS_BUCKET_NAME=kyc_id_cards-beta
INSPECTION_GCS_BUCKET=project001-489710-work-inspection-beta
```

### Secret Manager

Beta secrets created:

| Secret | Version status |
| --- | --- |
| `DATABASE_URL-beta` | Has version |
| `FIREBASE_WEB_API_KEY-beta` | Has version |
| `JWT_SECRET_KEY-beta` | Has version |
| `ADMIN_EMAILS-beta` | Has version |
| `LINE_CHANNEL_ID-beta` | Has version |
| `LINE_CHANNEL_SECRET-beta` | Has version |
| `LINE_LIFF_ID-beta` | Has version |
| `FLOWACCOUNT_CLIENT_ID-beta` | Missing value |
| `FLOWACCOUNT_CLIENT_SECRET-beta` | Missing value |

Initial admin emails configured in `ADMIN_EMAILS-beta`:

```text
rayadee.ryd@gmail.com
paobansawang@gmail.com
```

### Cloud Run

Production beta Cloud Run services:

| Service | Target name |
| --- | --- |
| Backend | `projects-001-be-beta` |
| Frontend | `projects-001-fe-beta` |

Deployment verification:

| Service | URL | Revision | Ready |
| --- | --- | --- | --- |
| `projects-001-be-beta` | `https://projects-001-be-beta-678310400174.asia-southeast1.run.app` | `projects-001-be-beta-00001-dmw` | Yes |
| `projects-001-fe-beta` | `https://projects-001-fe-beta-678310400174.asia-southeast1.run.app` | `projects-001-fe-beta-00001-2fp` | Yes |

Expected backend config:

```text
APP_ENV=prod-beta
FIRESTORE_DATABASE_ID=prod-beta
IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk
GCS_BUCKET_NAME=kyc_id_cards-beta
INSPECTION_GCS_BUCKET=project001-489710-work-inspection-beta
FLOWACCOUNT_ENABLED=false
```

Expected frontend build config:

```text
VITE_APP_ENV=prod-beta
VITE_IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk
VITE_API_BASE_URL=https://projects-001-be-beta-678310400174.asia-southeast1.run.app
```

## Remaining Limitations

1. Resolve service account policy:
   - Preferred: allow creation of `backend-runtime-beta` and `frontend-runtime-beta`.
   - Current beta deployment uses the agreed temporary fallback: `backend-runtime@project001-489710.iam.gserviceaccount.com`.

2. Decide whether FlowAccount is enabled for beta:
   - If no, deploy with `FLOWACCOUNT_ENABLED=false`.
   - If yes, add `FLOWACCOUNT_CLIENT_ID-beta` and `FLOWACCOUNT_CLIENT_SECRET-beta`.

3. If email/password login is required for beta users, implement the app UI/API flow first. Identity Platform is enabled for email/password, but the current app only exposes Google and LINE sign-in.

## Post-Deploy Checks

Completed on 2026-07-01:

- Backend service is ready.
- Frontend service is ready.
- Backend service account is `backend-runtime@project001-489710.iam.gserviceaccount.com`.
- Backend is attached only to `project001-489710:asia-southeast1:project-001-beta`.
- Backend uses `APP_ENV=prod-beta`.
- Backend uses `FIRESTORE_DATABASE_ID=prod-beta`.
- Backend uses `IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk`.
- Backend uses beta GCS buckets.
- Backend uses beta Secret Manager references.
- Backend `/health` returned `{"status":"ok"}`.
- Frontend root URL returned HTTP 200.
- Unauthenticated `/api/v1/profile/me` returned HTTP 401.
- No Cloud Run ERROR logs were found for either beta service in the checked recent window.

## Smoke Test Result

Completed on 2026-07-01:

| Item | Result |
| --- | --- |
| Production beta smoke test | Passed |
| Reported by | User |
| Accounts tested | Not recorded |
| Flows tested | Not recorded |
| Notes | User reported the smoke test passed after deploying both beta Cloud Run services. |
