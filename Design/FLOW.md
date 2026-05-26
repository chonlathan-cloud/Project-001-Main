# Project Flow

This document describes the current implementation flow for `Projects-001`.
It is based on the repository code and the existing product/design documents.

## 1. Product Summary

`Projects-001` is a construction management system for internal project finance, BOQ tracking, subcontractor input, approval, insight reporting, and AI-assisted analysis.

The system has two main user groups:

- Admin / Project Manager: manages projects, BOQs, approvals, subcontractors, dashboard, insights, settings, and AI chat.
- Subcontractor: signs in through LINE LIFF, registers profile/KYC, submits income or expense input requests, and views their own profile/input flow.

The app is currently split into:

- `Projects-001-FE`: React + Vite frontend.
- `Projects-001-BE`: FastAPI backend.
- Root documents: business requirements, architecture, API/DB specs, LLD, deployment checklist, walkthroughs, and user manuals.

## 2. Runtime Architecture

High-level runtime flow:

```text
Browser / LINE LIFF
  -> React frontend
  -> src/api.js
  -> FastAPI backend /api/v1/*
  -> PostgreSQL / Firestore / Google Cloud Storage / Vertex AI / Google Sheets
```

Main technology choices:

- Frontend: React, Vite, React Router, Firebase client auth, LINE LIFF client.
- Backend: FastAPI, SQLAlchemy async, Pydantic v2.
- SQL database: PostgreSQL, including pgvector support for BOQ embeddings.
- NoSQL directory/profile store: Firestore.
- File storage: Google Cloud Storage private bucket.
- AI: Vertex AI Gemini through `google-genai`.
- External data source: Google Sheets API for BOQ sync.

## 3. Repository Layout

```text
Projects-001/
  00_INSTRUCTION.md
  01_Business_Requirements.md
  02_HLD_Architecture.md
  03_TDD_API_DB_Spec.md
  04_LLD_Implementation.md
  05_Input_Page_Backlog.md
  docs/
    User_Manual_Admin.md
    User_Manual_Subcontractor.md
  Projects-001-FE/
    src/
      App.jsx
      api.js
      auth.js
      firebaseClient.js
      liffClient.js
      *Page.jsx
      components/
  Projects-001-BE/
    main.py
    app/
      api/v1/
      api/deps/
      core/
      models/
      schemas/
      services/
    scripts/
```

## 4. Shared API Response Shape

Most backend APIs return:

```json
{
  "status": "success",
  "data": {}
}
```

The frontend centralizes API calls in `Projects-001-FE/src/api.js`.
That file:

- Reads the backend URL from `VITE_API_BASE_URL`.
- Falls back to `http://localhost:8000`.
- Adds `Authorization: Bearer <session_token>` when a session exists.
- Unwraps `{ status, data }`.
- Normalizes backend payloads into UI-friendly shapes.

## 5. Frontend Routing Flow

Frontend routing is defined in `Projects-001-FE/src/App.jsx`.

Public routes:

| Route | Page | Purpose |
| --- | --- | --- |
| `/login` | `LoginPage` | Admin Google login or subcontractor LINE login entry. |
| `/signup` | `SignUpPage` | Subcontractor KYC/profile registration after LINE login. |
| `/auth/line/callback` | `LineCallbackPage` | Completes LINE login redirect flow. |

Protected admin routes:

| Route | Page | Purpose |
| --- | --- | --- |
| `/` | `DashboardPage` | Financial overview and attention items. |
| `/project` | `ProjectPage` | Project list, create/rename project, BOQ sync. |
| `/project/detail/:projectId` | `ProjectDetailPage` | BOQ comparison, project execution summary, linked warehouse records. |
| `/insights` | `InsightsPage` | Unified warehouse table, filters, export. |
| `/approval` | `ApprovalPage` | Admin review queue for input requests. |
| `/chat-ai` | `ChatAIPage` | Strategic AI chat and chat history. |
| `/profile` | `ProfilePage` | Admin profile. |
| `/setting` | `SettingPage` | Subcontractor/admin directory and KYC viewing. |

Protected shared/subcontractor routes:

| Route | Page | Purpose |
| --- | --- | --- |
| `/input` | `InputPage` | Submit income/expense input request with receipt OCR/upload. |
| `/profile/me` | `ProfilePage` | Subcontractor profile. |

