# Daily Report Feature Development Action Plan

This document is the implementation plan for the Daily Report feature based on:

- The interactive mockup in `mockup/`
- The confirmed subcontractor → Admin/Owner → customer workflow
- The existing RAYADEE authentication and project data
- The current Google Cloud infrastructure in project `project001-489710`
- The two LINE Official Accounts under the `RAYADEE LIMITED` provider

This is a planning document only. It does not implement the feature.

## 1. Product Objective

Create a controlled daily site-reporting workflow in which:

1. Each expected subcontractor submits a daily report for an assigned project.
2. RAYADEE combines the subcontractor submissions into one project-level report.
3. An Admin or Owner reviews the evidence and customer-facing content.
4. Only an Admin or Owner can approve and publish the report.
5. The customer receives a LINE summary through `RYD PROJECT CUSTOMER`.
6. The full report remains private behind a revocable project share link; customer login is not required.
7. Published versions are immutable and auditable.

The customer should receive one consolidated report per project and reporting date, not one message per subcontractor.

## 2. Confirmed Business Decisions

- Report structure: one consolidated customer report per project per day.
- Subcontractors submit separate source reports.
- Admin and Owner can review, request changes, edit the customer-facing draft, approve, and publish.
- Owner has access to every project.
- Admin access is limited to authorized projects.
- Subcontractors can access only their assigned projects and their own submissions.
- Anyone holding the active project share link can access only published customer-facing reports for that project.
- Customer acknowledgement is not contractual approval or work acceptance.
- Published reports are locked.
- Corrections create a new version and preserve previous versions.
- AI may prepare a draft but may never approve or publish.
- RAYADEE is the system of record.
- LINE OA is the customer messaging and share-link delivery gateway.
- The customer receives a LINE summary plus a revocable, login-free RAYADEE report link.
- Report deadlines and reminders are configurable per project.
- Default operational timezone is `Asia/Bangkok`.
- Automatic customer publishing is not allowed.

## 3. LINE Channel Decisions

### 3.1 Subcontractor gateway

LINE OA:

```text
RYD PROJECT ADMIN
```

Purpose:

- Open the subcontractor LIFF page from the Rich Menu
- Authenticate subcontractor LINE identities
- Send submission reminders and status notifications
- Link users to their own daily-report history

Recommended LIFF entry:

```text
https://liff.line.me/{SUBCONTRACTOR_LIFF_ID}/daily-reports/me
```

RAYADEE frontend route:

```text
/daily-reports/me
```

### 3.2 Customer gateway

LINE OA:

```text
RYD PROJECT CUSTOMER
```

Purpose:

- Send approved daily-report summaries to each project's LINE group
- Open the customer LIFF page from the Rich Menu
- Deliver the project-scoped report capability link to the bound LINE group
- Allow link holders to view published reports without creating an account

Recommended LIFF entry:

```text
https://{FRONTEND_HOST}/shared/project-reports#access={PROJECT_SHARE_TOKEN}
```

RAYADEE frontend route:

```text
/shared/project-reports
```

### 3.3 Internal Admin/Owner entry

Admins and Owners use the existing Google/Firebase authentication in the normal RAYADEE web app.

RAYADEE frontend route:

```text
/daily-reports
```

Admin and Owner do not use a LINE OA as the primary review interface.

### 3.4 Provider rule

Both LINE OAs and their related LINE Login/LIFF channels must remain under:

```text
RAYADEE LIMITED
```

The backend must still store the identity provider, LINE channel context, LINE user ID, RAYADEE account ID, roles, project memberships, and consent timestamps separately.

A shared provider-scoped LINE user ID must not automatically grant access across subcontractor and customer roles.

## 4. Scope

### 4.1 MVP scope

- First-time access request and approval for subcontractors
- First-time access request and approval for customers
- Existing first-time access request and approval for Admin/staff
- Project membership and authorization
- Per-project daily-report schedule settings
- Daily cycle creation
- Subcontractor draft and submission
- Photo upload
- Optional video and voice-note upload
- Work details, manpower, progress, issues, and tomorrow plan
- Change-request and resubmission workflow
- Consolidated project-level draft
- Optional AI drafting with deterministic fallback
- Admin/Owner evidence review
- Customer-facing content editing
- Admin/Owner approval and publication
- Immutable report versions
- Customer LINE Flex Message summary
- Authenticated customer report page
- Customer acknowledgement
- Report-linked customer questions
- Reminder, overdue, publication, and delivery notifications
- Audit trail
- Production/beta environment separation

### 4.2 Out of scope for MVP

- Customer AI free-form Q&A
- Fully autonomous report approval
- Automatic customer publication
- Public report links
- Contractual customer approval
- Financial approval or payment integration
- BOQ progress certification
- Automated video transcoding beyond basic compatibility handling
- Full offline-first synchronization
- Cross-project analytics warehouse
- PDF generation and permanent PDF archive
- Native LINE media submission as a replacement for the RAYADEE web form

Customer AI Q&A is a Phase 2 enhancement after deterministic commands and approved-report retrieval are stable.

## 5. Current Data Readiness

The system is ready to begin development, but the following data preparation is required before beta or production rollout.

### 5.1 Existing foundation

- Six project records exist.
- Five projects are active.
- One project is completed.
- Two active subcontractor profiles exist with LINE identities.
- Subcontractor project assignments already exist.
- Five internal Admin-directory records exist.
- Four internal accounts are active.
- The access-request workflow already has an approved historical record.
- Firestore, Cloud SQL, private GCS, Cloud Tasks, Cloud Scheduler, Pub/Sub, Identity Platform, Secret Manager, and Cloud Run are available.

### 5.2 Required cleanup

- Remove or correct one subcontractor assignment that references a non-existent project ID.
- Do not create daily cycles for completed projects.
- Decide whether completed projects should remain visible in historical subcontractor filters.
- Add explicit `role` and `roles` fields to legacy active Admin records.
- Confirm at least one explicit active Owner before rollout.
- Do not rely permanently on the legacy behavior that treats a role-less Admin record as an Owner.

### 5.3 Missing feature data

The following domains do not currently exist and must be introduced by this feature:

- Customer identities
- Customer access requests
- Project memberships
- Project-to-LINE-group destinations
- Daily-report project settings
- Daily cycles
- Subcontractor daily submissions
- Daily-report media metadata
- Consolidated daily reports
- Immutable report versions
- Report audit events
- Customer acknowledgements
- Customer questions
- LINE delivery jobs

## 6. Role and Permission Model

### 6.1 Proposed permissions

```text
daily_reports:view_all
daily_reports:view_project
daily_reports:view_own
daily_reports:create
daily_reports:update_draft
daily_reports:submit
daily_reports:respond_to_changes
daily_reports:review
daily_reports:request_changes
daily_reports:edit_customer_draft
daily_reports:approve
daily_reports:publish
daily_reports:create_correction
daily_reports:configure_project
project_reports:view_published
project_reports:acknowledge
project_reports:ask_question
line_destinations:manage
```

### 6.2 Permission matrix

