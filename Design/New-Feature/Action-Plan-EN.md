# Inspection Feature Code Development Action Plan

This document defines the code development plan for the Inspection feature, based on `UX-Flow.md` and the confirmed product decisions.

## 1. Confirmed Decisions

- Reuse the existing system roles: Admin / Owner / Inspector / Subcontractor.
- Subcontractors can only see defects assigned to them.
- Subcontractors can update a defect only up to `Ready for Review`.
- The frontend must not access Firestore/GCS directly. All access goes through the FastAPI backend.
- Inspection always belongs to the existing `projectId`.
- One project can have multiple inspection rounds, and every defect must belong to a round.
- Zone / floor / room should be created inside Inspection for flexibility.
- GCS uses a private bucket with signed URLs.
- Files to support: before photos, after photos, plan images, and PDF reports in a future phase.
- MVP reports use frontend print/PDF first. The system will not generate and store PDF files in GCS during MVP.
- Keep lightweight report logs such as user, timestamp, project, round, and report type.
- Notifications are out of MVP, but the event model should support future Gmail notifications.

## 2. Target Architecture

```text
React Frontend
  -> API with existing session auth
FastAPI Backend
  - Auth / role / project permission checks
  - Firestore inspection documents
  - GCS private objects + signed URLs
```

Why the backend should act as the gateway:

- Reuses the current auth/session and permission logic.
- Prevents the frontend from holding GCP credentials.
- Lets the backend control signed URL expiration.
- Keeps audit timeline and status transition validation reliable.
- Allows future Gmail notification integration from the same backend event stream.

## 3. Proposed Firestore Data Model

Use top-level collections to make project-level, round-level, and subcontractor-level queries straightforward.

### 3.1 `inspection_rounds`

```json
{
  "id": "round_abc",
  "project_id": "project_001",
  "name": "Pre-handover Round 1",
  "description": "Inspection before first handover",
  "status": "ACTIVE",
  "started_at": "2026-06-16T08:00:00Z",
  "target_close_at": "2026-06-30T17:00:00Z",
  "created_by": "user_001",
  "created_at": "2026-06-16T08:00:00Z",
  "updated_at": "2026-06-16T08:00:00Z"
}
```

Status:

- `ACTIVE`
- `CLOSED`
- `ARCHIVED`

### 3.2 `inspection_zones`

```json
{
  "id": "zone_abc",
  "project_id": "project_001",
  "round_id": "round_abc",
  "name": "Level 4 - North Wing",
  "floor": "Level 4",
  "room": "North Wing",
  "sort_order": 10,
  "plan_file_id": "file_plan_abc",
  "created_by": "user_001",
  "created_at": "2026-06-16T08:05:00Z",
  "updated_at": "2026-06-16T08:05:00Z"
}
```

### 3.3 `inspection_defects`

```json
{
  "id": "defect_abc",
  "display_no": "DF-0001",
  "project_id": "project_001",
  "round_id": "round_abc",
  "zone_id": "zone_abc",
  "title": "Water leak in toilet ceiling",
  "description": "Water stain and active dripping found above the ceiling",
  "category": "Plumbing",
  "severity": "CRITICAL",
  "status": "OPEN",
  "assigned_subcontractor_id": "sub_001",
  "assigned_subcontractor_name": "Apex Builders",
  "due_date": "2026-06-24",
  "plan_x": 45.2,
  "plan_y": 30.4,
  "before_file_ids": ["file_before_001"],
  "after_file_ids": [],
  "created_by": "user_001",
  "created_at": "2026-06-16T08:10:00Z",
  "updated_at": "2026-06-16T08:10:00Z",
  "resolved_at": null
}
```

Status:

- `OPEN`
- `IN_PROGRESS`
- `READY_FOR_REVIEW`
- `RESOLVED`

Reopen behavior:

- There is no separate `REOPENED` status.
- If the inspector rejects the fix, move the defect from `READY_FOR_REVIEW` back to `IN_PROGRESS`.
- Record the timeline event as `REVIEW_REJECTED` or `REOPENED`.

### 3.4 `inspection_files`