`ProtectedLayout` checks local session state:

- Missing session token -> redirect to `/login`.
- Admin-only route with non-admin user -> redirect to the user's post-login path.
- Admin users see the full sidebar.
- Subcontractors see only Input and Profile.

## 6. Authentication Flow

### 6.1 Admin Login

Frontend:

```text
LoginPage
  -> signInAdminWithGooglePopup()
  -> adminLogin()
  -> saveAuthSession()
  -> redirect to "/"
```

Backend:

```text
POST /api/v1/auth/admin-login
  -> verify Firebase ID token when provided
  -> check email against Firestore admin directory or configured admin allowlist/domain
  -> issue HMAC-signed session token
  -> optionally create Firebase custom token
```

Important files:

- `Projects-001-FE/src/LoginPage.jsx`
- `Projects-001-FE/src/firebaseClient.js`
- `Projects-001-FE/src/auth.js`
- `Projects-001-BE/app/api/v1/auth.py`
- `Projects-001-BE/app/core/security.py`
- `Projects-001-BE/app/services/identity_service.py`

### 6.2 Subcontractor LINE Login and Signup

Frontend:

```text
LoginPage
  -> beginLineLogin()
  -> LINE redirects to /auth/line/callback
  -> LineCallbackPage calls lineLogin()
```

Backend:

```text
POST /api/v1/auth/line-login
  -> call LINE profile API
  -> find Firestore user by line_uid
  -> if found, issue subcontractor session token
  -> if not found, return REQUIRE_SIGNUP
```

If signup is required:

```text
SignUpPage
  -> collect KYC, bank, contact, tax, and LINE profile data
  -> POST /api/v1/auth/sign-up
  -> upload KYC image to GCS if attached
  -> create Firestore user profile
  -> issue subcontractor session token
```

Important files:

- `Projects-001-FE/src/liffClient.js`
- `Projects-001-FE/src/LineCallbackPage.jsx`
- `Projects-001-FE/src/SignUpPage.jsx`
- `Projects-001-BE/app/api/v1/auth.py`
- `Projects-001-BE/app/services/gcs_storage_service.py`
- `Projects-001-BE/app/services/identity_service.py`

## 7. Backend Router Map

All backend v1 routers are mounted from `Projects-001-BE/main.py` under `/api/v1`.

| Router | Prefix | Main Purpose |
| --- | --- | --- |
| `auth.py` | `/api/v1/auth` | Admin login, LINE login, signup, session user. |
| `dashboard.py` | `/api/v1/dashboard` | KPI, cashflow, risk, recent actions. |
| `projects.py` | `/api/v1/projects` | Project CRUD, BOQ tree, BOQ sync/tabs/jobs. |
| `input_requests.py` | `/api/v1/input` | Input request OCR/upload/submit/review lifecycle. |
| `insights.py` | `/api/v1/insights` | Warehouse rows, summary, filters, export. |
| `chat.py` | `/api/v1/chat` | AI chat, chat history. |
| `profile.py` | `/api/v1/profile` | Current profile and avatar upload/reset. |
| `settings.py` | `/api/v1/settings` | Subcontractors, admins, KYC signed URL, LINE reset. |
| `subcontractor.py` | `/api/v1/subcontractor` | My bills and advance request flow. |
| `bills.py` | `/api/v1/bills` | Older bills/installments approval flow. |

Health check:

```text
GET /health
```

## 8. Data Stores and Models

### 8.1 PostgreSQL Models

Primary SQL models:

- `Project`: project master data and project-level financial percentages.
- `BOQItem`: customer/subcontractor BOQ rows, WBS hierarchy, material/labor split, SCD versioning, optional vector embedding.
- `Installment`: installment/customer-side due items and subcontractor-side payable items.
- `Transaction`: approved financial payment records with VAT/WHT/retention/net payable.
- `InputRequest`: general income/expense request submitted through the Input page.
- `ChatHistory`: persisted AI chat exchange snapshots.

Important files:

- `Projects-001-BE/app/models/boq.py`
- `Projects-001-BE/app/models/finance.py`
- `Projects-001-BE/app/models/input_request.py`
- `Projects-001-BE/app/models/chat_history.py`

### 8.2 Firestore

Firestore is used for identity/directory style data:

- `users`: subcontractor profiles, LINE binding, KYC storage path, financial rates, bank account, assigned projects.
- `admins`: admin directory and active/inactive access control.

Important file:

- `Projects-001-BE/app/services/identity_service.py`

### 8.3 Google Cloud Storage

GCS stores private files:

- KYC images under the configured KYC prefix.
- Profile images under the configured profile prefix.
- Temporary input receipts under the temp bills prefix.
- Approved/permanent receipts under the permanent bills prefix.

The backend exposes signed URLs for controlled preview access.

Important file:

- `Projects-001-BE/app/services/gcs_storage_service.py`

## 9. Core End-to-End Flows

### 9.1 Dashboard Flow

Frontend:

```text
DashboardPage
  -> getDashboardData()
  -> GET /api/v1/dashboard/summary
```

Backend aggregates:

- Project `contingency_budget` values as the current dashboard total budget.
- Transaction base amounts as actual cost.
- Pending input request count.
- Overdue installment amount.
- Monthly income from installments.
- Monthly expense from transactions.
- Top risky projects from overdue installments and pending input requests.
- Recent approved transactions/input requests.

Output feeds dashboard KPI cards, budget breakdown, cashflow charts, attention items, risky projects, and recent actions.

### 9.2 Project Creation and BOQ Sync Flow

Frontend:

```text
ProjectPage
  -> GET /api/v1/projects
  -> POST /api/v1/projects for new project
  -> PUT /api/v1/projects/{project_id} for rename/update
```

BOQ sync flow:

```text
Admin opens sync drawer
  -> enters Google Sheet URL
  -> POST /api/v1/projects/boq/tabs
  -> select syncable workbook tabs
  -> POST /api/v1/projects/boq/sync-batch
  -> frontend polls GET /api/v1/projects/boq/sync-jobs/{job_id}
```

Backend BOQ sync flow:

```text
Google Sheet URL
  -> extract spreadsheet ID
  -> get ADC Google access token
  -> fetch sheet tabs or rows through Google Sheets API
  -> clean duplicate/header rows
  -> send raw rows to Gemini for BOQ/WBS/material-labor parsing
  -> normalize parsed rows
  -> close previous current BOQ version by setting valid_to
  -> insert new current BOQ version with valid_from and valid_to = NULL
```

Important implementation details:

- Current multi-tab sync is handled by an in-memory background job store.
- Configured `BOQ_BATCH_SYNC_MAX_TABS` limits how many tabs can be queued per batch.
- `summary` and `work detail` tabs are treated as non-syncable.
- Existing BOQ rows are versioned using SCD Type 2 behavior.

Important files:

- `Projects-001-FE/src/ProjectPage.jsx`
- `Projects-001-BE/app/api/v1/projects.py`
- `Projects-001-BE/app/services/boq_sync_service.py`
- `Projects-001-BE/app/services/boq_sync_job_service.py`
- `Projects-001-BE/app/services/ai_service.py`

### 9.3 Project Detail and BOQ Comparison Flow

Frontend:

```text
ProjectDetailPage
  -> getProjectDetailData(projectId)
  -> GET /api/v1/projects/{project_id}
  -> GET /api/v1/projects/{project_id}/boq
  -> GET /api/v1/insights/rows for project-level installment/transaction rows
```

Backend returns:

- Basic project fields.
- Customer BOQ tree.
- Subcontractor BOQ tree.
- Compare tree.
- Compare summary.
- WBS summary.
- Execution summary from installments, transactions, and input requests.

Comparison logic:

- Customer and subcontractor BOQ nodes are grouped by sheet name, WBS level, item number, and description.
- Matched rows produce variance and margin percent.
- Customer-only and subcontractor-only rows are flagged separately.
- Top-level WBS rows feed the chart summaries.

The page supports deep links from Insight Warehouse:

```text
/project/detail/{project_id}?source=installment&installment_id={id}
/project/detail/{project_id}?source=transaction&transaction_id={id}
```

### 9.4 Input Request Submission Flow

Frontend:

```text
InputPage
  -> GET /api/v1/input/projects
  -> GET /api/v1/input/defaults
  -> user uploads receipt image/PDF
  -> POST /api/v1/input/receipt-extract
  -> frontend fills form using OCR result
  -> POST /api/v1/input/receipt-upload
  -> POST /api/v1/input/requests
  -> GET /api/v1/input/requests/{request_id}/receipt-url for preview
```