| Capability | Subcontractor | Admin | Owner | Customer |
|---|---:|---:|---:|---:|
| View own project assignments | Yes | Yes | Yes | Yes |
| Create own daily submission | Yes | No | No | No |
| Edit own draft | Yes | No | No | No |
| Edit after submission | Only after change request | No | No | No |
| View other subcontractor source submissions | No | Authorized projects | All projects | No |
| Request submission changes | No | Authorized projects | All projects | No |
| Edit customer-facing consolidated draft | No | Authorized projects | All projects | No |
| Approve and publish | No | Authorized projects | All projects | No |
| Create correction version | No | Authorized projects | All projects | No |
| Configure daily-report project settings | No | Authorized projects | All projects | No |
| View published customer report | No by default | Authorized projects | All projects | Active project share link |
| Acknowledge customer report | No | No | No | No; discuss in LINE |
| Ask report-linked question | No | No | No | No; discuss in LINE |

### 6.3 Account-approval authority

| Access request | Admin | Owner |
|---|---:|---:|
| Subcontractor | Approve/reject | Approve/reject |
| Customer | Not required for report viewing | Not required for report viewing |
| Admin/staff | No | Approve/reject |
| Owner | No | Approve/reject |

Only an Owner may grant an internal Admin or Owner role.

## 7. First-Time Authentication and Approval

### 7.1 Common lifecycle

```text
PROFILE_REQUIRED
  -> PENDING_APPROVAL
  -> ACTIVE
  -> SUSPENDED
```

Alternative state:

```text
PENDING_APPROVAL -> REJECTED
```

Rejected users may resubmit only through an explicit new request or approved resubmission flow.

### 7.2 Admin/staff

```text
Google sign-in
  -> no active internal directory record
  -> complete required profile
  -> create access request
  -> PENDING_APPROVAL
  -> Owner approves role and project scope
  -> ACTIVE
```

### 7.3 Subcontractor

```text
Open subcontractor LIFF
  -> verify LINE identity
  -> no active subcontractor profile
  -> complete company/contact/KYC information
  -> create access request
  -> PENDING_APPROVAL
  -> Admin or Owner approves and assigns projects
  -> ACTIVE
```

### 7.4 Customer

```text
Open customer LIFF
  -> verify LINE identity
  -> complete name/contact/consent information
  -> enter or open a one-time project invitation
  -> create project access request
  -> PENDING_APPROVAL
  -> Admin or Owner approves membership
  -> ACTIVE for the approved project
```

Membership in a LINE group is not sufficient authorization by itself.

## 8. Project Membership Model

Use one canonical project-membership service for daily-report authorization.

Proposed collection:

```text
project_memberships
```

Example:

```json
{
  "id": "membership_abc",
  "project_id": "project_uuid",
  "principal_type": "SUBCONTRACTOR",
  "principal_id": "subcontractor_id",
  "roles": ["SUBMITTER"],
  "status": "ACTIVE",
  "source": "MIGRATED_ASSIGNED_PROJECT_IDS",
  "approved_by": "admin_or_owner_id",
  "approved_at": "2026-07-18T08:00:00Z",
  "created_at": "2026-07-18T08:00:00Z",
  "updated_at": "2026-07-18T08:00:00Z"
}
```

Principal types:

- `SUBCONTRACTOR`
- `ADMIN`
- `CUSTOMER`

Membership roles:

- `SUBMITTER`
- `REVIEWER`
- `CUSTOMER_VIEWER`

Migration rule:

- Backfill subcontractor memberships from existing `users.assigned_project_ids`.
- Skip non-existent projects.
- Do not create active reporting membership for completed projects.
- Preserve `assigned_project_ids` during the compatibility period.
- Avoid adding a second independent authorization source.
- New membership writes should pass through one backend service.

Owner access remains global and does not require one membership document per project.

## 9. Daily Report Workflow

### 9.1 Project daily cycle

One cycle represents one project and one reporting date.

```text
SCHEDULED
  -> COLLECTING
  -> DRAFTING
  -> PENDING_REVIEW
  -> PUBLISHED
  -> CLOSED
```

Additional states:

- `OVERDUE`
- `CANCELLED`
- `NO_WORK`
- `PARTIALLY_SUBMITTED`

### 9.2 Subcontractor submission

```text
DRAFT
  -> SUBMITTED
  -> INCLUDED
  -> LOCKED
```

Change-request branch:

```text
SUBMITTED
  -> CHANGES_REQUESTED
  -> RESUBMITTED
  -> INCLUDED
```

Additional states:

- `EXCLUDED`
- `WITHDRAWN`

Rules:

- A subcontractor can have only one active submission per project/date.
- Draft saves must be idempotent.
- Submission locks source facts and media from normal editing.
- Admin/Owner cannot silently rewrite subcontractor source facts.
- Incorrect source facts require a change request.
- Admin/Owner may edit only the customer-facing consolidated draft.
- Excluding a submitted source requires an internal reason and audit event.

### 9.3 Consolidated customer report

```text
COLLECTING
  -> DRAFTING
  -> PENDING_REVIEW
  -> APPROVED
  -> PUBLISHED
```

Correction branch:

```text
PUBLISHED
  -> CORRECTION_DRAFT
  -> APPROVED
  -> PUBLISHED as next version
```

Rules:

- `APPROVED` and `PUBLISHED` require Admin or Owner.
- Publish should normally be one backend transaction plus an asynchronous delivery job.
- A published version is immutable.
- A correction creates Version 2, Version 3, and so on.
- Previous versions remain readable to authorized Admin/Owner.
- Customers see the latest published version and a visible correction history.

## 10. Default Schedule and Notifications

All schedule settings are configurable per project.

Default timezone:

```text
Asia/Bangkok
```

Default schedule:

| Time | Action |
|---|---|
| 06:00 | Create daily cycle and expected-submitter snapshot |
| 16:00 | First reminder to missing subcontractors |
| 17:00 | Submission deadline |
| 17:15 | Mark missing submissions overdue and alert Admin/Owner |
| 18:00 | Generate consolidated draft if not already generated |
| 19:00 | Internal review target |

Rules:

- Generate the consolidated draft early when every expected subcontractor has submitted.
- Do not auto-publish at 19:00.
- Respect project working days and holiday exceptions.
- Allow Admin/Owner to mark a project day as `NO_WORK`.
- A late submission after publication does not change the published version automatically.
- Admin/Owner decides whether the late submission requires a correction version.

### 10.1 Required MVP notifications

Subcontractor through `RYD PROJECT ADMIN`:

- Daily cycle available
- Submission reminder
- Overdue reminder
- Submission received
- Change requested
- Submission included
- Report published

Admin/Owner in RAYADEE:

- Missing submissions
- New submission
- Change-request response
- Consolidated draft ready
- Review deadline approaching
- LINE delivery failure
- Customer question

Customer through `RYD PROJECT CUSTOMER`:

- New approved report
- Corrected report version
- Question received
- Project-team response

## 11. Target Cloud Architecture

```text
Subcontractor LINE Rich Menu
  -> Subcontractor LIFF route
  -> React frontend
  -> FastAPI backend
  -> signed/resumable upload session
  -> private GCS media
  -> Firestore submission metadata
  -> Cloud Task for draft/consolidation

Admin/Owner RAYADEE Web
  -> FastAPI review APIs
  -> Firestore transaction
  -> immutable report version
  -> delivery outbox/job
  -> Cloud Task
  -> RYD PROJECT CUSTOMER Messaging API
  -> project LINE group

Customer LINE Rich Menu or report message
  -> Customer LIFF route
  -> LINE authentication
  -> customer/project membership check
  -> published report only
```

### 11.1 Service responsibilities