```json
{
  "id": "file_before_001",
  "project_id": "project_001",
  "round_id": "round_abc",
  "defect_id": "defect_abc",
  "zone_id": "zone_abc",
  "kind": "BEFORE_PHOTO",
  "gcs_path": "gs://bucket/inspection/project_001/round_abc/defects/defect_abc/before/file.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 348120,
  "original_filename": "leak.jpg",
  "uploaded_by": "user_001",
  "uploaded_at": "2026-06-16T08:11:00Z"
}
```

Kinds:

- `PLAN_IMAGE`
- `BEFORE_PHOTO`
- `AFTER_PHOTO`
- `REPORT_PDF` in a later phase

### 3.5 `inspection_events`

```json
{
  "id": "event_abc",
  "project_id": "project_001",
  "round_id": "round_abc",
  "defect_id": "defect_abc",
  "event_type": "STATUS_CHANGED",
  "from_status": "OPEN",
  "to_status": "IN_PROGRESS",
  "comment": "Repair work has started",
  "actor_id": "user_001",
  "actor_role": "subcontractor",
  "created_at": "2026-06-16T09:00:00Z"
}
```

Event types:

- `DEFECT_CREATED`
- `STATUS_CHANGED`
- `ASSIGNED`
- `COMMENT_ADDED`
- `FILE_UPLOADED`
- `READY_FOR_REVIEW`
- `REVIEW_REJECTED`
- `RESOLVED`
- `REPORT_PRINTED`

### 3.6 `inspection_report_logs`

```json
{
  "id": "report_log_abc",
  "project_id": "project_001",
  "round_id": "round_abc",
  "report_type": "CONTRACTOR",
  "filters": {
    "status": ["OPEN", "IN_PROGRESS", "READY_FOR_REVIEW"],
    "severity": ["CRITICAL", "MAJOR"],
    "zone_id": "zone_abc"
  },
  "printed_by": "user_001",
  "printed_at": "2026-06-16T10:00:00Z"
}
```

## 4. GCS Object Layout

Private bucket. Object access must go through signed URLs only.

```text
inspection/
  {project_id}/
    {round_id}/
      plans/
        {zone_id}/{file_id}-{filename}
      defects/
        {defect_id}/
          before/{file_id}-{filename}
          after/{file_id}-{filename}
      reports/
        {report_id}.pdf
```

MVP uses only:

- `plans`
- `defects/before`
- `defects/after`

`reports` is reserved for a future phase.

## 5. Backend API Plan

Use this route prefix:

```text
/api/v1/inspection
```

### 5.1 Rounds

```text
GET    /api/v1/inspection/projects/{project_id}/rounds
POST   /api/v1/inspection/projects/{project_id}/rounds
GET    /api/v1/inspection/projects/{project_id}/rounds/{round_id}
PATCH  /api/v1/inspection/projects/{project_id}/rounds/{round_id}
```

Permission:

- Owner/Admin/Inspector: list/create/update
- Subcontractor: list only rounds that contain assigned defects

### 5.2 Zones

```text
GET    /api/v1/inspection/projects/{project_id}/rounds/{round_id}/zones
POST   /api/v1/inspection/projects/{project_id}/rounds/{round_id}/zones
PATCH  /api/v1/inspection/projects/{project_id}/rounds/{round_id}/zones/{zone_id}
```

Permission:

- Owner/Admin/Inspector: create/update
- Subcontractor: read only zones related to assigned defects

### 5.3 Defects

```text
GET    /api/v1/inspection/projects/{project_id}/rounds/{round_id}/defects
POST   /api/v1/inspection/projects/{project_id}/rounds/{round_id}/defects
GET    /api/v1/inspection/projects/{project_id}/rounds/{round_id}/defects/{defect_id}
PATCH  /api/v1/inspection/projects/{project_id}/rounds/{round_id}/defects/{defect_id}
POST   /api/v1/inspection/projects/{project_id}/rounds/{round_id}/defects/{defect_id}/status
POST   /api/v1/inspection/projects/{project_id}/rounds/{round_id}/defects/{defect_id}/comments
```

Query filters:

- `zone_id`
- `status`
- `severity`
- `category`
- `assigned_subcontractor_id`
- `search`
- `due_before`
- `overdue=true`

Permission:

- Owner/Admin/Inspector: full read/write
- Subcontractor: read only assigned defects
- Subcontractor allowed status transition: `OPEN` or `IN_PROGRESS` to `READY_FOR_REVIEW`
- Inspector/Admin/Owner can move `READY_FOR_REVIEW` to `RESOLVED`
- Inspector/Admin/Owner can move `READY_FOR_REVIEW` back to `IN_PROGRESS` with a review rejection comment

