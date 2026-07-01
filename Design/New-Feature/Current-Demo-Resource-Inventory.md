# Current Demo Resource Inventory

Inventory date: 2026-06-30

This document records the current read-only GCP inventory for `project001-489710`. Treat the current resources as the demo/sandbox environment for the production beta rollout.

No secret payloads, database data, object contents, or signed URLs were read.

## 1. Project

| Field | Value |
| --- | --- |
| Project ID | `project001-489710` |
| Project number | `678310400174` |
| Display name | `Project001` |
| Lifecycle state | `ACTIVE` |
| Firebase label | `enabled` |
| Default region used by active services | `asia-southeast1` |

## 2. Cloud Run

### 2.1 Current Demo Services

| Service | Region | URL | Latest ready revision | Service account |
| --- | --- | --- | --- | --- |
| `projects-001-be` | `asia-southeast1` | `https://projects-001-be-678310400174.asia-southeast1.run.app` | `projects-001-be-00087-qvb` | `backend-runtime@project001-489710.iam.gserviceaccount.com` |
| `projects-001-fe` | `asia-southeast1` | `https://projects-001-fe-678310400174.asia-southeast1.run.app` | `projects-001-fe-00014-jjh` | `678310400174-compute@developer.gserviceaccount.com` |

Backend service notes:

- `projects-001-be` has `maxScale=3`.
- `projects-001-be` is attached to these Cloud SQL instances:
  - `project001-489710:asia-southeast1:project-001`
  - `project001-489710:asia-southeast1:project-001-saas`
- `project-001` is the current demo database candidate.
- `project-001-saas` is excluded SaaS context and should not be carried into the production beta environment for this repository.

Frontend service notes:

- `projects-001-fe` has `maxScale=3`.
- `projects-001-fe` currently uses the Compute Engine default service account.

### 2.2 Excluded SaaS Services

These services exist in the project but are not part of this repository's architecture according to the project boundary decision.

| Service | Region | URL | Latest ready revision | Service account |
| --- | --- | --- | --- | --- |
| `project-saas-001-be` | `asia-southeast1` | `https://project-saas-001-be-678310400174.asia-southeast1.run.app` | `project-saas-001-be-00013-psk` | `backend-runtime@project001-489710.iam.gserviceaccount.com` |
| `project-saas-001-fe` | `asia-southeast1` | `https://project-saas-001-fe-678310400174.asia-southeast1.run.app` | `project-saas-001-fe-00003-f2s` | `backend-runtime@project001-489710.iam.gserviceaccount.com` |

## 3. Cloud SQL

### 3.1 Instances

| Instance | Version | Region | State | Tier | Availability |
| --- | --- | --- | --- | --- | --- |
| `project-001` | `POSTGRES_18` | `asia-southeast1` | `RUNNABLE` | `db-custom-1-3840` | `ZONAL` |
| `project-001-saas` | `POSTGRES_18` | `asia-southeast1` | `STOPPED` | `db-custom-1-3840` | `REGIONAL` |
| `project-001-saas-restore-test` | `POSTGRES_18` | `asia-southeast1` | `STOPPED` | `db-custom-1-3840` | `ZONAL` |

Use `project-001` as the current demo Cloud SQL instance for this repository.

Treat `project-001-saas` and `project-001-saas-restore-test` as excluded SaaS context unless the user explicitly redirects.

### 3.2 Current Demo Databases

Instance: `project-001`

| Database | Charset | Collation |
| --- | --- | --- |
| `postgres` | `UTF8` | `en_US.UTF8` |
| `project-001` | `UTF8` | `en_US.UTF8` |

### 3.3 Current Demo Users

Instance: `project-001`

| User | Type |
| --- | --- |
| `Test` | `BUILT_IN` |
| `postgres` | `BUILT_IN` |

No database passwords or connection strings were read.

## 4. Firestore

| Database | Location | Type | Delete protection | PITR |
| --- | --- | --- | --- | --- |
| `(default)` | `asia-southeast1` | `FIRESTORE_NATIVE` | `DELETE_PROTECTION_DISABLED` | `POINT_IN_TIME_RECOVERY_DISABLED` |

Recommendation for production beta:

- Keep `(default)` as the current demo database for now.
- Create a new named Firestore database: `prod-beta`.
- Add backend config support for `FIRESTORE_DATABASE_ID`.

## 5. Cloud Storage