| Service | Responsibility |
|---|---|
| Cloud Run frontend | RAYADEE React web application |
| Cloud Run backend | Authentication, permissions, workflow, APIs, webhooks and signed URLs |
| Firestore | Workflow documents, memberships, settings, versions and audit events |
| GCS | Private photos, videos, voice notes and thumbnails |
| Cloud Tasks | Draft generation, media processing, reminders and LINE delivery retries |
| Cloud Scheduler | Cycle creation and due-action scans |
| Secret Manager | LINE channel secrets, access tokens and server-side credentials |
| Identity Platform/Firebase | Existing Google Admin authentication |
| Cloud Logging/Monitoring | Operational logs, errors, metrics and alerts |
| Vertex AI | Optional report-drafting assistance |
| Pub/Sub | Optional later fan-out to analytics or other consumers |

### 11.2 Environment separation

Maintain separate resources and values for:

- Production
- Beta

Do not share:

- LINE channel access tokens
- LINE channel secrets
- Customer group bindings
- Firestore report data
- GCS report media
- Cloud Task queues
- Delivery-job state

## 12. Firestore Data Model

Use top-level collections for project/date/status queries and cross-project Admin queues.

### 12.1 `daily_report_project_settings`

Document ID:

```text
{project_id}
```

Example:

```json
{
  "project_id": "project_uuid",
  "enabled": true,
  "timezone": "Asia/Bangkok",
  "working_days": [1, 2, 3, 4, 5, 6],
  "submission_due_time": "17:00",
  "first_reminder_time": "16:00",
  "overdue_grace_minutes": 15,
  "draft_time": "18:00",
  "review_target_time": "19:00",
  "minimum_photo_count": 1,
  "allow_video": true,
  "allow_voice_note": true,
  "require_manpower": true,
  "require_progress": true,
  "customer_destination_id": "destination_abc",
  "created_by": "owner_id",
  "created_at": "2026-07-18T08:00:00Z",
  "updated_at": "2026-07-18T08:00:00Z"
}
```

### 12.2 `daily_report_cycles`

Recommended deterministic document ID:

```text
{project_id}_{YYYY-MM-DD}
```

Example:

```json
{
  "id": "project_uuid_2026-07-18",
  "project_id": "project_uuid",
  "report_date": "2026-07-18",
  "timezone": "Asia/Bangkok",
  "status": "COLLECTING",
  "expected_subcontractor_ids": ["sub_001", "sub_002"],
  "submitted_subcontractor_ids": ["sub_001"],
  "missing_subcontractor_ids": ["sub_002"],
  "submission_due_at": "2026-07-18T10:00:00Z",
  "review_target_at": "2026-07-18T12:00:00Z",
  "report_id": "report_abc",
  "created_at": "2026-07-17T23:00:00Z",
  "updated_at": "2026-07-18T09:00:00Z"
}
```

Expected-submitter IDs are a snapshot. Later membership changes must not silently change the historical cycle.

### 12.3 `daily_report_submissions`

Recommended deterministic document ID:

```text
{project_id}_{YYYY-MM-DD}_{subcontractor_id}
```

Example:

```json
{
  "id": "submission_abc",
  "cycle_id": "project_uuid_2026-07-18",
  "project_id": "project_uuid",
  "report_date": "2026-07-18",
  "subcontractor_id": "sub_001",
  "submitted_by_id": "account_001",
  "status": "SUBMITTED",
  "work_locations": ["Level 2", "Zone B"],
  "work_items": [
    {
      "description": "Ceiling framing",
      "quantity": 120,
      "unit": "sqm",
      "progress_percent": 42
    }
  ],
  "manpower": {
    "total": 8,
    "supervisors": 1,
    "workers": 7
  },
  "issue_flags": ["QUALITY"],
  "issue_note": "Damaged ceiling material separated for replacement.",
  "tomorrow_plan": "Continue Zone B and receive replacement material.",
  "media_count": 4,
  "voice_note_count": 1,
  "location_consent": false,
  "source_version": 1,
  "submitted_at": "2026-07-18T09:42:00Z",
  "created_at": "2026-07-18T08:00:00Z",
  "updated_at": "2026-07-18T09:42:00Z"
}
```

Avoid storing large media arrays or base64 content in this document.

### 12.4 `daily_report_media`

Example:

```json
{
  "id": "media_abc",
  "submission_id": "submission_abc",
  "project_id": "project_uuid",
  "report_date": "2026-07-18",
  "kind": "PHOTO",
  "upload_status": "READY",
  "storage_key": "gs://bucket/daily-reports/project_uuid/2026-07-18/submissions/submission_abc/media_abc/photo.jpg",
  "thumbnail_storage_key": null,
  "content_type": "image/jpeg",
  "size_bytes": 348120,
  "checksum": "server-verified-checksum",
  "capture_timestamp": null,
  "uploaded_by": "account_001",
  "uploaded_at": "2026-07-18T09:30:00Z"
}
```

Kinds:

- `PHOTO`
- `VIDEO`
- `VOICE_NOTE`
- `THUMBNAIL`
- `REPORT_PDF` in a future phase

Upload states:

- `PENDING`
- `UPLOADING`
- `READY`
- `FAILED`
- `QUARANTINED`
- `DELETED`

### 12.5 `daily_reports`

One working consolidated report per project/date.

Example:

```json
{
  "id": "report_abc",
  "cycle_id": "project_uuid_2026-07-18",
  "project_id": "project_uuid",
  "report_date": "2026-07-18",
  "status": "PENDING_REVIEW",
  "source_submission_ids": ["submission_abc", "submission_def"],
  "excluded_submission_ids": [],
  "draft": {
    "executive_summary": "Customer-facing summary.",
    "today_progress": ["Ceiling framing in Zone A and Zone B"],
    "current_progress_percent": 42,
    "issues": ["Replacement material required"],
    "tomorrow_plan": ["Continue Zone B"]
  },
  "ai_metadata": {
    "used": true,
    "provider": "VERTEX_AI",
    "model": "configured-model-name",
    "confidence": "MEDIUM",
    "generated_at": "2026-07-18T10:05:00Z"
  },
  "current_version": 0,
  "last_edited_by": "admin_id",
  "created_at": "2026-07-18T10:00:00Z",
  "updated_at": "2026-07-18T10:15:00Z"
}
```

Do not store prompts containing secret or unrelated internal data.

### 12.6 `daily_report_versions`

Every published version is an immutable snapshot.

Example:

```json
{
  "id": "report_abc_v1",
  "report_id": "report_abc",
  "project_id": "project_uuid",
  "report_date": "2026-07-18",
  "version": 1,
  "content": {
    "executive_summary": "Approved customer-facing summary.",
    "today_progress": ["Ceiling framing in Zone A and Zone B"],
    "current_progress_percent": 42,
    "issues": ["Replacement material required"],
    "tomorrow_plan": ["Continue Zone B"]
  },
  "published_media_ids": ["media_abc"],
  "source_submission_ids": ["submission_abc", "submission_def"],
  "approved_by": "admin_or_owner_id",
  "approved_at": "2026-07-18T11:45:00Z",
  "published_at": "2026-07-18T11:45:00Z",
  "supersedes_version_id": null,
  "correction_reason": null
}
```

Application code must reject normal updates to published version documents.

### 12.7 `daily_report_events`

Append-only audit history.

Example:

```json
{
  "id": "event_abc",
  "project_id": "project_uuid",
  "cycle_id": "project_uuid_2026-07-18",
  "report_id": "report_abc",
  "submission_id": null,
  "event_type": "REPORT_PUBLISHED",
  "actor_id": "admin_id",
  "actor_role": "admin",
  "from_status": "APPROVED",
  "to_status": "PUBLISHED",
  "comment": null,
  "metadata": {
    "version": 1
  },
  "created_at": "2026-07-18T11:45:00Z"
}
```

Event types include:

- `CYCLE_CREATED`
- `REMINDER_SENT`
- `SUBMISSION_SAVED`
- `SUBMISSION_SUBMITTED`
- `CHANGES_REQUESTED`
- `SUBMISSION_RESUBMITTED`
- `SUBMISSION_INCLUDED`
- `SUBMISSION_EXCLUDED`
- `DRAFT_GENERATED`
- `DRAFT_EDITED`
- `REPORT_APPROVED`
- `REPORT_PUBLISHED`
- `CORRECTION_CREATED`
- `CUSTOMER_ACKNOWLEDGED`
- `CUSTOMER_QUESTION_CREATED`
- `LINE_DELIVERY_SUCCEEDED`
- `LINE_DELIVERY_FAILED`

### 12.8 `customers`

Example:

```json
{
  "id": "customer_abc",
  "line_uid": "provider-scoped-line-user-id",
  "display_name": "Customer",
  "contact_name": "Customer contact",
  "phone": null,
  "is_active": true,
  "consent_version": "2026-07",
  "consented_at": "2026-07-18T08:00:00Z",
  "created_at": "2026-07-18T08:00:00Z",
  "updated_at": "2026-07-18T08:00:00Z"
}
```

### 12.9 `line_destinations`

Example:

```json
{
  "id": "destination_abc",
  "project_id": "project_uuid",
  "channel_key": "CUSTOMER_OA",
  "destination_type": "GROUP",
  "line_group_id": "group-id-from-verified-webhook",
  "display_name": "Project customer group",
  "status": "ACTIVE",
  "verified_by": "admin_or_owner_id",
  "verified_at": "2026-07-18T08:00:00Z",
  "created_at": "2026-07-18T08:00:00Z",
  "updated_at": "2026-07-18T08:00:00Z"
}
```

Never store channel access tokens or channel secrets in this collection.

### 12.10 `daily_report_delivery_jobs`

Example:

```json
{
  "id": "delivery_abc",
  "report_id": "report_abc",
  "version_id": "report_abc_v1",
  "project_id": "project_uuid",
  "destination_id": "destination_abc",
  "channel_key": "CUSTOMER_OA",
  "status": "PENDING",
  "retry_key": "uuid-used-for-line-idempotency",
  "attempt_count": 0,
  "last_error_code": null,
  "line_request_id": null,
  "next_attempt_at": null,
  "created_at": "2026-07-18T11:45:00Z",
  "updated_at": "2026-07-18T11:45:00Z"
}
```

Delivery states:

- `PENDING`
- `PROCESSING`
- `SENT`
- `RETRYING`
- `FAILED`
- `CANCELLED`

## 13. Firestore Index Plan

Create indexes based on actual API query shapes.

Expected composite indexes:

```text
daily_report_cycles:
  project_id + report_date desc
  status + submission_due_at
  status + review_target_at

daily_report_submissions:
  project_id + report_date + status
  subcontractor_id + report_date desc
  cycle_id + status

daily_reports:
  project_id + report_date desc
  status + updated_at desc

daily_report_versions:
  report_id + version desc
  project_id + report_date desc

daily_report_events:
  report_id + created_at asc
  submission_id + created_at asc
  project_id + created_at desc

project_memberships:
  principal_id + status + project_id
  project_id + principal_type + status

daily_report_delivery_jobs:
  status + next_attempt_at
  report_id + created_at desc
```

Do not create speculative indexes that are not used by a defined query.

## 14. GCS Storage Plan

Use dedicated private buckets:

```text
project001-489710-daily-reports
project001-489710-daily-reports-beta
```

Final names must be checked for global availability during implementation.

Recommended object layout:

```text
daily-reports/
  {project_id}/
    {report_date}/
      submissions/
        {submission_id}/
          photos/
            {media_id}-{safe_filename}
          videos/
            {media_id}-{safe_filename}
          voice/
            {media_id}-{safe_filename}
          thumbnails/
            {media_id}.jpg
      published/
        {report_id}/
          version-{version}/
            report.pdf
```

MVP uses submission media. Stored PDF output remains a future phase.

Required bucket controls:

- Uniform bucket-level access
- Public access prevention
- Same selected region as the application unless data residency requires otherwise
- Soft delete
- Lifecycle cleanup for abandoned uploads
- Optional object versioning based on retention policy
- Backend service account scoped only to required buckets
- No public ACLs
- No permanent public media URLs

Upload design:

1. Authenticated client requests an upload session.
2. Backend verifies role, project membership, submission state, content type, and size.
3. Backend issues a short-lived signed or resumable upload.
4. Client uploads directly to GCS.
5. Client calls finalize.
6. Backend verifies object metadata/checksum.
7. Media document becomes `READY`.

Suggested signed read URL lifetime:

```text
5–15 minutes
```

## 15. Backend API Plan

Use route prefix:

```text
/api/v1/daily-reports
```

All API authorization is enforced in FastAPI. The frontend never accesses Firestore directly.

### 15.1 Subcontractor APIs

```text
GET    /api/v1/daily-reports/me/projects
GET    /api/v1/daily-reports/me/cycles
GET    /api/v1/daily-reports/me/submissions
GET    /api/v1/daily-reports/me/submissions/{submission_id}
POST   /api/v1/daily-reports/me/submissions
PATCH  /api/v1/daily-reports/me/submissions/{submission_id}
POST   /api/v1/daily-reports/me/submissions/{submission_id}/submit
POST   /api/v1/daily-reports/me/submissions/{submission_id}/resubmit
```

Rules:

- Project must be active.
- User must have active `SUBMITTER` membership.
- Submission project/date/subcontractor identity is resolved server-side.
- A subcontractor cannot read or mutate another subcontractor's submission.
- Submitted facts are immutable until a change request reopens the submission.

### 15.2 Media APIs

```text
POST   /api/v1/daily-reports/me/submissions/{submission_id}/media/upload-session
POST   /api/v1/daily-reports/me/submissions/{submission_id}/media/{media_id}/finalize
DELETE /api/v1/daily-reports/me/submissions/{submission_id}/media/{media_id}
GET    /api/v1/daily-reports/media/{media_id}/signed-url
```

Rules:

- Validate MIME type and size server-side.
- Normalize filenames.
- Require media ownership/permission checks before signed URL generation.
- Do not return raw GCS paths to customer clients.
- Do not allow media deletion from locked or published source submissions.

### 15.3 Admin/Owner review APIs

```text
GET    /api/v1/daily-reports/admin/queue
GET    /api/v1/daily-reports/admin/projects/{project_id}/cycles
GET    /api/v1/daily-reports/admin/cycles/{cycle_id}
GET    /api/v1/daily-reports/admin/submissions/{submission_id}
POST   /api/v1/daily-reports/admin/submissions/{submission_id}/request-changes
POST   /api/v1/daily-reports/admin/submissions/{submission_id}/include
POST   /api/v1/daily-reports/admin/submissions/{submission_id}/exclude
GET    /api/v1/daily-reports/admin/reports/{report_id}
PATCH  /api/v1/daily-reports/admin/reports/{report_id}/draft
POST   /api/v1/daily-reports/admin/reports/{report_id}/regenerate-draft
POST   /api/v1/daily-reports/admin/reports/{report_id}/approve-and-publish
POST   /api/v1/daily-reports/admin/reports/{report_id}/corrections
GET    /api/v1/daily-reports/admin/reports/{report_id}/events
```