### 5.4 Files

```text
POST   /api/v1/inspection/projects/{project_id}/rounds/{round_id}/files
GET    /api/v1/inspection/files/{file_id}/signed-url
DELETE /api/v1/inspection/files/{file_id}
```

Upload form fields:

- `file`
- `kind`
- `zone_id`
- `defect_id`

Permission:

- Plan image upload: Owner/Admin/Inspector
- Before photo: Owner/Admin/Inspector
- After photo: Owner/Admin/Inspector/Subcontractor if assigned to the defect
- Signed URL: only users who can access the related round/defect

### 5.5 Summary / Report Log

```text
GET  /api/v1/inspection/projects/{project_id}/rounds/{round_id}/summary
POST /api/v1/inspection/projects/{project_id}/rounds/{round_id}/report-logs
GET  /api/v1/inspection/projects/{project_id}/rounds/{round_id}/report-logs
```

Summary response should return:

- total defects
- open defects
- in-progress defects
- ready-for-review defects
- resolved defects
- overdue count
- severity counts
- category counts
- contractor counts
- readiness score

## 6. Frontend Implementation Plan

### 6.1 API Client

Add inspection functions in `Projects-001-FE/src/api.js`:

- `getInspectionRounds(projectId)`
- `createInspectionRound(projectId, payload)`
- `getInspectionZones(projectId, roundId)`
- `createInspectionZone(projectId, roundId, payload)`
- `getInspectionDefects(projectId, roundId, filters)`
- `createInspectionDefect(projectId, roundId, payload)`
- `updateInspectionDefect(projectId, roundId, defectId, payload)`
- `updateInspectionDefectStatus(projectId, roundId, defectId, payload)`
- `uploadInspectionFile(projectId, roundId, formData)`
- `getInspectionFileSignedUrl(fileId)`
- `getInspectionSummary(projectId, roundId)`
- `createInspectionReportLog(projectId, roundId, payload)`

### 6.2 Project Detail Entry

Add a local section/tab inside `ProjectDetailPage`:

```text
Compare / BOQ
Warehouse Records
Inspection
```

MVP can render `InspectionWorkspace` inside Project Detail when the active tab is `inspection`.

### 6.3 Components

Create components under `Projects-001-FE/src/components/inspection/`:

- `InspectionWorkspace.jsx`
- `InspectionRoundPicker.jsx`
- `InspectionOverview.jsx`
- `InspectionMap.jsx`
- `InspectionDefectDrawer.jsx`
- `InspectionDefectForm.jsx`
- `InspectionDefectTable.jsx`
- `InspectionReportView.jsx`
- `InspectionFilePreview.jsx`
- `inspectionUtils.js`

### 6.4 UX Behavior

Desktop:

- Overview cards at the top
- Map/table/report local tabs
- Drawer for selected defect
- Right-side details panel on map view

Mobile/tablet:

- Sticky `Add Defect` action
- Full-width map
- Drawer becomes a bottom sheet or full-screen panel
- Camera/photo upload must be easy to reach

### 6.5 Role-Based UI

Owner/Admin/Inspector:

- Create round
- Create zone
- Upload plan
- Create/edit defect
- Assign subcontractor
- Verify resolved
- Reject review back to `IN_PROGRESS`
- Print reports

Subcontractor:

- View assigned defects only
- Add comment
- Upload after photo
- Change status to `READY_FOR_REVIEW`
- Cannot resolve
- Cannot see unrelated defects

## 7. Status Transition Rules

```text
OPEN -> IN_PROGRESS
OPEN -> READY_FOR_REVIEW
IN_PROGRESS -> READY_FOR_REVIEW
READY_FOR_REVIEW -> RESOLVED
READY_FOR_REVIEW -> IN_PROGRESS
```

Rules:

- `READY_FOR_REVIEW -> RESOLVED` is allowed only for Inspector/Admin/Owner.
- `READY_FOR_REVIEW -> IN_PROGRESS` requires a rejection comment.
- Subcontractors can only move an assigned defect to `READY_FOR_REVIEW`.
- Every status transition writes an `inspection_events` record.