Backend flow:

```text
receipt-extract
  -> validate file type
  -> send image/PDF bytes to Gemini
  -> return extracted fields and low-confidence fields

receipt-upload
  -> upload file to GCS temp receipt prefix
  -> return gs:// storage key

requests
  -> validate project exists
  -> for subcontractors, verify assigned project
  -> enforce request business rules
  -> save InputRequest in PostgreSQL
  -> detect duplicate by Receipt No. + Date + Amount
  -> status starts as PENDING_ADMIN
```

Important rules:

- `entry_type` must be `EXPENSE` or `INCOME`.
- Request type `ค่าเบิกล่วงหน้า` is allowed only for `EXPENSE`.
- Subcontractors can submit only to assigned projects.
- Duplicate detection flags but does not block submission.
- Receipt preview uses short-lived signed URLs.

Important files:

- `Projects-001-FE/src/InputPage.jsx`
- `Projects-001-BE/app/api/v1/input_requests.py`
- `Projects-001-BE/app/schemas/input_schema.py`
- `Projects-001-BE/app/services/ai_service.py`
- `Projects-001-BE/app/services/gcs_storage_service.py`

### 9.5 Admin Approval Flow

Frontend:

```text
ApprovalPage
  -> GET /api/v1/input/projects
  -> GET /api/v1/input/admin/requests
  -> GET /api/v1/input/admin/requests/{request_id}/receipt-url
  -> PUT /api/v1/input/admin/requests/{request_id}
  -> POST /api/v1/input/admin/requests/{request_id}/approve
  -> POST /api/v1/input/admin/requests/{request_id}/reject
  -> POST /api/v1/input/admin/requests/{request_id}/mark-paid
```

Backend lifecycle:

```text
PENDING_ADMIN or REJECTED
  -> admin edits fields
  -> duplicate detection can rerun
  -> approve moves receipt from temp GCS to perm GCS
  -> status becomes APPROVED
  -> mark-paid sets paid_at/payment_reference and status PAID

PENDING_ADMIN or REJECTED
  -> reject requires review note
  -> status becomes REJECTED
```

Reviewable statuses:

- `DRAFT`
- `PENDING_ADMIN`
- `REJECTED`

Paid flow:

- Only `APPROVED` input requests can be marked as `PAID`.

Important files:

- `Projects-001-FE/src/ApprovalPage.jsx`
- `Projects-001-BE/app/api/v1/input_requests.py`
- `Projects-001-BE/app/services/gcs_storage_service.py`

### 9.6 Insight Warehouse Flow

Frontend:

```text
InsightsPage
  -> GET /api/v1/insights/filters
  -> GET /api/v1/insights/summary
  -> GET /api/v1/insights/rows
  -> GET /api/v1/insights/export?format=csv|json
```

Backend normalizes multiple sources into one warehouse shape:

- `InputRequest` -> `INPUT_REQUEST`
- `Installment` -> `INSTALLMENT`
- `Transaction` -> `TRANSACTION`

Warehouse rows include:

- Project context.
- Actor context.
- Reference/title/description.
- Entry type and cash direction.
- Status.
- Amount and dates.
- Duplicate/overdue/OCR flags.
- Navigation target back into Approval or Project Detail.

Supported filters include:

- Global search.
- Quick view.
- Project.
- Source type.
- Status.
- Entry type.
- Flow direction.
- Date range.
- Amount range.
- Duplicate only.
- Overdue only.

Important files:

- `Projects-001-FE/src/InsightsPage.jsx`
- `Projects-001-BE/app/api/v1/insights.py`
- `Projects-001-BE/app/services/insight_warehouse_service.py`
- `Projects-001-BE/app/schemas/insight_schema.py`

### 9.7 Chat AI Flow

Frontend:

```text
ChatAIPage
  -> GET /api/v1/input/projects for project scoping
  -> GET /api/v1/chat/history
  -> POST /api/v1/chat/ask
  -> DELETE /api/v1/chat/history
```

Backend flow:

```text
POST /api/v1/chat/ask
  -> analyze question intent
  -> aggregate grounded data from database
  -> optionally ask Gemini to polish grounded response
  -> remove internal llm_context
  -> save response snapshot to chat_history
  -> return reply, summary, metrics, sources, next actions, time scope
```