Rules:

- Admin must have active `REVIEWER` membership for the project.
- Owner bypasses project membership through global Owner permission.
- Request changes requires a reason.
- Exclude requires an internal reason.
- Draft edits create audit events.
- Approve-and-publish requires an explicit confirmation payload.
- Backend validates that the report is still on the reviewed source/draft version.
- Concurrent publication requests must be idempotent.

### 15.4 Project-settings APIs

```text
GET   /api/v1/daily-reports/admin/projects/{project_id}/settings
PUT   /api/v1/daily-reports/admin/projects/{project_id}/settings
POST  /api/v1/daily-reports/admin/projects/{project_id}/no-work-days
GET   /api/v1/daily-reports/admin/projects/{project_id}/memberships
POST  /api/v1/daily-reports/admin/projects/{project_id}/memberships
PATCH /api/v1/daily-reports/admin/projects/{project_id}/memberships/{membership_id}
```

### 15.5 Customer APIs

```text
GET   /api/v1/project-reports/me/projects
GET   /api/v1/project-reports
GET   /api/v1/project-reports/{report_id}
GET   /api/v1/project-reports/{report_id}/versions
POST  /api/v1/project-reports/{report_id}/acknowledge
POST  /api/v1/project-reports/{report_id}/questions
GET   /api/v1/project-reports/{report_id}/questions
```

Rules:

- Return only published versions.
- Verify active customer membership on every request.
- Do not expose source submissions, internal events, Admin notes, excluded evidence, AI prompts, or delivery metadata.
- Acknowledgement must state that it is not contractual acceptance.

### 15.6 LINE webhook APIs

```text
POST /api/v1/webhooks/line/subcontractor
POST /api/v1/webhooks/line/customer
```

Rules:

- Verify `X-Line-Signature` against the unmodified raw body.
- Use the correct channel secret for each endpoint.
- Return a successful webhook response quickly.
- Process non-trivial work asynchronously.
- Store webhook event IDs or idempotency identifiers where supported.
- Capture customer `groupId` only from a verified customer-OA webhook.
- Require Admin/Owner confirmation before activating a group/project binding.

### 15.7 Internal task endpoints

Private authenticated Cloud Task endpoints:

```text
POST /api/v1/internal/daily-reports/create-cycle
POST /api/v1/internal/daily-reports/send-reminder
POST /api/v1/internal/daily-reports/generate-draft
POST /api/v1/internal/daily-reports/deliver-line-message
POST /api/v1/internal/daily-reports/process-media
POST /api/v1/internal/daily-reports/scan-due-actions
```

These endpoints must reject public user sessions and require the expected Cloud Task identity.

## 16. Transaction and Idempotency Rules

Use Firestore transactions for:

- Creating one daily cycle per project/date
- Creating one submission per project/date/subcontractor
- Locking a submitted source version
- Moving submission state
- Creating one report version number
- Publishing the report and creating the delivery job
- Recording customer acknowledgement once per customer/report/version

Required idempotency keys:

- Cycle creation: `{project_id}:{report_date}`
- Submission creation: `{project_id}:{report_date}:{subcontractor_id}`
- Submission submit/resubmit operation
- Approve-and-publish operation
- Customer acknowledgement
- LINE delivery retry

For LINE push retries:

- Generate one stable `X-Line-Retry-Key` before the first request.
- Reuse the same key for supported retries.
- Store the key in the delivery job.
- Treat LINE `409` with accepted-request metadata as successful deduplication.

## 17. Drafting and AI Plan

### 17.1 Deterministic consolidation

Always provide a deterministic fallback that:

- Combines included work items
- Aggregates manpower
- Lists work locations
- Calculates or displays approved progress inputs
- Groups issue flags
- Lists tomorrow plans
- References available evidence

This fallback must work even when AI is unavailable.

### 17.2 Optional AI draft

AI may:

- Rewrite source facts into a concise customer-facing summary
- Deduplicate repeated work descriptions
- Highlight conflicting information
- Flag missing evidence
- Suggest questions for the reviewer

AI may not:

- Approve a report
- Publish a report
- Change source facts
- Invent progress percentages
- Certify contract work
- Hide issues
- Reveal internal or financial information to customers

Store:

- Provider
- Model identifier
- Prompt/template version
- Generation timestamp
- Confidence label
- Source submission version IDs
- Reviewer edits after generation

Do not block manual reporting when AI fails.

## 18. Frontend Route Plan

### 18.1 Subcontractor

```text
/daily-reports/me
/daily-reports/me/new
/daily-reports/me/{submissionId}
```

### 18.2 Admin/Owner

```text
/daily-reports
/daily-reports/projects/{projectId}
/daily-reports/review/{reportId}
/daily-reports/settings/{projectId}
```

### 18.3 Customer

```text
/project-reports
/project-reports/{reportId}
```

Route names may be adjusted during API/UX contract review, but role boundaries must remain explicit.

## 19. Frontend Component Plan

Implement future React components under:

```text
Projects-001-FE/src/components/dailyReports/
```

### 19.1 Shared

- `DailyReportStatusBadge.jsx`
- `DailyReportTimeline.jsx`
- `DailyReportMediaGrid.jsx`
- `DailyReportMediaViewer.jsx`
- `DailyReportIssueList.jsx`
- `DailyReportProgressSummary.jsx`
- `dailyReportUtils.js`

### 19.2 Subcontractor

- `SubcontractorDailyReportWorkspace.jsx`
- `DailyReportProjectPicker.jsx`
- `DailyReportEvidenceStep.jsx`
- `DailyReportWorkStep.jsx`
- `DailyReportChecklistStep.jsx`
- `DailyReportReviewStep.jsx`
- `DailyReportSubmissionSuccess.jsx`
- `DailyReportChangeRequest.jsx`
- `DailyReportHistory.jsx`

### 19.3 Admin/Owner

- `DailyReportReviewQueue.jsx`
- `DailyReportReviewWorkspace.jsx`
- `DailyReportSubmissionPanel.jsx`
- `DailyReportEvidencePane.jsx`
- `DailyReportDraftEditor.jsx`
- `DailyReportSourceComparison.jsx`
- `DailyReportPublishDialog.jsx`
- `DailyReportCorrectionDialog.jsx`
- `DailyReportProjectSettings.jsx`
- `DailyReportLineDestinationSettings.jsx`

### 19.4 Customer

- `CustomerProjectReports.jsx`
- `CustomerDailyReportCard.jsx`
- `CustomerDailyReportDetail.jsx`
- `CustomerReportVersionNotice.jsx`
- `CustomerAcknowledgement.jsx`
- `CustomerReportQuestionForm.jsx`

## 20. UX Requirements

### 20.1 Subcontractor experience

- Mobile-first LIFF layout
- Normal daily report target completion within three minutes
- Auto-save drafts
- Large camera and media controls
- Clear upload progress and retry
- Calm no-issue path
- Required-field explanation
- Review before submit
- Submission confirmation
- Visible status and change-request reason
- History for assigned projects
- Thai-first copy with consistent construction terminology

