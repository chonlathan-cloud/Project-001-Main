# Application Flow: Projects-001 Subcontractor LINE/LIFF Portal

This document describes the current subcontractor-side flow based on the repository code and product documents.

The implemented subcontractor experience is intentionally smaller than the Admin portal. After login, a subcontractor sees only:

- `Input`
- `Profile`

The long-term business specs also mention personal bill history and advance requests. The backend contains early endpoints for those flows, but the current React app does not expose them as subcontractor pages yet.

## 1. Entry Point and Role Boundary

Subcontractors enter through the same public login screen as Admin users.

```text
/login
  -> Continue as Subcontractor with LINE
  -> LINE LIFF login
  -> /auth/line/callback
  -> backend /api/v1/auth/line-login
```

If the LINE account is already bound to a subcontractor profile, the backend returns a subcontractor session and the frontend redirects to `/input`.

If the LINE account is not found, the backend returns `REQUIRE_SIGNUP` and the frontend redirects to `/signup`.

Role behavior:

- Missing session token redirects to `/login`.
- Internal-only routes redirect subcontractors back to the subcontractor post-login path.
- Subcontractor sidebar navigation contains only `Input` and `Profile`.
- Subcontractor post-login path is `/input`.

Important files:

- `Projects-001-FE/src/LoginPage.jsx`
- `Projects-001-FE/src/LineCallbackPage.jsx`
- `Projects-001-FE/src/liffClient.js`
- `Projects-001-FE/src/auth.js`
- `Projects-001-FE/src/App.jsx`
- `Projects-001-FE/src/components/Sidebar.jsx`
- `Projects-001-BE/app/api/v1/auth.py`
- `Projects-001-BE/app/api/deps/auth.py`

## 2. LINE Login Flow

### State 1: Login Page

- **UI:** Login card with two actions: Admin Google login and Subcontractor LINE login.
- **Action:** `[Continue as Subcontractor with LINE]`.
- **Frontend:** `beginLineLogin()` initializes LIFF using `VITE_LINE_LIFF_ID`.
- **Redirect:** If LIFF is not already logged in, LINE redirects back to `/auth/line/callback`.

### State 2: LINE Callback

```text
LineCallbackPage
  -> getActiveLineAccessToken()
  -> lineLogin()
  -> POST /api/v1/auth/line-login
```

Backend behavior:

- Calls LINE profile API using the LINE access token.
- Reads `userId`, display name, and LINE avatar URL.
- Searches Firestore `users` by `line_uid`.
- If found, issues an HMAC session token with role `subcontractor`.
- If not found, returns `REQUIRE_SIGNUP`.

### State 3: Returning Subcontractor

```text
Backend session response
  -> saveAuthSession()
  -> resolvePostLoginPath(user)
  -> /input
```

Session payload includes:

- `role = subcontractor`
- `display_name`
- `subcontractor_id`
- `line_uid`

## 3. First-Time Signup and KYC

First-time subcontractors complete `/signup` after LINE login.

### Signup Form Fields

- Company / Subcontractor Name
- Default Contact Name
- Default Phone Number
- Tax Identification Number
- Default Bank Name
- Default Account Number
- Default Account Name
- KYC ID Card Image

### Signup Flow

```text
/signup
  -> hydrate LINE profile from pending auth or active LIFF profile
  -> user fills KYC/contact/bank form
  -> POST /api/v1/auth/sign-up
  -> upload KYC image to private GCS storage
  -> create Firestore users/{subcontractor_id}
  -> issue subcontractor session token
  -> redirect to /input
```

Created Firestore profile defaults:

- `line_uid` is bound to the LINE account.
- `line_picture_url` is saved if available.
- `assigned_project_ids` starts as an empty list.
- `vat_rate` defaults to `0.07`.
- `wht_rate` defaults to `0.03`.
- `retention_rate` defaults to `0.05`.
- `bank_account` stores the default bank values.
- `kyc_gcs_path` stores the private GCS object reference.

KYC storage rule:

- KYC images are stored in private GCS.
- Admin viewing uses a short-lived signed URL through Settings.
- The subcontractor profile photo is separate from the KYC document.

Important files:

- `Projects-001-FE/src/SignUpPage.jsx`
- `Projects-001-BE/app/api/v1/auth.py`
- `Projects-001-BE/app/services/identity_service.py`
- `Projects-001-BE/app/services/gcs_storage_service.py`

## 4. Subcontractor Navigation Shell

After authentication, subcontractors use `ProtectedLayout` with the shared sidebar.

Subcontractor sidebar:

