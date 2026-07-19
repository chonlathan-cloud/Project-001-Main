# Daily Report Phase 8 Hardening Runbook

Last updated: 2026-07-19  
GCP project: `project001-489710`  
Beta backend: `projects-001-be-beta`  
Firestore database: `prod-beta`  
Daily Report bucket: `project001-489710-daily-reports-beta`

## 1. Implemented controls

### Application

- Privacy-safe JSON logs with request IDs, route, status, duration, safe entity identifiers, and error category.
- No access tokens, LINE IDs, group IDs, signed URLs, contact details, KYC data, or report content in the new structured logs.
- Per-instance fixed-window limits for:
  - LINE/Admin authentication: 20 requests per minute.
  - Daily Report media uploads: 30 requests per minute.
  - Customer questions: 10 requests per minute.
  - Customer LINE webhook: 180 requests per minute.
- `429` responses include `Retry-After`, `X-RateLimit-Limit`, and `X-RateLimit-Remaining`.
- Upload bodies are read in bounded chunks and rejected immediately after the configured size limit.
- Media MIME types and file signatures are checked for supported mobile image, video, and voice formats.
- Generic authentication failure responses no longer expose internal exception text.
- Project failures create project-scoped Admin/Owner notifications.
- Global Scheduler failures create notifications visible to every active Admin and Owner.
- API responses include request ID, no-sniff, referrer, permissions-policy, and no-store headers.

The rate limiter is defense in depth for beta. Its counters are per Cloud Run instance. For stronger distributed production limits, place the service behind an external Application Load Balancer with Cloud Armor or add a shared Redis counter.

### Firestore

- `prod-beta` has point-in-time recovery enabled.
- `prod-beta` has delete protection enabled.
- Composite indexes are defined in `Projects-001-BE/infra/gcp/firestore.indexes.json`.
- The deployment helper creates indexes only in `prod-beta`.

### Cloud Storage

- Autoclass is enabled with `ARCHIVE` as the terminal storage class.
- Soft delete remains 7 days.
- Public access prevention is enforced.
- Uniform bucket-level access is enabled.
- Labels remain `app=project-001` and `env=prod-beta`.
- The only lifecycle rule aborts incomplete multipart uploads after 7 days.
- Valid Daily Report evidence has no deletion lifecycle and is retained indefinitely.

### Monitoring

These log-based metrics are configured:

- `daily_report_scheduler_failures`
- `daily_report_line_delivery_failures`
- `daily_report_subcontractor_notification_failures`
- `daily_report_upload_failures`
- `daily_report_webhook_signature_rejections`
- `daily_report_rate_limit_rejections`
- `daily_report_server_errors`

Email alert policies require the shared monitoring email:

```bash
cd Projects-001-BE
ALERT_EMAIL=monitoring@example.com ./scripts/configure_daily_report_monitoring.sh
```

The command creates or reuses the `RAYADEE Daily Report Operations` email channel and routes Scheduler, LINE delivery, subcontractor-notification, upload, webhook-spike, rate-limit-spike, and server-error policies to it.

## 2. Backend deployment configuration

Add these non-secret values to the beta backend:

```text
LOG_LEVEL=INFO
RATE_LIMIT_ENABLED=true
RATE_LIMIT_AUTH_PER_MINUTE=20
RATE_LIMIT_UPLOAD_PER_MINUTE=30
RATE_LIMIT_QUESTION_PER_MINUTE=10
RATE_LIMIT_WEBHOOK_PER_MINUTE=180
```

Deploy the normal beta backend revision after its LINE, Scheduler, Firestore, GCS, database, and authentication secret references are present. Do not place secret payloads in an env YAML file.

## 3. Least-privilege IAM

Current audit finding:

- `projects-001-be`, `projects-001-be-beta`, and `projects-001-fe-beta` share `backend-runtime@project001-489710.iam.gserviceaccount.com`.
- The intended `backend-runtime-beta@project001-489710.iam.gserviceaccount.com` identity does not yet exist.
- That shared identity currently has broad project-level roles including `roles/storage.objectAdmin`, `roles/secretmanager.secretAccessor`, `roles/iam.serviceAccountUser`, `roles/iam.serviceAccountTokenCreator`, Firestore service-agent, and Firestore reliability-admin roles.
- Removing those roles now can break the demo, beta backend, beta frontend, and unrelated features at the same time.

Safe migration:

1. Create or obtain approval for `backend-runtime-beta`.
2. Pass every beta backend Secret Manager reference through `SECRET_NAMES`.
3. Run:

```bash
cd Projects-001-BE
SECRET_NAMES=secret-a,secret-b,secret-c \
  ./scripts/configure_daily_report_beta_iam.sh
```

4. Test authentication, profile/KYC, bills, inspection, AI, Daily Report upload, signed media, publish, LINE delivery, and Scheduler.
5. Give `projects-001-fe-beta` a frontend-only identity with no backend data roles.
6. Only after both services are migrated and tested, remove unused broad roles from the old shared identity.

The helper refuses to switch identities when `SECRET_NAMES` is empty and never reads secret values.

## 4. Phase 8 verification

### Automated

```bash
cd Projects-001-BE
python -m unittest discover -s tests
python -m compileall app tests
```

```bash
cd Projects-001-FE
npm run lint
npm run build
```

### Manual beta regression

1. Sign in as Owner, Admin, subcontractor, and customer.
2. Confirm pending and rejected first-time accounts cannot access protected pages.
3. Upload valid JPEG, PNG, HEIC, mobile video, and voice evidence.
4. Confirm spoofed or oversized media is rejected without creating a media record.
5. Submit, review, request changes, resubmit, publish, and open the customer report from LINE.
6. Confirm customers see only published project data and signed media expires.
7. Retry one failed LINE delivery and confirm the project Admin/Owner sees the failure alert.
8. Trigger a safe beta Scheduler failure and confirm:
   - a global Admin/Owner notification is visible;
   - the log contains a request ID and error category;
   - the monitoring email receives the incident.
9. Exceed one test rate limit and confirm `429` plus `Retry-After`.
10. Confirm the mobile/accessibility behavior accepted in the previous E2E test remains unchanged.

## 5. Rollback

- Application: redeploy the prior beta revision.
- Rate limits only: set `RATE_LIMIT_ENABLED=false` and redeploy.
- Monitoring: disable the affected alert policy; do not delete incident history during diagnosis.
- Firestore indexes: leave them during application rollback; they do not change stored data.
- GCS lifecycle: remove the incomplete-multipart rule only if upload tooling proves incompatible.
- Autoclass: it can be disabled, but existing storage-class transitions are not reversed immediately.
- Never disable soft delete, public access prevention, or Firestore delete protection as a routine rollback.

## 6. Phase 8 exit evidence

Phase 8 is complete only when:

- the new backend revision passes the beta end-to-end flow;
- every Firestore index reports `READY`;
- the monitoring email channel is verified and a test incident is received;
- the beta backend no longer depends on the shared over-privileged runtime identity;
- no critical authorization, privacy, upload-recovery, or LINE-delivery issue remains.
