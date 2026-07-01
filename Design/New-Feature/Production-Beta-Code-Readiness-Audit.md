# Production Beta Code Readiness Audit

Audit date: 2026-06-30

This audit maps the current codebase against the production beta environment plan.

Implementation update: the code-side environment/tenant separation changes were implemented on 2026-06-30. Production beta GCP data resources were created on 2026-06-30 and beta Cloud Run smoke tests passed on 2026-07-01; see `Design/New-Feature/Production-Beta-Environment-Verification.md`.

## 1. Current Readiness Summary

| Area | Current status | Production beta readiness |
| --- | --- | --- |
| Backend database config | `DATABASE_URL` exists | Ready; `DATABASE_URL-beta` exists and beta schema is bootstrapped |
| Backend app env | `APP_ENV` exists | Ready; beta Cloud Run deploy verified |
| Backend GCS config | Bucket and prefix env vars exist | Ready; beta Cloud Run deploy verified |
| Backend Firestore config | `FIRESTORE_DATABASE_ID` supported | Ready; Firestore `prod-beta` exists |
| Backend Identity Platform tenant config | `IDENTITY_PLATFORM_TENANT_ID` supported | Ready; tenant ID is `beta-company-001-bswmk` |
| Backend Firebase ID token verification | Tenant check implemented when configured | Ready; runtime smoke test passed |
| Backend session token | Includes and enforces tenant/env when configured | Ready; runtime smoke test passed |
| Frontend API base URL | `VITE_API_BASE_URL` exists | Ready |
| Frontend Firebase config | Firebase web config exists | Ready |
| Frontend tenant selection | `VITE_IDENTITY_PLATFORM_TENANT_ID` supported | Ready; beta Cloud Run deploy verified |
| SQL migration process | SQL scripts exist, no formal migration runner | Beta schema bootstrapped; formal runner still recommended |

## 2. Confirmed Environment Values

Production beta Identity Platform tenant:

```text
Tenant display name: beta-company-001
Tenant resource: projects/678310400174/tenants/beta-company-001-bswmk
Tenant ID for app config: beta-company-001-bswmk
```

Initial production beta Owners:

```text
rayadee.ryd@gmail.com
paobansawang@gmail.com
```

## 3. Backend Findings

### 3.1 Config Layer

File: `Projects-001-BE/app/core/config.py`

Current support:

- `APP_ENV`
- `DATABASE_URL`
- `GCP_PROJECT_ID`
- `GCP_LOCATION`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_WEB_API_KEY`
- `FIREBASE_STORAGE_BUCKET`
- `GCS_BUCKET_NAME`
- `INSPECTION_GCS_BUCKET`
- `ADMIN_EMAILS`

Added for production beta:

- `FIRESTORE_DATABASE_ID`
- `IDENTITY_PLATFORM_TENANT_ID`

Implemented change:

```text
Add:
FIRESTORE_DATABASE_ID=(default)
IDENTITY_PLATFORM_TENANT_ID=
```

Acceptance criteria:

- Demo backend can keep using `(default)`.
- Production beta backend can use `prod-beta`.
- Production beta backend can require `beta-company-001-bswmk` for Firebase admin login tokens.

### 3.2 Firebase And Firestore Client Factory

File: `Projects-001-BE/app/core/google_clients.py`

Previous behavior:

- Firebase Admin app initializes with `projectId` and optional `storageBucket`.
- Firestore client is created with only `project=settings.firebase_project_id`.
- Firestore database ID is not configurable.

Implemented change:

```python
client_kwargs = {}
if settings.firebase_project_id:
    client_kwargs["project"] = settings.firebase_project_id
if settings.firestore_database_id:
    client_kwargs["database"] = settings.firestore_database_id