```text
Input      -> /input
Profile    -> /profile/me
Sign Out   -> clears local session and LINE client session
```

Subcontractors do not see:

- Dashboard
- Project
- Insights
- Approval
- Chat AI
- Setting

This is enforced primarily by frontend route grouping and backend dependencies on sensitive endpoints.

## 5. Input Page Flow

The `Input` page is the main subcontractor work surface. It is used to submit income or expense requests with a receipt image/PDF.

### State 1: Load Page Context

```text
InputPage
  -> GET /api/v1/input/projects
  -> GET /api/v1/input/defaults
```

Project dropdown behavior:

- For subcontractors, `/api/v1/input/projects` reads the Firestore profile.
- Only projects in `assigned_project_ids` are returned.
- If no projects are assigned, the page shows a warning telling the user to ask Admin to set Assigned Projects.

Default values:

- Contact name
- Phone number
- Bank name
- Account number
- Account name

These are loaded from the subcontractor Firestore profile and prefilled in the form.

### State 2: Upload Receipt

Supported upload types:

- Image files
- PDF files

Frontend flow:

```text
User selects file
  -> local preview is created
  -> POST /api/v1/input/receipt-extract
  -> Gemini OCR returns suggested values
  -> frontend fills empty form fields
```

OCR result can fill:

- Suggested entry type
- Vendor / shop name
- Receipt number
- Document date
- Suggested request type
- Total amount
- Line items
- Low-confidence fields

The user must review and correct the OCR values before submitting.

### State 3: Fill Input Request Form

Main fields:

- Entry type: `EXPENSE` or `INCOME`
- Project
- Requester name
- Phone
- Request date
- Receipt number
- Document date
- Work type
- Request type
- Vendor / shop name
- Note
- Bank name
- Amount
- Account number
- Account name

Work type options:

- `งานโครงสร้าง`
- `งานสถาปัตย์`
- `งานระบบ`
- `งานบริหารโครงการ`

Request type options:

- `ค่าวัสดุ`
- `ค่าแรง`
- `ค่าเบิกล่วงหน้า`
- `ค่าใช้จ่ายทั่วไป`

Business rules:

- Amount must be greater than 0.
- Project is required.
- Requester name is required.
- A receipt file is required.
- `ค่าเบิกล่วงหน้า` is allowed only when entry type is `EXPENSE`.
- Subcontractors can submit only to assigned projects.

### State 4: Upload Receipt to Temporary Storage

```text
Submit clicked
  -> POST /api/v1/input/receipt-upload
  -> GCS temp object is created under temp bills prefix
  -> frontend receives gs:// storage key
```

The temporary file is linked to the request during final submission.

### State 5: Create Input Request

```text
POST /api/v1/input/requests
  -> validate project exists
  -> verify assigned project for subcontractor
  -> validate business rules
  -> create input_requests row in PostgreSQL
  -> detect duplicates
  -> status = PENDING_ADMIN
```

Duplicate detection rule:

```text
Receipt No. + Document Date + Amount
```

Duplicate detection does not block submission. It flags the request for Admin review.

### State 6: Submission Result

After successful submission, the page shows:

- Request ID
- Project name
- Entry type
- Requester
- Vendor
- Receipt number
- Document date
- Amount
- Status
- Duplicate warning, if detected
- OCR low-confidence warning, if present
- Receipt preview through a signed URL

Receipt preview flow:

```text
GET /api/v1/input/requests/{request_id}/receipt-url
  -> verify current subcontractor owns the request
  -> generate short-lived signed GCS URL
```

Important files:

- `Projects-001-FE/src/InputPage.jsx`
- `Projects-001-FE/src/api.js`
- `Projects-001-BE/app/api/v1/input_requests.py`
- `Projects-001-BE/app/schemas/input_schema.py`
- `Projects-001-BE/app/models/input_request.py`
- `Projects-001-BE/app/services/ai_service.py`
- `Projects-001-BE/app/services/gcs_storage_service.py`

## 6. Request Status Lifecycle

Subcontractor-created input requests start at `PENDING_ADMIN`.

Current lifecycle:

```text
PENDING_ADMIN
  -> APPROVED
  -> PAID

PENDING_ADMIN
  -> REJECTED
```

Owner can edit reviewable requests before approval. Limited Admin can view/review the queue but cannot mutate request data:

```text
DRAFT / PENDING_ADMIN / REJECTED
  -> owner edits fields
  -> duplicate detection reruns
```

Status meanings:

- `PENDING_ADMIN`: submitted and waiting for internal review.
- `APPROVED`: reviewed and approved by Owner.
- `PAID`: approved request has been marked paid by Owner.
- `REJECTED`: Owner rejected the request and recorded a review note.

