# Production Beta Environment Action Plan

This plan defines how to keep the current GCP setup as the demo/sandbox environment while adding a clean production beta environment for the first real company inside the same GCP project.

Related implementation readiness document:

- `Design/New-Feature/Production-Beta-Code-Readiness-Audit.md`

## 1. Confirmed Direction

- Use the current GCP resources as-is for the demo environment.
- Create new isolated production beta resources inside the same GCP project: `project001-489710`.
- Production beta starts with zero business data.
- Demo keeps test data and prospect trial data.
- Demo and production beta must stay identical for code, schema, infrastructure pattern, and configuration shape.
- Demo and production beta must not share customer data, demo data, uploaded files, secrets, or auth users.
- Use Identity Platform multi-tenancy for auth separation.
- Treat the beta company as the first production tenant, not as hardcoded special logic.

## 2. Environment Model

```text
project001-489710
  demo
    current Cloud Run services
    current PostgreSQL setup
    current Firestore database
    current GCS buckets
    current secrets
    current auth users

  prod-beta
    new Cloud Run services
    new PostgreSQL database or instance
    new Firestore database
    new GCS buckets
    new secrets
    new Identity Platform tenant
    new service accounts
```

Core rule:

```text
Same code + same schema + same deploy artifact
Different data + different secrets + different service accounts + different auth tenants
```

## 3. Proposed Resource Naming

| Resource Type | Demo | Production Beta |
| --- | --- | --- |
| Environment key | `demo` | `prod-beta` |
| Backend Cloud Run | current backend service | `project001-prod-beta-be` |
| Frontend Cloud Run | current frontend service | `project001-prod-beta-fe` |
| Backend service account | current service account | `project001-prod-beta-be-sa` |
| Frontend service account | current service account | `project001-prod-beta-fe-sa` |
| PostgreSQL | current DB/data | `project001_prod_beta` database or separate instance |
| PostgreSQL user | current user | `app_prod_beta_user` |
| Firestore database | current database, likely `(default)` | `prod-beta` |
| GCS bucket | current bucket(s) | `project001-prod-beta-private-assets` |
| Secret prefix | current names | `prod-beta-*` |
| Identity Platform tenant | demo/current auth context | `beta-company-001` |
| Public URL | current demo URL | beta company URL |

Do not rename or rebuild current demo resources during the first implementation phase. Add labels later if needed.

## 4. Target Architecture

```text
React Frontend
  -> Environment-specific API base URL
  -> Identity Platform tenant selection

FastAPI Backend
  -> Verifies auth token and tenant context
  -> Connects to environment-specific PostgreSQL
  -> Connects to environment-specific Firestore database
  -> Uses environment-specific GCS bucket
  -> Uses environment-specific Secret Manager values

GCP Project: project001-489710
  -> Shared project boundary
  -> Separate resources and IAM identities per environment
```

The backend remains the gateway for Firestore and GCS. The frontend must not directly access Firestore, GCS, or service account credentials.

## 5. Identity Platform Multi-Tenancy Plan

Use Identity Platform tenants to separate auth users.

Initial tenants:

| Tenant | Purpose |
| --- | --- |
| `demo` or current auth context | Demo users and prospect trial users |
| `beta-company-001` | First real beta company |

Implementation requirements:

- Enable Identity Platform multi-tenancy in the project if it is not already enabled.
- Create a production beta tenant for the first company.
- Configure login providers for the production beta tenant.
- Ensure frontend auth code selects the correct tenant before sign-in.
- Ensure backend token verification validates the expected tenant.
- Store environment and tenant IDs in config, not hardcoded business logic.
- Reject requests where the token tenant does not match the backend environment.

Recommended backend config keys:

```text
APP_ENV=demo|prod-beta
IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk
FIREBASE_PROJECT_ID=project001-489710
```

Recommended frontend config keys:

```text
VITE_APP_ENV=demo|prod-beta
VITE_API_BASE_URL=https://...
VITE_IDENTITY_PLATFORM_TENANT_ID=beta-company-001-bswmk
```

Reference docs:

- Identity Platform multi-tenancy: https://cloud.google.com/identity-platform/docs/multi-tenancy-quickstart
- Tenant authentication: https://cloud.google.com/identity-platform/docs/multi-tenancy-authentication

## 6. Data Isolation Plan

### 6.1 PostgreSQL

Preferred for production beta:

```text
Separate Cloud SQL instance:
  demo: current instance
  prod-beta: new production beta instance
```

Lower-cost beta option:

```text
Same Cloud SQL instance:
  demo: current database
  prod-beta: new database `project001_prod_beta`
  prod-beta DB user: `app_prod_beta_user`
```

Minimum requirements:

- Production beta uses a separate database.
- Production beta uses a separate database user.
- Demo credentials cannot access the production beta database.
- Production beta credentials cannot access demo data.
- Migrations run against both environments using the same migration version.
- Demo seed data never runs against production beta.

### 6.2 Firestore

Use separate Firestore databases if the application and SDK usage support named databases.

```text
demo: current database, likely `(default)`
prod-beta: `prod-beta`
```

Required code capability:

```text
FIRESTORE_DATABASE_ID=(default)|prod-beta
```

If the current backend always connects to `(default)`, add a config-driven Firestore client factory before creating the production beta database dependency.

Reference docs:

- Firestore database management: https://cloud.google.com/firestore/docs/manage-databases

### 6.3 Cloud Storage

Create production beta private buckets or at minimum a fully separated bucket namespace.

Recommended:

```text
project001-prod-beta-private-assets
project001-prod-beta-temp-assets
```

Minimum requirements:

- Bucket is private.
- Backend service account can read/write only the production beta bucket.
- Signed URLs are generated only by the backend.
- Demo and production beta object paths do not overlap.
- Lifecycle rules for temporary files are configured separately.

### 6.4 Secret Manager

Use environment-specific secrets.

Example:

```text
prod-beta-database-url
prod-beta-firebase-service-account-json
prod-beta-gcs-private-bucket-name
prod-beta-line-channel-id
prod-beta-line-channel-secret
prod-beta-gemini-api-key
```

Rules:

- Do not share demo secrets with production beta.
- Do not print secret payloads in logs.
- Cloud Run services should reference secrets by name/version.
- Prefer explicit secret names over generic names when both environments are in the same project.

## 7. Backend Development Work

### 7.1 Configuration Layer

Add or confirm config support for:

```text
APP_ENV
DATABASE_URL
FIRESTORE_DATABASE_ID
GCS_PRIVATE_BUCKET_NAME
IDENTITY_PLATFORM_TENANT_ID
FIREBASE_PROJECT_ID
```

Acceptance criteria:

- Backend can start in demo mode using current resources.
- Backend can start in prod-beta mode using only production beta resources.
- No environment-specific resource name is hardcoded in services.
- Logs show environment name, but never secret values.

### 7.2 Auth And Tenant Enforcement

Add tenant-aware auth validation.

Required behavior:

- Every authenticated request resolves:
  - `user_id`
  - `email` or LINE identity where applicable
  - `tenant_id`
  - internal role
  - company/tenant context
- Backend rejects a request if token tenant does not match `IDENTITY_PLATFORM_TENANT_ID`.
- Owner/Admin role checks still come from the existing authorization model.
- Production beta tenant starts with one initial Owner.
- Demo users cannot authenticate into production beta.
- Production beta users cannot authenticate into demo unless intentionally created there.

### 7.3 Firestore Client Factory

Add a single backend helper for Firestore client creation.

Required behavior:

- Reads `FIRESTORE_DATABASE_ID`.
- Defaults to `(default)` only when explicitly configured or in local demo mode.
- Allows production beta to use `prod-beta`.
- All Firestore services use this helper.

### 7.4 Storage Service Configuration

Confirm all file operations use a config-driven bucket name.

Required behavior:

- KYC files, receipts, profile images, inspection files, and generated assets use the environment-specific bucket.
- Signed URL generation uses the current backend service account.
- No frontend direct bucket access.

### 7.5 Database Migration Discipline

If migrations are not currently formalized, add a migration process before production beta launch.

Required behavior:

- Demo and production beta show the same schema revision.
- Migrations are applied to demo first.
- Production beta receives the exact same migration after demo smoke tests pass.
- Seed scripts are guarded by environment.
- Production beta bootstrap script creates only required initial records.

## 8. Frontend Development Work

### 8.1 Environment Config

Add or confirm frontend env support:

```text
VITE_APP_ENV
VITE_API_BASE_URL
VITE_IDENTITY_PLATFORM_TENANT_ID
```

Acceptance criteria:

- Demo frontend points to demo backend.
- Production beta frontend points to production beta backend.
- Frontend selects the correct Identity Platform tenant before sign-in.
- The UI does not need separate code branches for demo vs production beta.

### 8.2 Visual Environment Safety

Add a clear non-production indicator only in demo.

Examples:

```text
Demo
Sandbox
Test Data
```

Production beta should not show a demo banner. This reduces the chance of testers confusing demo data with real company data.

## 9. GCP Setup Work

### Phase 1: Inventory Current Demo

- Record current Cloud Run service names.
- Record current Cloud SQL instance/database/user names.
- Record current Firestore database ID.
- Record current GCS buckets.
- Record current Secret Manager secret names.
- Record current service accounts.
- Record current frontend/backend URLs.
- Mark all current resources as demo in the documentation.