The chat service is designed to avoid sending raw unbounded data directly to the LLM. It first builds database-grounded metrics and context, then uses Gemini as a best-effort polishing step.

Important files:

- `Projects-001-FE/src/ChatAIPage.jsx`
- `Projects-001-BE/app/api/v1/chat.py`
- `Projects-001-BE/app/services/chat_analytics_service.py`
- `Projects-001-BE/app/services/chat_history_service.py`
- `Projects-001-BE/app/services/ai_service.py`

### 9.8 Settings and Profile Flow

Settings page:

```text
SettingPage
  -> GET /api/v1/settings/subcontractors
  -> PUT /api/v1/settings/subcontractors/{sub_id}
  -> POST /api/v1/settings/subcontractors/{sub_id}/reset-line
  -> GET /api/v1/settings/users/{user_id}/kyc-image
  -> GET /api/v1/settings/admins
  -> POST /api/v1/settings/admins
  -> PUT /api/v1/settings/admins/{admin_id}
```

Settings responsibilities:

- Maintain subcontractor directory.
- Assign projects to subcontractors.
- Update tax/retention/bank/profile fields.
- Generate signed KYC image URLs.
- Reset LINE binding.
- Manage admin directory.

Profile page:

```text
ProfilePage
  -> GET /api/v1/profile/me
  -> POST /api/v1/profile/me/avatar
  -> DELETE /api/v1/profile/me/avatar
```

Profile image uploads are stored in GCS and surfaced through signed URLs.

Important files:

- `Projects-001-FE/src/SettingPage.jsx`
- `Projects-001-FE/src/ProfilePage.jsx`
- `Projects-001-BE/app/api/v1/settings.py`
- `Projects-001-BE/app/api/v1/profile.py`
- `Projects-001-BE/app/services/identity_service.py`
- `Projects-001-BE/app/services/gcs_storage_service.py`

### 9.9 Legacy Bills, Installments, and Advance Flow

The repository also contains an older bills/installments approval flow.

Endpoints:

```text
POST /api/v1/bills/extract
POST /api/v1/bills/submit
GET /api/v1/bills/admin/bills
PUT /api/v1/bills/admin/bills/{bill_id}
POST /api/v1/bills/admin/bills/{bill_id}/approve
GET /api/v1/subcontractor/my-bills
POST /api/v1/subcontractor/installments/{installment_id}/advance
```

Current implementation notes:

- `/api/v1/bills/extract` returns mock OCR data.
- `/api/v1/bills/submit` returns a mock success response and does not yet persist a full bill workflow.
- Admin bill approval operates on `Installment` records and creates `Transaction` records.
- Advance request splits one installment into an advance row and remaining locked row.

Advance split business rule:

```text
Original installment amount = 100%
Advance percent must be > 0 and <= 50

New advance installment:
  installment_no = original + ".1-ADV"
  amount = advance amount
  status = PENDING_ADMIN

Original installment becomes:
  installment_no = original + ".2-REM"
  amount = remaining amount
  status = LOCKED
```

Net payable formula:

```text
Net Payable = (Base Amount + VAT) - WHT - Advance Deduction - Retention
```

Important files:

- `Projects-001-BE/app/api/v1/bills.py`
- `Projects-001-BE/app/api/v1/subcontractor.py`
- `Projects-001-BE/app/services/finance_service.py`

## 10. Security and Access Control

Frontend:

- Stores session token and user payload in local storage through `auth.js`.
- Adds session token to backend requests through `api.js`.
- Uses protected routes to separate admin-only pages from shared/subcontractor pages.

Backend:

- Uses HMAC-signed session tokens in `core/security.py`.
- Uses `get_current_user`, `require_admin_user`, and `require_subcontractor_user`.
- In development, admin-only endpoints can use a debug admin override when no bearer token is present.
- Admin authorization checks Firestore admin records and configured admin allowlists/domain.
- GCS files are private and viewed through signed URLs.

Access-sensitive areas:

- Input project options are filtered by assigned project for subcontractors.
- Subcontractors can access only their own receipt URLs.
- Admin settings, KYC viewing, and approval endpoints require admin access.

## 11. Environment and Configuration

Frontend uses environment variables such as:

- `VITE_API_BASE_URL`
- Firebase web config variables.
- `VITE_LINE_LIFF_ID`