Current UI note:

- The Input page shows the result immediately after submission.
- The backend supports listing the current user's input requests through `GET /api/v1/input/requests`.
- A dedicated subcontractor status-history page or timeline is not yet implemented in the current frontend.

## 7. Profile Flow

Subcontractors open Profile from `/profile/me`.

```text
ProfilePage
  -> fetchData('profile')
  -> GET /api/v1/profile/me
```

Profile content:

- Avatar or initials
- Subcontractor name
- Contact name
- Phone
- Tax ID context
- Role
- Timezone
- LINE UID
- Assigned project IDs
- Bank account
- Activity stats
- Request activity chart

Subcontractor stats are calculated from their own `input_requests`:

- Pending approvals
- Approved or paid requests
- Total requests
- VAT rate
- Approved amount

Avatar actions:

```text
Change Photo
  -> POST /api/v1/profile/me/avatar
  -> upload image to private GCS profile prefix
  -> return signed URL

Use LINE Avatar
  -> DELETE /api/v1/profile/me/avatar
  -> clear custom avatar storage key
  -> fall back to LINE avatar or initials
```

Important files:

- `Projects-001-FE/src/ProfilePage.jsx`
- `Projects-001-BE/app/api/v1/profile.py`
- `Projects-001-BE/app/services/identity_service.py`
- `Projects-001-BE/app/services/gcs_storage_service.py`

## 8. Admin Dependencies for Subcontractor Success

Subcontractor usability depends on internal setup in Settings.

Settings controls:

- Subcontractor name
- Contact name
- Phone
- Tax ID
- VAT rate
- WHT rate
- Retention rate
- Active/inactive state
- Assigned Projects
- Bank account
- KYC signed URL viewing
- LINE binding reset

Critical dependency:

```text
Assigned Projects in Setting
  -> controls which projects appear in subcontractor Input dropdown
```

If `assigned_project_ids` is empty, the subcontractor cannot submit a request because no project can be selected.

LINE recovery:

```text
Owner clicks Reset LINE Binding
  -> backend clears users/{subcontractor_id}.line_uid
  -> subcontractor can bind a new LINE account through login/signup flow
```

Important files:

- `Projects-001-FE/src/SettingPage.jsx`
- `Projects-001-BE/app/api/v1/settings.py`
- `Projects-001-BE/app/services/identity_service.py`

## 9. Security and Data Access

Authentication:

- Subcontractors use LINE LIFF.
- Backend issues a signed session token.
- Frontend stores the session token in local storage.
- `src/api.js` sends `Authorization: Bearer <session_token>` on API requests.

Backend access controls:

- `get_current_user` requires a valid session token.
- `require_subcontractor_user` restricts subcontractor-only endpoints.
- `require_admin_user` restricts admin-only endpoints.

Subcontractor data isolation:

- Project options are filtered by `assigned_project_ids`.
- Input request creation verifies the selected project is assigned.
- Input request listing filters to the current `subcontractor_id`.
- Receipt signed URL access checks request ownership.
- KYC image viewing is Owner/Admin internal-only.
- Settings and Approval read endpoints are Owner/Admin internal-only; mutation endpoints are Owner-only.

Private storage areas:

- KYC files: private GCS KYC prefix.
- Input receipt temp files: private GCS temp bills prefix.
- Approved receipt files: private GCS permanent bills prefix.
- Profile avatars: private GCS profile prefix.

## 10. Backend API Map

| Flow | Endpoint | Role | Purpose |
| --- | --- | --- | --- |
| LINE login | `POST /api/v1/auth/line-login` | Public LINE token | Verify LINE profile and return session or signup requirement. |
| Signup | `POST /api/v1/auth/sign-up` | Public after LINE identity | Create subcontractor profile and KYC file. |
| Current session | `GET /api/v1/auth/me` | Authenticated | Return current session user. |
| Input projects | `GET /api/v1/input/projects` | Authenticated | Return project dropdown options, filtered for subcontractors. |
| Input defaults | `GET /api/v1/input/defaults` | Authenticated | Prefill contact and bank values from profile. |
| Receipt OCR | `POST /api/v1/input/receipt-extract` | Authenticated | Extract receipt fields with Gemini. |
| Receipt upload | `POST /api/v1/input/receipt-upload` | Authenticated | Upload receipt to temp GCS storage. |
| Submit request | `POST /api/v1/input/requests` | Authenticated | Create `PENDING_ADMIN` input request. |
| My requests | `GET /api/v1/input/requests` | Authenticated | List requests scoped to current subcontractor. |
| Receipt preview | `GET /api/v1/input/requests/{request_id}/receipt-url` | Owner/Admin-aware | Generate signed receipt URL for internal review. |
| Profile | `GET /api/v1/profile/me` | Authenticated | Return current user's profile dashboard data. |
| Profile avatar | `POST /api/v1/profile/me/avatar` | Subcontractor | Upload custom profile avatar. |
| Reset avatar | `DELETE /api/v1/profile/me/avatar` | Subcontractor | Use LINE avatar/default initials. |
| Legacy my bills | `GET /api/v1/subcontractor/my-bills` | Subcontractor | Return installment-backed bill history. No current FE page. |
| Legacy advance | `POST /api/v1/subcontractor/installments/{installment_id}/advance` | Subcontractor | Split installment up to 50%. No current FE page. |