## 8. Readiness Score

MVP calculation can stay simple:

```text
readiness = resolved defects / total defects
```

Suggested weighted version:

```text
Critical open = heavy penalty
Major open = medium penalty
Minor/Cosmetic open = light penalty
Overdue = extra penalty
```

Initial implementation:

- Start with a count-based score for predictability.
- Surface blockers separately: open critical items, overdue items, and ready-for-review items waiting for approval.

## 9. Development Phases

### Phase 0: Spec Finalization

- Finalize Firestore collection names.
- Finalize API path names.
- Finalize role naming for Inspector if the role does not exist yet.
- Confirm the GCS bucket env var name.
- Confirm the default signed URL expiration.

Deliverable:

- Backend/FE implementation checklist ready.

### Phase 1: Backend Foundation

- Add Firestore inspection service.
- Add GCS inspection file service using the existing private/signed URL pattern.
- Add schemas for rounds, zones, defects, files, events, and report logs.
- Add inspection router under `/api/v1/inspection`.
- Implement permission helpers.
- Implement status transition validator.
- Implement summary aggregation.

Verification:

- Create round.
- Create zone.
- Upload plan image.
- Create defect.
- Upload before/after photo.
- Generate signed URL.
- Verify subcontractor only sees assigned defects.

### Phase 2: Frontend Project Detail Integration

- Add local `Inspection` tab in `ProjectDetailPage`.
- Add API client functions.
- Add `InspectionWorkspace`.
- Add round picker and create round flow.
- Add overview summary cards.
- Add empty states.

Verification:

- Open project detail.
- Switch to Inspection.
- Create/select round.
- Summary loads without breaking BOQ/warehouse views.

### Phase 3: Map + Defect Capture

- Add zone management.
- Add plan upload.
- Render plan image with pins.
- Add defect from map coordinate.
- Add defect drawer.
- Add before photo upload.

Verification:

- Create zone.
- Upload plan.
- Click map to create defect.
- Pin appears at the correct coordinate.
- Defect detail shows signed photo preview.

### Phase 4: Defect Register + Workflow

- Add table with filters.
- Add role-based actions.
- Add status update flow.
- Add after photo upload.
- Add review rejection flow.
- Add timeline/events panel.

Verification:

- Admin creates and assigns defect.
- Subcontractor sees only assigned defect.
- Subcontractor uploads after photo and marks `READY_FOR_REVIEW`.
- Inspector resolves or rejects.

### Phase 5: Reports + Print Log

- Add Client / Contractor / Management report views.
- Add report filters.
- Add print button.
- Add `REPORT_PRINTED` event or `inspection_report_logs` record.

Verification:

- Print report from frontend.
- Log contains user, project, round, report type, filters, and timestamp.
- Report respects current filters.

### Phase 6: Hardening

- Loading/error states.
- Responsive QA.
- Accessibility pass.
- Empty states.
- File size/type validation.
- Pagination or virtualized table if needed.
- Build/lint verification.

Verification:

- `npm run lint`
- `npm run build`
- Manual role-based flows
- Signed URL expiry behavior

## 10. Future Phase Hooks

Keep these out of MVP, but design the data so they can be added later:

- Gmail notifications for assignment, overdue, ready for review, and rejected review.
- Saved PDF reports in GCS.
- Cross-project inspection dashboard.
- Offline draft support for site inspection.
- BOQ/WBS linking.
- LINE notification if needed later.
- AI recommendation based on defect history.

## 11. Key Risks

- Firestore query/index design: subcontractor assigned-defect queries need indexes.
- File privacy: signed URLs must be generated only after permission checks.
- Status integrity: the frontend must not be trusted; the backend must validate transitions.
- Report print logs: frontend print can only confirm print intent, not actual print completion.
- Role model: `Inspector` needs a clear mapping if it is not already present in auth/session.
- Large floor plans: image size and mobile performance need constraints.

## 12. Implementation Order Recommendation

Start with backend data/API contracts first, then frontend:

1. Firestore/GCS service and API skeleton
2. Round + zone CRUD
3. Defect CRUD + status events
4. File upload + signed URL
5. Frontend Inspection tab and overview
6. Map pin capture
7. Register/table workflow
8. Report print and logs

This order avoids building UI around mock state that later does not match the backend permission and status model.