return firestore.Client(**client_kwargs)
```

Acceptance criteria:

- `FIRESTORE_DATABASE_ID=(default)` continues current demo behavior.
- `FIRESTORE_DATABASE_ID=prod-beta` directs all Firestore services to the production beta database.
- `identity_service.py` and `inspection_service.py` need no collection-level changes because both already call `get_firestore_client()`.

### 3.3 Auth Token Verification

File: `Projects-001-BE/app/api/v1/auth.py`

Previous behavior:

- Google admin login verifies `firebase_id_token` with `firebase_auth.verify_id_token(...)`.
- The decoded token email is used for local admin/subcontractor lookup.
- No tenant check is performed.

Implemented change:

- Add helper to validate decoded Firebase token tenant:

```text
expected_tenant = settings.identity_platform_tenant_id
actual_tenant = decoded.get("firebase", {}).get("tenant")
reject if expected_tenant is set and actual_tenant != expected_tenant
```

Acceptance criteria:

- Demo can run with `IDENTITY_PLATFORM_TENANT_ID=` and preserve current behavior.
- Production beta requires `IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk`.
- Token from demo/default auth is rejected by production beta backend.
- Token from production beta tenant is accepted only after normal role checks pass.

### 3.4 Session Token Claims

Files:

- `Projects-001-BE/app/core/security.py`
- `Projects-001-BE/app/api/deps/auth.py`
- `Projects-001-BE/app/schemas/profile_schema.py`

Previous behavior:

- Backend issues its own HMAC session token after Google/LINE login.
- Session token does not carry `tenant_id` or `app_env`.
- API dependencies trust the backend session token after verification.

Implemented change:

- Add optional `tenant_id` and `app_env` claims to issued session tokens.
- Add the same optional fields to `AuthenticatedUser` and `SessionUserPayload`.
- In production beta, reject backend session tokens whose `tenant_id` does not match `IDENTITY_PLATFORM_TENANT_ID`.

Why this matters:

- Firebase ID token tenant validation protects login.
- Session token tenant validation protects all subsequent API calls.

### 3.5 LINE Login Boundary

Files:

- `Projects-001-BE/app/api/v1/auth.py`
- `Projects-001-FE/src/liffClient.js`
- `Projects-001-FE/src/LoginPage.jsx`
- `Projects-001-FE/src/LineCallbackPage.jsx`

Current behavior:

- LINE login sends a LINE access token to the backend.
- Backend verifies the token by calling LINE profile API.
- This path does not use Firebase tenant sign-in.

Required production beta decision:

- Use separate LINE LIFF/channel config for production beta, or
- Add an environment-specific backend guard so production beta LINE sign-ins resolve only users stored in production beta Firestore.

Minimum safe implementation:

- Keep `LINE_CHANNEL_ID`, `LINE_CHANNEL_SECRET`, `LINE_LIFF_ID`, and `LINE_REDIRECT_URI` environment-specific.
- Since production beta Firestore is separate, LINE users from demo will not resolve unless copied, which should not happen.

### 3.6 GCS Storage

File: `Projects-001-BE/app/services/gcs_storage_service.py`

Current behavior:

- Main bucket is config-driven through `GCS_BUCKET_NAME`.
- Inspection bucket is config-driven through `INSPECTION_GCS_BUCKET`, falling back to `GCS_BUCKET_NAME`.
- Prefixes are config-driven.

Production beta readiness:

- Mostly ready.

Required deployment config:

```text
GCS_BUCKET_NAME=<prod-beta-main-bucket>
INSPECTION_GCS_BUCKET=<prod-beta-inspection-bucket or same main bucket>
GCS_KYC_PREFIX=kyc_id_cards
GCS_PROFILE_PREFIX=profile_images
GCS_TEMP_BILLS_PREFIX=temp_bills
GCS_PERM_BILLS_PREFIX=perm_bills
```

Recommended hardening:

- Avoid one bucket with mixed demo/prod objects.
- Use separate production beta buckets.
- Ensure service account IAM is bucket-scoped where possible.

### 3.7 SQL Schema And Migration

Current behavior:

- SQLAlchemy models exist.
- `scripts/create_missing_tables.py` can run `Base.metadata.create_all`.
- SQL migrations exist under `Projects-001-BE/scripts/migrations/`.
- No Alembic migration history was found.

Required before production beta go-live:

- Define the exact schema bootstrap command for the clean production beta database.
- Apply all SQL scripts in deterministic order.
- Do not run `seed_round1_data.py` against production beta.
- Create only required bootstrap records, such as initial Owner records.

Recommended minimum production beta bootstrap order:

```text
1. Create new Cloud SQL instance.
2. Create production beta database.
3. Run create_missing_tables.py or equivalent schema setup.
4. Run SQL migrations in chronological order.
5. Verify expected tables/columns.
6. Create initial Owner records only.
```

## 4. Frontend Findings

### 4.1 API Base URL

File: `Projects-001-FE/src/api.js`

Current behavior:

- `VITE_API_BASE_URL` controls backend URL.
- API requests attach the backend session token.

Production beta readiness:

- Ready.

Required deployment config:

```text
VITE_API_BASE_URL=https://<prod-beta-backend-cloud-run-url>
```

### 4.2 Firebase Client

File: `Projects-001-FE/src/firebaseClient.js`

Current behavior:

- Firebase app uses `VITE_FIREBASE_*` config.
- `getAuth(firebaseApp)` is used.
- Google sign-in uses popup provider.
- No tenant ID is assigned to the auth instance.

Implemented change:

```javascript
const identityPlatformTenantId = import.meta.env.VITE_IDENTITY_PLATFORM_TENANT_ID;
if (identityPlatformTenantId) {
  firebaseAuth.tenantId = identityPlatformTenantId;
}
```

Acceptance criteria:

- Demo can run with empty `VITE_IDENTITY_PLATFORM_TENANT_ID`.
- Production beta uses `VITE_IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk`.
- Google popup produces tenant-scoped Firebase ID tokens for production beta.

### 4.3 Frontend Env Example

File: `Projects-001-FE/.env.example`

Required additions:

```text
VITE_APP_ENV=demo
VITE_IDENTITY_PLATFORM_TENANT_ID=
```

Optional:

```text
VITE_ENVIRONMENT_LABEL=Demo
```

### 4.4 Demo Visual Safety

Current behavior:

- No explicit environment banner was found.

Recommended later:

- Show a small demo-only marker when `VITE_APP_ENV=demo`.
- Do not show the marker in production beta.

This is useful but not required before the backend tenant boundary is implemented.

## 5. Completed Code Change Order

Implemented in this order:

1. Backend config keys:
   - `FIRESTORE_DATABASE_ID`
   - `IDENTITY_PLATFORM_TENANT_ID`
2. Backend Firestore named database support in `get_firestore_client()`.
3. Backend Firebase tenant validation during `admin-login`.
4. Backend session token tenant/env claims and enforcement.
5. Frontend `VITE_IDENTITY_PLATFORM_TENANT_ID` support in `firebaseClient.js`.
6. Env examples for backend and frontend.

## 6. GCP Resource Work

Completed on 2026-06-30:

1. Created Cloud SQL instance `project-001-beta`.
2. Created database `project-001-beta` and user `app_prod_beta_user`.
3. Created and populated `DATABASE_URL-beta` with the latest beta DB connection string.
4. Enabled the PostgreSQL `vector` extension.
5. Bootstrapped schema with zero rows in `projects` and `input_requests`.
6. Created Firestore database `prod-beta`.
7. Created production beta GCS buckets.
8. Created production beta Secret Manager placeholders.
9. Enabled Google sign-in for Identity Platform tenant `beta-company-001-bswmk`.
10. Added expected beta frontend Cloud Run domains to Identity Platform authorized domains.

Current limitations:

1. Add beta FlowAccount secret values if FlowAccount is enabled.
2. Resolve org-policy blocker for dedicated beta service accounts, or continue with the agreed `backend-runtime` fallback.
3. Add a formal migration runner before the platform moves beyond beta.

## 7. Release Safety Gates

Maintain these checks before each production beta release:

- `projects-001-be` demo continues to use current resources.
- New production beta backend uses `FIRESTORE_DATABASE_ID=prod-beta`.
- New production beta backend uses `IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk`.
- Production beta frontend uses `VITE_IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk`.
- Demo Firebase token is rejected by production beta backend.
- Production beta tenant token is accepted by production beta backend.
- Production beta Firestore starts with no demo documents.
- Production beta PostgreSQL starts with schema and zero business rows.
- Production beta GCS buckets start empty.
- `project-001-saas` is not attached to production beta Cloud Run.

## 8. Risks

- Current backend Cloud Run demo service is attached to excluded `project-001-saas`; do not copy that setting to production beta.
- Current backend service account has broad project-level roles such as `storage.objectAdmin` and `secretmanager.secretAccessor`; production beta should use a separate service account and narrower IAM if org policy allows it.
- New service account creation is currently blocked by org policy `constraints/iam.disableServiceAccountCreation`.
- Firestore named database support is deployed; continue verifying that writes land in `prod-beta` during each smoke test.
- Custom Firebase tokens for LINE users are generated but not consumed by the frontend today. Environment separation for LINE depends mostly on separate LIFF/channel config plus separate Firestore data.
- No formal migration runner exists. Production beta bootstrap needs a controlled manual or scripted schema process.

## 9. Recommended Next Task

Use `Design/New-Feature/Production-Beta-Release-Runbook.md` and `Design/New-Feature/Environment-Sync-Checklist.md` for every release, then continue beta onboarding with controlled production data only.