Backend settings are loaded from `Projects-001-BE/.env` through `app/core/config.py`.

Important backend variables include:

- `DATABASE_URL`
- `GCP_PROJECT_ID`
- `GCP_LOCATION`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `FIREBASE_PROJECT_ID`
- `LINE_CHANNEL_ID`
- `LINE_CHANNEL_SECRET`
- `JWT_SECRET_KEY`
- `GCS_BUCKET_NAME`
- GCS prefix variables.
- `GEMINI_MODEL`
- `EMBEDDING_MODEL`
- `BOQ_BATCH_SYNC_MAX_TABS`
- Admin allowlist/domain variables.

Deployment-related files:

- `deploy_frontend.sh`
- `deploy_backend.sh`
- `CLOUD_RUN_DEPLOY_CHECKLIST.md`
- `cloudrun.env.example`
- `cloudrun-backend.env.yaml.example`
- `cloudrun-frontend.build.env.example`
- `Projects-001-FE/Dockerfile`
- `Projects-001-BE/Dockerfile`

## 12. Current Implementation Status and Known Gaps

Implemented or mostly implemented:

- React routing and protected layout.
- Admin Google login and subcontractor LINE login/signup session flow.
- Project creation/update/listing.
- Google Sheets tab discovery and BOQ sync through Gemini.
- BOQ versioning and project detail comparison.
- Input page receipt OCR, temp upload, request submission, duplicate flagging.
- Approval page direct edit, approve, reject, mark paid, signed receipt preview.
- Insight Warehouse rows/summary/filter/export flow.
- Chat AI database-grounded analytics and chat history.
- Settings directory management, KYC signed URL, LINE reset.
- Profile avatar upload/reset.

Partially implemented or planned:

- Older `/api/v1/bills/extract` and `/api/v1/bills/submit` are still mock/TODO-oriented.
- BOQ item embeddings are modeled, but the current BOQ sync path does not persist embeddings for every item.
- In-memory BOQ batch job storage is development-oriented and will not survive process restart.
- Input approval currently updates `input_requests`; deeper integration into finance transactions is listed as backlog.
- Audit trail for submit/review/approve/reject/paid is listed as backlog.
- Automated production cleanup scheduling for temp receipts is listed as backlog, though the backend cleanup service exists.
- Some backend analytics/project endpoints do not enforce admin dependencies directly yet and rely on frontend route protection or development assumptions.

## 13. Main User Journeys

### Admin Starts Work

```text
Open app
  -> /login
  -> Google admin login
  -> backend verifies admin
  -> session saved
  -> Dashboard
```

### Admin Creates Project and Syncs BOQ

```text
Project page
  -> Add new project
  -> Save project
  -> Open BOQ sync drawer
  -> Enter Google Sheet URL
  -> Load tabs
  -> Select tabs
  -> Queue sync
  -> Poll job status
  -> Open Project Detail
  -> Review customer/subcontractor/compare BOQ views
```

### Subcontractor Submits Request

```text
LINE LIFF login
  -> signup if first time
  -> Input page
  -> upload receipt
  -> OCR autofills fields
  -> user reviews/corrects fields
  -> submit request
  -> request becomes PENDING_ADMIN
```

### Admin Reviews Request

```text
Approval page
  -> filter queue
  -> open request
  -> preview signed receipt URL
  -> edit fields if needed
  -> approve or reject
  -> approved request can be marked paid
```

### Admin Investigates Data

```text
Insights page
  -> filter/search warehouse rows
  -> open linked Approval or Project Detail record
  -> export CSV/JSON if needed
```

### Admin Asks AI

```text
Chat AI page
  -> choose optional project scope
  -> ask question
  -> backend aggregates database context
  -> Gemini optionally polishes response
  -> answer, metrics, sources, and next actions return
```

## 14. Glossary

- BOQ: Bill of Quantities.
- WBS: Work Breakdown Structure.
- SCD Type 2: versioning style where old rows are closed by `valid_to`, and new rows become current.
- LIFF: LINE Front-end Framework.
- KYC: Know Your Customer identity data.
- GCS: Google Cloud Storage.
- ADC: Google Application Default Credentials.
- OCR: Optical Character Recognition.
- WHT: Withholding Tax.
- RAG: Retrieval-Augmented Generation.