### 20.2 Admin/Owner experience

- Cross-project review queue
- Filters by project, date, status, overdue, and issue severity
- Evidence and source facts visible beside the customer draft
- Clear indication of AI-generated text
- Missing-submitter visibility
- Source conflicts and missing evidence warnings
- Explicit publish destination
- Approval confirmation checkbox
- Version and audit history
- Delivery status and retry action

### 20.3 Customer experience

- Mobile-first LIFF layout
- Published information only
- Clear project/date/version
- Current progress
- Today's work
- Issues and responsible follow-up
- Tomorrow plan
- Approved media
- “Reviewed by” identity
- Acknowledgement disclaimer
- Report-linked question
- Visible correction notice

## 21. LINE Message Plan

### 21.1 Customer publication message

Use a deterministic Flex Message containing:

- Project name
- Report date
- Current progress
- Short approved summary
- Issue indicator
- Report version
- Reviewer label
- Button to open the authenticated report

Do not generate publication wording with AI in MVP.

### 21.2 Simple customer bot commands

MVP command intents:

- Latest report
- Current progress
- Open issues
- Tomorrow plan
- Help

The response must read only the latest published version for the group-bound project.

### 21.3 Phase 2 AI chatbot

Future customer questions may use AI only with:

- Published report versions
- Approved customer-visible issue history
- Project/date context

If the answer is not present in approved data:

- Do not infer.
- Create a report-linked question for Admin/Owner.
- Tell the customer that the project team will respond.

## 22. Security and Privacy Requirements

- Verify LINE access or ID tokens server-side.
- Validate the expected LINE channel/audience.
- Never trust role or project ID from the client.
- Verify Firebase Admin tokens and tenant context.
- Use backend-issued RAYADEE sessions.
- Verify every project membership server-side.
- Verify LINE webhook signatures before parsing.
- Store LINE secrets and access tokens only in Secret Manager/server configuration.
- Do not expose GCS paths to customers.
- Use short-lived signed URLs after permission checks.
- Restrict upload MIME types and sizes.
- Record checksums.
- Sanitize filenames.
- Avoid logging tokens, signed URLs, phone numbers, LINE IDs, KYC paths, or report media URLs.
- Separate customer-visible data from source/internal data.
- Keep published versions immutable.
- Record all review, approval, correction, and delivery events.
- Apply least-privilege IAM to the daily-report bucket and task endpoints.
- Add rate limiting to authentication, upload-session, question, and webhook endpoints.
- Preserve user consent and privacy-policy version.

## 23. Cloud Configuration Plan

Required server-side settings, using environment-specific names:

```text
SUBCONTRACTOR_LINE_CHANNEL_ID
SUBCONTRACTOR_LINE_CHANNEL_SECRET
SUBCONTRACTOR_LINE_CHANNEL_ACCESS_TOKEN
SUBCONTRACTOR_LINE_LIFF_ID

CUSTOMER_LINE_CHANNEL_ID
CUSTOMER_LINE_CHANNEL_SECRET
CUSTOMER_LINE_CHANNEL_ACCESS_TOKEN
CUSTOMER_LINE_LIFF_ID

DAILY_REPORT_GCS_BUCKET
DAILY_REPORT_GCS_PREFIX
DAILY_REPORT_SIGNED_URL_MINUTES
DAILY_REPORT_TASK_QUEUE
DAILY_REPORT_TASK_REGION
DAILY_REPORT_DEFAULT_TIMEZONE
```

Rules:

- LIFF IDs may be exposed as frontend build configuration where required.
- Channel secrets and access tokens are server-side only.
- Do not place real values in repository files.
- Create matching beta values and resources.

Recommended Cloud Task queue:

```text
projects001-daily-reports
projects001-beta-daily-reports
```

Recommended Scheduler approach:

- One authenticated job creates due daily cycles.
- One authenticated job scans due actions every 15 minutes.
- The backend applies each project's timezone and schedule.
- The scanner enqueues per-project/per-recipient Cloud Tasks.
- Avoid creating many Scheduler jobs per project.

## 24. Data Migration and Bootstrap Plan

### 24.1 Pre-development validation

- Confirm active project IDs.
- Confirm completed project handling.
- Identify stale subcontractor assignments.
- Confirm explicit Admin/Owner roles.
- Confirm both OA channels are under the same provider.
- Confirm production and beta LIFF applications.

### 24.2 Membership backfill

- Create `project_memberships`.
- Backfill valid active subcontractor assignments.
- Add Admin reviewer memberships or explicit all-project policy.
- Preserve legacy customer memberships during rollout; new share-link viewing does not require membership.
- Produce a dry-run summary before writing.
- Make migration idempotent.

### 24.3 Project settings bootstrap

For each active project:

- Create daily-report settings disabled by default.
- Confirm working days.
- Confirm timezone.
- Confirm submission deadline.
- Confirm expected subcontractors.
- Confirm Admin reviewers.
- Confirm evidence rules.
- Bind and verify the customer LINE group.
- Enable reporting only after the project checklist is complete.

### 24.4 Admin-role normalization

- Write explicit `role` and `roles` to legacy records.
- Confirm at least one active Owner.
- Ensure Admin accounts cannot grant Owner access.
- Preserve audit details for who normalized each account.

## 25. Observability Plan

### 25.1 Structured logs

Log identifiers, not private content:

- Project ID
- Cycle ID
- Submission ID
- Report ID
- Version
- Delivery job ID
- Event type
- Status transition
- Duration
- Error category
- LINE request ID where safe

Do not log:

- Access tokens
- Channel secrets
- Signed URLs
- LINE user IDs
- Group IDs
- Contact information
- KYC information
- Full report text
- Media object URLs

### 25.2 Metrics

- Cycles created
- Expected submissions
- On-time submission rate
- Overdue submission count
- Draft-generation latency
- Review latency
- Publish latency
- LINE delivery success rate
- LINE delivery retry/failure count
- Upload failure rate
- Customer acknowledgement rate
- Customer question count

### 25.3 Alerts

- Scheduler job failure
- Cloud Task repeated failure
- LINE webhook signature failures above threshold
- LINE delivery failure above threshold
- GCS upload finalization failure
- AI drafting failure rate
- Firestore permission or transaction errors
- Report stuck in `PENDING_REVIEW`
- Delivery job stuck in `PROCESSING`

## 26. Testing Strategy

### 26.1 Backend tests

- Role and permission matrix
- Project membership enforcement
- Owner global access
- Admin authorized-project access
- Subcontractor isolation
- Customer published-only access
- First-time access request states
- Owner-only internal account approval
- Daily cycle idempotency
- Submission uniqueness
- Draft save and submit transitions
- Change request and resubmission
- Immutable submitted facts
- Consolidation rules
- Version publication transaction
- Correction versioning
- Signed upload/read permission checks
- Webhook signature verification
- Delivery retry idempotency
- Customer acknowledgement uniqueness
- Customer question authorization

### 26.2 Frontend tests

- Route protection by role
- LIFF initialization context
- Mobile three-step submission
- Draft auto-save recovery
- Upload progress and retry
- Required-field validation
- Change-request display
- Review queue filters
- Draft editor dirty-state protection
- Publish confirmation
- Published/corrected version display
- Customer acknowledgement disclaimer
- Empty, loading, error, and offline states

