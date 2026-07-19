# Phase 7 Scheduler Runbook

## Scope

Phase 7 automates Daily Report collection while keeping customer publication manual.

Implemented backend milestones:

| Default local time | Action |
|---|---|
| 06:00 | Create the project/date cycle and freeze the expected-subcontractor snapshot |
| 16:00 | Send the first Thai LINE reminder to missing subcontractors |
| 17:00 | Submission deadline |
| 17:15 | Mark missing reports overdue and create an Admin/Owner alert |
| 18:00 | Ensure a consolidated draft exists and create a draft-ready alert |
| 19:00 | Create a review-target alert without publishing |

The scanner uses each project's configured timezone. The default is `Asia/Bangkok`.
Repeated scans are idempotent: a completed notification milestone is not sent twice.
Automation starts only for projects that have a stored Daily Report settings document
with `enabled: true`; an unconfigured project is skipped.

## Project settings

The project settings API supports:

- `enabled`
- `timezone`
- `working_days` using ISO weekday numbers `1` through `7`
- `cycle_creation_time`
- `first_reminder_time`
- `submission_due_time`
- `overdue_grace_minutes`
- `draft_time`
- `review_target_time`
- `reminder_minutes_before`
- `expected_subcontractor_ids`

Admin/Owner can create and clear project no-work dates through:

```text
GET    /api/v1/daily-reports/projects/{project_id}/no-work-days
POST   /api/v1/daily-reports/projects/{project_id}/no-work-days
DELETE /api/v1/daily-reports/projects/{project_id}/no-work-days/{report_date}
```

## Internal endpoints

Cloud Scheduler uses OIDC to call:

```text
POST /api/v1/internal/daily-reports/create-due-cycles
POST /api/v1/internal/daily-reports/scan-due-actions
```

The legacy secret-protected endpoint remains available for compatibility:

```text
POST /api/v1/daily-reports/internal/deadline-tick
```

The internal endpoints reject ordinary RAYADEE user sessions. Authentication can use:

1. The configured Scheduler service-account OIDC identity; or
2. `X-Daily-Report-Task-Secret` for controlled compatibility testing.

Do not place the task secret in source code or Scheduler job metadata.

## Cloud configuration

Required Cloud Run environment variables:

```text
DAILY_REPORT_SCHEDULER_SERVICE_ACCOUNT
DAILY_REPORT_SCHEDULER_AUDIENCE
```

Optional compatibility configuration:

```text
DAILY_REPORT_INTERNAL_TASK_SECRET
```

The repository includes an idempotent configuration helper:

```bash
cd Projects-001-BE
PROJECT_ID=project001-489710 \
REGION=asia-southeast1 \
SERVICE_NAME=projects-001-be \
./scripts/configure_daily_report_scheduler.sh
```

The helper:

1. Resolves the Cloud Run service URL.
2. Creates the dedicated Scheduler service account if missing.
3. Adds the OIDC identity and audience to Cloud Run.
4. Creates or updates the global cycle-creation scan every 15 minutes.
5. Creates or updates the global due-action scan every 5 minutes.

Run the helper separately for demo/beta and production with the correct service name and project.
It does not deploy application source code.

## Verification

Before enabling a project:

- Confirm the project is active.
- Confirm Daily Report settings are enabled.
- Confirm expected subcontractors and LINE bindings.
- Confirm working days and no-work exceptions.
- Confirm the subcontractor LINE channel access token.
- Confirm Admin/Owner can see staff notifications.

After Scheduler configuration:

1. Force-run the cycle job in Cloud Scheduler.
2. Confirm one `daily_report_cycles` document was created for each eligible project/date.
3. Run the job again and confirm no duplicate cycle appears.
4. Temporarily use safe test times to verify reminder, overdue, draft, and review alerts.
5. Confirm the report remains `PENDING_REVIEW` until Admin/Owner publishes it.
6. Confirm completed, archived, disabled, non-working-day, and no-work projects create no new cycles.

## Pause and rollback

Pause both Scheduler jobs to stop new automated actions. Existing report data is not deleted.
Customer publication remains a separate explicit Admin/Owner action and is never triggered by
the Phase 7 scanner.