## 11. Legacy and Planned Subcontractor Flows

The repository includes a legacy/early subcontractor portal backend:

```text
GET /api/v1/subcontractor/my-bills
POST /api/v1/subcontractor/installments/{installment_id}/advance
```

Implemented behavior:

- `my-bills` reads `Installment` rows for the authenticated subcontractor.
- `advance` calls `process_advance_request`.
- Advance percent must be greater than 0 and less than or equal to 50.
- The original installment is split into an advance row and remaining locked row.

Current gap:

- There is no active React page linked from the subcontractor sidebar for bill history or advance request.
- The main implemented subcontractor workflow is the `Input` request flow.

Related backlog:

- Add subcontractor request history or status timeline.
- Add notifications for approve/reject/paid.
- Connect approved input requests deeper into finance transactions if the business wants them counted as real project cost immediately.
- Add audit trail for submit/review/approve/reject/paid.
- Add production scheduler for temp receipt cleanup.

## 12. End-to-End Subcontractor Journey

### First-Time Subcontractor

```text
Open app from LINE
  -> /login
  -> Continue as Subcontractor with LINE
  -> LINE callback
  -> backend returns REQUIRE_SIGNUP
  -> /signup
  -> fill KYC/contact/bank profile
  -> upload KYC image
  -> backend creates Firestore profile
  -> session saved
  -> /input
```

### Returning Subcontractor Submits a Request

```text
Open app
  -> LINE login
  -> backend finds line_uid
  -> /input
  -> load assigned projects and defaults
  -> upload receipt image/PDF
  -> OCR extracts values
  -> user reviews and corrects fields
  -> upload receipt to temp GCS
  -> create input request
  -> status becomes PENDING_ADMIN
  -> show request summary and receipt preview
```

### Internal User Reviews Request

Limited Admin can open Approval and inspect request data/receipt preview. Owner completes the mutation lifecycle.

```text
Owner opens Approval
  -> sees PENDING_ADMIN request
  -> previews receipt with signed URL
  -> edits fields if needed
  -> approve or reject
  -> approved request can be marked paid
```

### Subcontractor Manages Profile

```text
/profile/me
  -> view profile and request stats
  -> upload custom avatar
  -> or reset to LINE avatar
```

## 13. Empty and Error States

Important subcontractor-facing states:

- Missing session token: redirect to `/login`.
- LINE token invalid or expired: login error.
- First-time LINE account: redirect to `/signup`.
- Missing LINE identity on signup: user must restart from LINE login.
- Missing KYC image on signup: signup blocks submission.
- No assigned projects: Input page disables project selection and shows warning.
- Unsupported receipt type: OCR endpoint rejects non-image/non-PDF files.
- Empty receipt file: upload/extract endpoint rejects the request.
- OCR low confidence: page warns but allows manual correction.
- Duplicate candidate: page warns after submission; an internal user reviews and Owner mutates if needed.
- Unauthorized receipt URL: backend rejects if the request belongs to another subcontractor.

## 14. Current Implementation Status

Implemented:

- LINE LIFF login and callback.
- First-time subcontractor signup with KYC upload.
- Subcontractor-only sidebar items.
- Assigned-project filtering for Input.
- Profile defaults for Input form.
- Receipt OCR, local preview, temp upload, and signed preview.
- Input request creation with duplicate flagging.
- Request status lifecycle through Admin Approval.
- Subcontractor profile data and avatar upload/reset.
- Private GCS storage for KYC, receipts, and profile images.

Partially implemented or not yet surfaced in UI:

- Subcontractor request history page.
- Subcontractor bill history page.
- Advance request page.
- Notifications when request status changes.
- Audit timeline for each request.
- Full finance transaction integration for approved input requests.