### 26.3 Integration tests

- Subcontractor LINE login → approved account → submission
- Multiple subcontractors → one consolidated report
- Admin request changes → subcontractor resubmission
- Admin approval → immutable version → delivery job
- Customer OA push → login-free project report link
- Missing, disabled, or rotated share token denied
- Share token from another project denied
- Failed LINE delivery retried without duplicate message
- Late submission after publish creates no silent mutation

### 26.4 Manual beta tests

- Real subcontractor mobile device in LINE
- Camera/photo/video selection
- Slow mobile network
- Closed LIFF and reopened draft
- Both production-like OA Rich Menus in beta
- Customer project group binding
- Group push and report link
- Multiple customers in one group
- Blocked/unfriended OA behavior
- Completed project behavior
- Holiday/no-work behavior

## 27. Development Phases

### Phase 0: Contract and Data Preparation

Tasks:

- Finalize collection names.
- Finalize route names.
- Finalize role permissions.
- Finalize customer invitation approach.
- Clean stale project assignment.
- Normalize Admin/Owner roles.
- Define project-membership migration.
- Confirm beta and production LINE channel setup.
- Confirm default file constraints.

Exit criteria:

- No unresolved authorization decisions.
- Data-migration dry-run plan approved.
- API and state contracts approved.

### Phase 1: Backend Foundation

Tasks:

- Add daily-report schemas.
- Add Firestore service layer.
- Add permission helpers.
- Add status-transition validators.
- Add audit-event writer.
- Add deterministic IDs and idempotency handling.
- Add project-settings service.
- Add project-membership service.

Exit criteria:

- Backend can create/read project settings and daily cycles.
- Role tests pass.
- No frontend dependency on direct Firestore access.

### Phase 2: Authentication and Membership

Tasks:

- Extend multi-LIFF configuration.
- Harden LINE token audience/channel verification.
- Extend access requests for customer accounts.
- Add customer profiles.
- Add one-time project invitation flow.
- Add membership approval.
- Add Admin reviewer project scope.
- Preserve Owner global access.

Exit criteria:

- Admin/staff first-time approval works.
- Subcontractor first-time approval works.
- Customer first-time approval works.
- Cross-project access is denied.

### Phase 3: Subcontractor Submission and Media

Tasks:

- Add subcontractor APIs.
- Add private GCS upload-session flow.
- Add media metadata and finalization.
- Add draft auto-save.
- Add submit/resubmit workflow.
- Build mobile LIFF submission pages.
- Add history and status UI.

Exit criteria:

- Subcontractor completes a normal report within the target flow.
- At least one required photo is enforced.
- Submitted facts are locked.
- Change requests reopen only the correct submission.

### Phase 4: Consolidation and Admin Review

Tasks:

- Add cycle aggregation.
- Add deterministic draft generation.
- Add optional AI drafting.
- Add Admin review queue.
- Add evidence/source comparison.
- Add customer-draft editing.
- Add change requests and include/exclude actions.
- Add audit timeline.

Exit criteria:

- Multiple submissions produce one project draft.
- Admin/Owner can trace every statement to included source data.
- AI failure does not block review.

### Phase 5: Publication and Customer Portal

Tasks:

- Add transactional approve-and-publish.
- Add immutable versions.
- Add correction flow.
- Add customer report APIs.
- Add customer report pages.
- Add acknowledgement.
- Add report-linked questions.

Exit criteria:

- Only Admin/Owner can publish.
- Published Version 1 cannot be edited.
- Correction produces Version 2.
- Customers see only approved project reports.

### Phase 6: LINE Delivery

Status: Complete — acceptance testing confirmed by the user on 2026-07-19.

Tasks:

- Add customer OA webhook.
- Add subcontractor OA webhook where needed.
- Add verified group binding.
- Add Flex Message template.
- Add delivery jobs.
- Add Cloud Task delivery worker.
- Add `X-Line-Retry-Key` handling.
- Add delivery status UI.
- Add basic deterministic customer commands.

Exit criteria:

- One publish action produces one customer message.
- Retry does not duplicate the message.
- Incorrect/unverified group binding cannot receive a report.

### Phase 6.5: Subcontractor Portal Mobile Readiness

Status: Complete — release gate passed on 2026-07-19.

Detailed plan:

- [Subcontractor Mobile Responsive Plan](./Subcontractor-Mobile-Responsive-Plan.md)

Implementation status (2026-07-19):

- Local frontend implementation complete for Sidebar, Topbar, Daily Report, Input, and Profile.
- Frontend lint and production build pass.
- Demo deployment and real iPhone/Android LINE testing passed.
- Subcontractor and customer mobile UI/UX, LINE flows, uploads, publication, acknowledgement, questions, permissions, and desktop regressions passed.
- No critical or high-priority defects remain open.
- Phase 6.5 is closed and its Phase 7 release gate is satisfied.

Scope:

- Responsive web and LIFF optimization only
- Entire subcontractor portal
- Daily Report
- Input
- Profile
- Sidebar
- Topbar
- No native iOS or Android application
- No backend or business-rule redesign

Tasks:

- Approve mobile wireframes for the shared shell, Daily Report, Input, and Profile.
- Replace the desktop mobile shell with a compact header and off-canvas navigation.
- Remove the desktop sidebar offset and horizontal overflow on mobile.
- Optimize the Daily Report three-step flow for camera-first mobile use.
- Optimize Input receipt capture, OCR review, line items, preview, and submission.
- Replace Profile inline desktop grids with responsive sections.
- Add safe-area, keyboard, touch-target, upload-retry, and weak-network handling.
- Verify all modified pages in LINE on iPhone and Android.
- Run desktop regression checks.

Exit criteria:

- Daily Report, Input, and Profile work from 320px through 430px.
- No supported subcontractor flow has horizontal page scrolling.
- Mobile navigation and Sign Out are accessible.
- Primary actions remain reachable with the keyboard open.
- Camera/gallery uploads and retry states work inside LINE.
- Daily Report normal path meets the target completion time.
- iPhone LINE and Android LINE beta flows pass.
- Desktop Sidebar, Topbar, Daily Report, Input, and Profile do not regress.
- Frontend lint and production build pass.

Phase gate:

- Phase 7 must not begin until Phase 6.5 passes in demo.
- Subcontractor reminders must not be enabled until the mobile portal is ready.
- Gate result: passed on 2026-07-19.

### Phase 7: Scheduling and Reminders

Status: Implemented locally on 2026-07-19 — Cloud Scheduler configuration and deployed-environment verification remain.

Tasks:

- Add global Scheduler jobs.
- Add due-action scanner.
- Add cycle creation tasks.
- Add missing-submission reminders.
- Add overdue notifications.
- Add review-target alerts.
- Add working-day and no-work rules.

Implementation notes:

- Added authenticated global cycle-creation and due-action scan endpoints.
- Added per-project schedule settings with `Asia/Bangkok` defaults.
- Added immutable expected-subcontractor cycle snapshots.
- Added Thai LINE cycle, reminder, overdue, and submission-received messages.
- Added durable Admin/Owner alerts for missing submissions, new submissions, change responses, draft readiness, review targets, LINE delivery failures, and customer questions.
- Added Admin/Owner no-work-day APIs.
- Added an idempotent Cloud Scheduler configuration helper using OIDC.
- Added focused backend tests for idempotency, no-work suppression, overdue alerts, draft/review alerts, and manual publication.
- Deployment instructions: `Phase-7-Scheduler-Runbook.md`.