| Bucket | Location | Type | Public access prevention | Uniform bucket-level access |
| --- | --- | --- | --- | --- |
| `kyc_id_cards` | `ASIA-SOUTHEAST1` | `region` | `enforced` | `True` |
| `perm_bills` | `ASIA-SOUTHEAST3` | `region` | `enforced` | `True` |
| `project001-489710-work-inspection` | `ASIA-SOUTHEAST3` | `region` | `enforced` | `True` |
| `temp_bills` | `ASIA-SOUTHEAST1` | `region` | `enforced` | `True` |

Recommendation for production beta:

- Create matching buckets with `-beta` suffix where valid.
- Keep public access prevention enforced.
- Keep backend-only signed URL access.

## 6. Secret Manager

Secret metadata only:

| Secret | Created | Labels |
| --- | --- | --- |
| `ADMIN_EMAILS` | `2026-06-16T06:11:52` | none shown |
| `DATABASE_URL` | `2026-03-18T08:39:47` | none shown |
| `FIREBASE_WEB_API_KEY` | `2026-06-16T06:08:20` | none shown |
| `FLOWACCOUNT_CLIENT_ID` | `2026-06-23T07:27:58` | none shown |
| `FLOWACCOUNT_CLIENT_SECRET` | `2026-06-23T07:28:04` | none shown |
| `JWT_SECRET_KEY` | `2026-06-16T06:09:27` | none shown |
| `LINE_CHANNEL_ID` | `2026-03-18T08:43:07` | none shown |
| `LINE_CHANNEL_SECRET` | `2026-03-18T08:44:07` | none shown |
| `LINE_LIFF_ID` | `2026-06-16T06:11:22` | none shown |
| `backend-runtime-sa-key` | `2026-05-01T08:01:29` | none shown |
| `projects001-staging-admin-emails` | `2026-06-12T12:04:06` | `env=staging`, `app=projects001` |
| `projects001-staging-database-url` | `2026-06-12T12:03:12` | `env=staging`, `app=projects001` |
| `projects001-staging-firebase-web-api-key` | `2026-06-12T12:03:22` | `env=staging`, `app=projects001` |
| `projects001-staging-jwt-secret-key` | `2026-06-12T12:03:57` | `env=staging`, `app=projects001` |
| `projects001-staging-line-channel-id` | `2026-06-12T12:03:31` | `env=staging`, `app=projects001` |
| `projects001-staging-line-channel-secret` | `2026-06-12T12:03:41` | `env=staging`, `app=projects001` |
| `projects001-staging-line-liff-id` | `2026-06-12T12:03:49` | `env=staging`, `app=projects001` |

No secret values were accessed.

Recommendation for production beta:

- Create `-beta` or `prod-beta-*` secret names through Google Cloud Console.
- Do not reuse current demo secret values unless the value is intentionally shared and safe, such as non-sensitive project ID.

## 7. Service Accounts

| Service account | Display name | Disabled |
| --- | --- | --- |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `backend-runtime` | `False` |
| `678310400174-compute@developer.gserviceaccount.com` | `Compute Engine default service account` | `False` |
| `firebase-adminsdk-fbsvc@project001-489710.iam.gserviceaccount.com` | `firebase-adminsdk` | `False` |

Relevant project-level IAM bindings found:

| Member | Role |
| --- | --- |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/aiplatform.user` |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/cloudsql.client` |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/cloudtasks.enqueuer` |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/datastore.user` |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/firestore.serviceAgent` |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/iam.serviceAccountTokenCreator` |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/iam.serviceAccountUser` |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/recommender.firestoredatabasereliabilityAdmin` |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/secretmanager.secretAccessor` |
| `backend-runtime@project001-489710.iam.gserviceaccount.com` | `roles/storage.objectAdmin` |
| `firebase-adminsdk-fbsvc@project001-489710.iam.gserviceaccount.com` | `roles/firebase.sdkAdminServiceAgent` |
| `firebase-adminsdk-fbsvc@project001-489710.iam.gserviceaccount.com` | `roles/firebaseauth.admin` |
| `firebase-adminsdk-fbsvc@project001-489710.iam.gserviceaccount.com` | `roles/iam.serviceAccountTokenCreator` |
| `firebase-adminsdk-fbsvc@project001-489710.iam.gserviceaccount.com` | `roles/secretmanager.admin` |

Recommendation for production beta:

- Create a separate backend service account, for example `backend-runtime-beta`.
- Grant only the roles needed for production beta resources.
- Avoid using the Compute Engine default service account for the production beta frontend.
- Avoid mounting service account key JSON if Workload Identity/Cloud Run service identity is sufficient.

## 8. Artifact Registry

Location: `asia-southeast1`

| Repository | Format | Mode | Size MB | Created | Updated |
| --- | --- | --- | --- | --- | --- |
| `preorder` | `DOCKER` | `STANDARD_REPOSITORY` | `1717.389` | `2026-03-29T14:12:28` | `2026-03-29T18:06:21` |
| `projects-001` | `DOCKER` | `STANDARD_REPOSITORY` | `2781.333` | `2026-04-30T13:20:21` | `2026-06-30T12:08:26` |

Recommendation for production beta:

- Reuse `projects-001` Artifact Registry repository.
- Build once and deploy the same image digest to demo and production beta.
- Avoid environment-specific image rebuilds.

## 9. BigQuery

No BigQuery datasets were listed by `bq ls --project_id=project001-489710`.

## 10. Vertex AI

Read-only checks in `asia-southeast1` returned:

- Models: none listed.
- Endpoints: none listed.

This does not block use of managed Gemini model names through Vertex AI.

## 11. Cloud Build

`gcloud builds list` could not complete because the Cloud Build API is disabled or unavailable for the active credential context. No API was enabled and no write action was taken.

## 12. Identity Platform / Firebase Auth

Current `gcloud` installation does not expose Identity Platform or Firebase project subcommands, so Identity Platform was checked through the read-only Identity Toolkit REST API with local `gcloud` authentication.

Sanitized project config:

| Field | Value |
| --- | --- |
| Config resource | `projects/678310400174/config` |
| Auth subtype | `IDENTITY_PLATFORM` |
| Email/password sign-in | `enabled` |
| Password required | `true` |
| MFA | `DISABLED` |
| Multi-tenant config | `allowTenants=true`, `defaultTenantLocation=organizations/176847691265` |

Authorized domains currently returned by the API:

- `localhost`
- `project001-489710.firebaseapp.com`
- `project001-489710.web.app`
- `127.0.0.1`
- `projects-001-fe-678310400174.asia-southeast1.run.app`
- `project-saas-001-fe-678310400174.asia-southeast1.run.app`

Tenant list returned:

| Tenant resource | Display name |
| --- | --- |
| `projects/678310400174/tenants/beta-company-001-bswmk` | `beta-company-001` |

Use tenant ID `beta-company-001-bswmk` in application configuration, because the API resource name includes the generated suffix.

The production beta plan should therefore proceed with manual verification in Google Cloud Console:

- Confirm Identity Platform is enabled.
- Confirm tenant support remains enabled.
- Confirm tenant `beta-company-001` exists.
- Configure the required login providers.

Agreed strategy:

- Keep current auth setup as the demo auth context for now.
- Use production beta tenant `beta-company-001`.

## 13. Production Beta Resource Targets

Based on user decisions:

| Area | Decision |
| --- | --- |
| Domain | Use default Cloud Run URLs, no custom domain for now |
| Initial Owners | `rayadee.ryd@gmail.com`, `paobansawang@gmail.com` |
| PostgreSQL | Create a separate Cloud SQL instance |
| Auth strategy | Keep current auth as demo; use production beta Identity Platform tenant `beta-company-001` |
| Login providers | Google, email/password, LINE, or final selected subset in Console |
| Naming | Same as demo where practical, with `-beta` suffix |
| Secrets | Create/manage in Google Cloud Console Secret Manager |
| Production beta data | Zero demo/test data, schema and bootstrap records only |

## 14. Open Follow-Up

- Decide exact production beta Cloud SQL instance name. Recommended: `project-001-beta`.
- Decide exact production beta PostgreSQL database name. Recommended: `project_001_beta`.
- Decide exact production beta service account names. Recommended:
  - `backend-runtime-beta`
  - `frontend-runtime-beta`
- Decide exact production beta bucket names. Recommended:
  - `kyc-id-cards-beta`
  - `perm-bills-beta`
  - `temp-bills-beta`
  - `project001-489710-work-inspection-beta`
- Confirm Identity Platform provider configuration for tenant `beta-company-001`.
- Confirm selected login providers for production beta.