No rebuild is required in this phase.

### Phase 2: Create Production Beta Resources

- Create production beta backend Cloud Run service.
- Create production beta frontend Cloud Run service.
- Create production beta backend service account.
- Create production beta frontend service account if needed.
- Create production beta PostgreSQL database or instance.
- Create production beta database user.
- Create production beta Firestore database `prod-beta`.
- Create production beta private GCS bucket(s).
- Create production beta Secret Manager secrets.
- Use Identity Platform tenant `beta-company-001`.
- Configure login providers for the production beta tenant.
- Grant least-privilege IAM to production beta service accounts.

### Phase 3: Deploy Same Version To Both Environments

Build once:

```text
backend image: git SHA or immutable digest
frontend image: git SHA or immutable digest
```

Promote the same build:

```text
deploy to demo
run demo smoke tests
deploy same image digest to prod-beta
run prod-beta smoke tests
```

Do not rebuild separately for production beta.

### Phase 4: Bootstrap Production Beta

- Run migrations on production beta.
- Create initial company profile if required by the app.
- Create initial Owner user for the beta company.
- Configure required integrations.
- Confirm production beta has zero demo/test business records.
- Confirm production beta storage bucket has no demo files.
- Confirm production beta Firestore database has no demo documents.

## 10. Deployment And Sync Policy

Every release should follow this sequence:

```text
1. Merge code to main.
2. Build backend and frontend images once.
3. Apply database migration to demo.
4. Deploy exact image digest to demo.
5. Run demo smoke tests.
6. Apply same database migration to prod-beta.
7. Deploy same image digest to prod-beta.
8. Run prod-beta smoke tests.
9. Record release version and migration revision.
```

Version parity requirements:

- Same Git commit.
- Same container image digest.
- Same API contract.
- Same database migration revision.
- Same frontend build version.
- Same feature flag defaults unless intentionally overridden.

## 11. Safety Gates

Before production beta launch:

- Demo and production beta Cloud Run services use different URLs.
- Demo and production beta services use different service accounts.
- Demo backend cannot access production beta DB.
- Production beta backend cannot access demo DB.
- Demo backend cannot access production beta GCS buckets.
- Production beta backend cannot access demo GCS buckets.
- Production beta auth token includes the expected tenant.
- Backend rejects mismatched tenant tokens.
- Production beta starts with no demo business records.
- Production beta secrets are not shared with demo.
- Smoke tests pass in both environments.

## 12. Smoke Test Checklist

Demo:

- Login as demo Owner/Admin.
- Open Dashboard if role permits.
- Open Project list.
- Open Approval queue.
- Upload a test receipt or test file.
- Verify signed URL preview.
- Verify test data remains visible.

Production beta:

- Login as production beta Owner.
- Confirm zero or bootstrap-only data.
- Create first project if allowed.
- Create or view subcontractor profile flow if allowed.
- Upload a controlled test file, then delete it if the feature supports deletion.
- Verify Firestore writes land in `prod-beta`.
- Verify PostgreSQL writes land in production beta database.
- Verify GCS objects land in production beta bucket.
- Verify demo user cannot access production beta.

## 13. Future SaaS Readiness

This setup should avoid hardcoding the first company as a special case.

Design direction:

```text
environment = demo | prod-beta | saas-prod
tenant_id = company/customer boundary
company_id = business entity inside the tenant
```

When the official SaaS launch comes later, the production model can evolve from:

```text
one production beta tenant
```

to:

```text
many SaaS tenants
```

without rewriting the auth and environment boundaries.

## 14. Development Task Order

1. Document current demo resource inventory.
2. Add backend environment config keys.
3. Add tenant-aware backend auth verification.
4. Add Firestore database ID config support.
5. Confirm GCS bucket config is fully environment-driven.
6. Add frontend tenant/env config.
7. Create production beta GCP resources.
8. Configure production beta Identity Platform tenant.
9. Configure production beta secrets and IAM.
10. Deploy demo using current resources.
11. Deploy production beta using new resources.
12. Run smoke tests and record release parity.

## 15. Open Decisions

- Whether production beta PostgreSQL should use a new Cloud SQL instance or a new database on the current instance.
- Whether the current demo auth context should stay as-is or be migrated into a dedicated `demo` Identity Platform tenant.
- Final production beta domain name.
- Initial Owner account for the beta company.
- Whether production beta should allow any demo-like seed data, or only real bootstrap records.

Recommended default answers:

- Use a separate production beta Cloud SQL instance if budget allows.
- Keep current demo auth as-is during phase 1 to avoid disruption.
- Use dedicated production beta tenant `beta-company-001`.
- Use zero demo seed data in production beta.