Exit criteria:

- Default schedule operates in `Asia/Bangkok`.
- Project-specific times work.
- Completed/disabled projects create no cycles.
- Customer publishing remains manual.

### Phase 8: Hardening and Beta

Tasks:

- Add Firestore indexes.
- Add GCS lifecycle and soft-delete controls.
- Enable Firestore point-in-time recovery and delete protection before production.
- Apply least-privilege IAM.
- Add rate limits.
- Add structured logs, metrics, and alerts.
- Run security and privacy review.
- Complete mobile/accessibility QA.
- Run beta project pilot.

Implementation status (2026-07-19): in progress.

Implemented:

- Added privacy-safe structured request and operational logs with request IDs.
- Added rate limits for authentication, uploads, customer questions, and the customer LINE webhook.
- Added bounded upload reads plus supported MIME and file-signature validation.
- Added global system-failure notifications for all active Admins/Owners and retained project-scoped failure routing.
- Removed internal exception details from authentication failure responses.
- Added Firestore composite-index configuration; all eight indexes report `READY` in `prod-beta`.
- Confirmed `prod-beta` point-in-time recovery and delete protection are enabled.
- Enabled GCS Autoclass with `ARCHIVE` terminal storage, 7-day soft delete, public access prevention, and uniform access.
- Added only incomplete-multipart cleanup after 7 days; valid evidence has no delete lifecycle.
- Added Cloud Logging metrics for Scheduler, LINE delivery, subcontractor notification, upload, webhook signature, rate-limit, and server failures.
- Added repeatable Storage, Firestore index, monitoring, and dedicated beta IAM helpers.
- Added focused security tests and the Phase 8 operations runbook.
- Deployed the hardened backend and frontend revisions to the isolated beta
  Cloud Run services on 2026-07-19.
- Created beta-only cycle-creation and due-action Scheduler jobs and confirmed
  both OIDC requests returned HTTP 200.

Remaining before Phase 8 exit:

- Cut the shared LINE OA/LIFF applications over to the beta URLs and repeat the
  beta E2E regression.
- Provide and verify the shared monitoring email channel.
- Create the currently missing dedicated beta runtime identity, move beta services away from the shared over-privileged `backend-runtime` identity, then remove unused broad roles.

Operations and rollback instructions: `Phase-8-Hardening-Runbook.md`.

Exit criteria:

- Beta end-to-end flow passes.
- No critical authorization or privacy findings.
- Delivery and upload failure recovery verified.
- Operations runbook completed.

### Phase 9: Production Rollout

Tasks:

- Deploy disabled by default.
- Configure one pilot project.
- Verify project members and customer group.
- Enable reporting for the pilot.
- Monitor for one reporting week.
- Fix high-priority operational issues.
- Expand project by project.

Exit criteria:

- Pilot acceptance metrics met.
- Admin/Owner signs off.
- Rollback procedure verified.
- No unresolved critical incidents.

## 28. Rollout and Rollback

### 28.1 Feature flags

Recommended flags:

```text
DAILY_REPORTS_ENABLED
DAILY_REPORTS_AI_DRAFT_ENABLED
DAILY_REPORTS_LINE_DELIVERY_ENABLED
DAILY_REPORTS_CUSTOMER_QUESTIONS_ENABLED
```

Also store per-project `enabled`.

### 28.2 Safe rollout

1. Deploy backend contracts with the feature globally disabled.
2. Deploy frontend routes hidden unless enabled.
3. Configure beta LINE channels and beta project.
4. Complete beta end-to-end tests.
5. Configure one production pilot project.
6. Enable submission only.
7. Enable Admin review.
8. Enable customer portal.
9. Enable LINE delivery last.

### 28.3 Rollback behavior

- Disable new cycle creation.
- Preserve all existing submissions and published versions.
- Stop new LINE delivery jobs.
- Do not delete report data.
- Allow Admin/Owner read-only access to historical reports.
- Resume failed delivery jobs only after the issue is resolved.

## 29. Key Risks and Mitigations

### Risk: customer group link is forwarded

Mitigation:

- Require LINE authentication and active customer project membership.
- Do not treat possession of the URL as authorization.

### Risk: duplicate customer messages

Mitigation:

- Transactional outbox/delivery job.
- Stable LINE retry key.
- Idempotent worker.

### Risk: Admin changes source facts

Mitigation:

- Keep source submissions immutable after submit.
- Use change-request workflow.
- Separate customer draft from source facts.

### Risk: stale project assignments

Mitigation:

- Membership migration validation.
- Foreign-project existence check.
- Active-project filter.

### Risk: legacy Admin records receive excessive access

Mitigation:

- Normalize explicit roles before rollout.
- Require Owner approval for internal roles.
- Add role-audit report.

### Risk: AI hallucination

Mitigation:

- Deterministic fallback.
- Source references.
- Required human approval.
- Never let AI publish.

### Risk: large mobile uploads

Mitigation:

- Resumable direct GCS upload.
- Size/type limits.
- Upload retry and progress.
- Optional client-side compression for photos.

### Risk: Firestore document growth

Mitigation:

- Store media and events in separate collections.
- Store immutable versions separately.
- Avoid unbounded arrays.

### Risk: published report mutation

Mitigation:

- Immutable version collection.
- Backend update rejection.
- Correction version workflow.

### Risk: schedule differences among projects

Mitigation:

- Per-project timezone and working calendar.
- Global due scanner using stored next-action times.

## 30. Definition of Done

The MVP is complete only when:

- All active internal accounts have explicit roles.
- Project memberships are validated.
- Customer onboarding and approval work.
- Both LINE OA contexts are configured for beta and production.
- Subcontractors can submit only for assigned active projects.
- Multiple submissions consolidate into one report.
- Admin and Owner can review and publish.
- Source facts remain traceable and immutable.
- Customer-facing drafts are separately editable.
- Published versions are immutable.
- Corrections create new versions.
- Customer LINE delivery is idempotent.
- Customer links require authentication and membership.
- Customer acknowledgement includes the non-contractual disclaimer.
- Report-linked questions reach the project team.
- Reminders respect project schedule and timezone.
- No automatic customer publication exists.
- GCS media is private.
- Signed URLs require authorization.
- Firestore PITR/delete protection decisions are completed.
- Audit events cover submission, review, publication, correction, acknowledgement, and delivery.
- Lint/build/backend tests and manual LINE beta flows pass.
- Monitoring and rollback procedures are documented.

## 31. Recommended Implementation Order

1. Data cleanup and explicit Admin/Owner roles
2. Data contracts and state-transition rules
3. Project membership service and migration
4. Customer identity/access-request extension
5. Multi-LIFF and two-OA configuration
6. Daily project settings and cycle creation
7. Subcontractor submission APIs
8. Private media upload/finalization
9. Entire subcontractor responsive portal: Daily Report, Input, Profile, Sidebar, and Topbar
10. Consolidation and deterministic draft
11. Admin/Owner review queue and editor
12. Versioned approve-and-publish transaction
13. Customer portal
14. Customer LINE group binding and Flex delivery
15. Reminders and Scheduler/Task automation
16. Observability, security hardening, and beta pilot

This order establishes identity, authorization, and data integrity before building the visible workflow around them.
