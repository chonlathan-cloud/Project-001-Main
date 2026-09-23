# Phase 7 demo rollout — 2026-09-22

## Authorized boundary

- GCP project: `project001-489710`
- Environment changed: demo only
- Demo services: `projects-001-be`, `projects-001-fe`
- Demo Cloud SQL instance: `project-001`
- Beta services and `project-001-beta` were inspected read-only and were not
  migrated, deployed, or reconfigured.
- No IAM change, production-data operation, beta cutover, or automatic customer
  delivery was performed.

## Pre-cutover safety

- On-demand backup `1790063477126`, description
  `phase7-pre-migration-fbab72b`: `SUCCESSFUL`.
- Started `2026-09-22T07:51:17.140Z`; completed
  `2026-09-22T07:52:48.570Z`; location `asia`.
- Automated backups remain enabled with 30 retained backups.
- PITR remains enabled with seven days of transaction-log retention.
- The existing migration guard first rejected a localhost non-test target. The
  migration was then run deliberately through the Cloud SQL Auth Proxy with the
  documented nonlocal override after the backup and schema preflight passed.

## Schema result

- PostgreSQL: `18.3`
- Alembic before: `20260917_0003`
- Alembic after: `20260922_0004 (head)`
- Registered tables after migration: 42
- `boq_v2_*` tables after migration: 26
- Post-migration fingerprint:
  `48c88b160ac75fe3a9778c8f72daaa8f826f9788ddd4cc23ad4cdc8aa3720e4b`
- Isolated PostgreSQL validation also passed fresh install, Phase 6 upgrade,
  downgrade, and re-upgrade paths.

## Deployed images and revisions

Frontend:

- Commit: `fbab72b27026b1163132e06a9fcbd72b795f5212`
- Image manifest-list digest:
  `sha256:c854296d057137f0e6e5cd36e2d1b60eca37e0c0b0fe65767475ce7a6a873266`
- Cloud Run revision: `projects-001-fe-00063-k54`, 100% traffic
- Normalized runtime spec hash before and after, excluding image:
  `e089d7d292fb7580298b9f5bb473d2209636f72e76526ac3b5e256230155a514`

Backend final:

- Commit: `3134a1a0a4d60b0ec9f24627a3cfd2dccffcad6d`
- Image manifest-list digest:
  `sha256:4823daa7abd0b36c87e7d24a9ad971ee77a16ad802e1e23efe188259fa000006`
- Cloud Run revision: `projects-001-be-00135-mgt`, 100% traffic
- Normalized runtime spec hash before and after, excluding image:
  `3b6cc511450139e68c368d621b2feacd03946e684466b8f2512ed7af9bd97f85`

The final backend revision includes the PDF specification-line rendering fix
found during rendered-page QA. No environment variables, service account,
Cloud SQL attachment, scaling setting, or traffic split changed with either
image update.

## Demo-specific configuration to reuse for a future approved beta rollout

- Build `VITE_BOQ_V2_ENABLED=true`.
- Reuse the existing demo public Firebase/LIFF build configuration; do not copy
  demo secrets or runtime identities to beta.
- Apply migration `20260922_0004` only after a separate beta backup, schema
  preflight, and isolated restore drill approval.
- Deploy the compatibility backend before the frontend, preserve the target
  service runtime spec, then verify the exact image digest and traffic.
- Keep quotation media private and retain the existing short-lived signed-URL
  behavior.

## Validation results

```text
Backend Ruff: passed
Backend Phase 3 + Phase 7: 12 passed
Backend startup import: passed
Frontend tests: 16 passed
Frontend lint: passed
Frontend build: passed (existing chunk-size warning)
Backend /health: HTTP 200, {"status":"ok"}
Frontend /: HTTP 200
Frontend /quotations: HTTP 200
Unauthenticated /api/v1/boq/quotations: HTTP 401
Final demo revision ERROR logs: none in bounded post-deploy queries
```

The frontend container build also reported the existing dependency audit state
of 10 findings (four moderate, six high). This rollout did not mutate package
versions. The Vite chunk-size warning remains unchanged.

## Canonical sample artifacts

All samples use synthetic bilingual data and the same frozen v2 render
contract:

- `samples/phase7-bilingual-customer-sample.pdf`: six A4 pages, 21,575 bytes,
  SHA-256 `ba1de74103347a7cc4c5bcdabc3d06868a29a597b10598513f166782a7a5fc00`
- `samples/phase7-bilingual-customer-sample.xlsx`: five native sheets with one
  embedded visual, 11,263 bytes, SHA-256
  `3b6dbc7c33e853b5d9be5c4feaf45a6185f9ed432f48670fd5621c03ea9d0cba`
- `samples/phase7-bilingual-customer-sample-page-1.png`: rendered first-page
  evidence, 78,690 bytes, SHA-256
  `8c6928a05ab4b36b6f2d1960fcc704fd7bb2500c73a3c996b4a6dc2307fb73c0`

`pdfinfo`, `pdftotext`, and all-page visual inspection confirm embedded Thai
text, page footers, six enabled sections, totals, captioned visual content, and
no blank pages. Customer artifacts contain no cost, margin, vendor, internal
note, or raw storage identifier.

## Browser UAT status

The authenticated Chrome tab is already at the demo Quotation Center, but the
computer-use provider consistently returns: `Google Chrome is blocking
automation because another extension UI is open on this page`. A fresh Chrome
tab and reconnect attempt return the same blocker. Consequently no live demo
data was issued or deleted and viewport screenshots were not fabricated.

Resume the remaining click-through after dismissing the open Chrome extension
UI: Center search -> open `Renovation The Mall` -> compose visuals -> preview ->
issue -> export PDF/XLSX -> verify pinned exact snapshot at 1440, 1024, 768, and
390 px.

## Device-upload frontend follow-up

This additive frontend-only follow-up was deployed to Demo after the main
Phase 7 rollout. It did not run a migration or deploy the backend.

- Commit: `aa6da55d412aeb34aa54acb92c437e31e6d40b16`
- Image tag: `aa6da55-phase7-device-upload-demo`
- Image manifest-list digest:
  `sha256:47bc5538baca06f32fd4a8a998381354a2b2633f8d32b246b479c40ec18d4044`
- Cloud Run revision: `projects-001-fe-00064-8xt`, 100% traffic
- Predecessor and replacement revision `.spec` hashes, canonicalized without
  the container image: both
  `424db53aa69cd7c303edcfa4ef071cc46e77a95d105b5542023c7e54e93395e1`
- Demo frontend `/` and `/quotations`: HTTP 200
- Demo backend `/health`: HTTP 200 with `{"status":"ok"}`
- New frontend revision ERROR-or-5xx logs since creation: zero
- Beta frontend remained `projects-001-fe-beta-00019-9k7` at 100% traffic.

Validation for the follow-up was `18 passed`, ESLint passed, production build
passed with the existing chunk-size warning, and `git diff --check` passed.
The existing dependency audit result (four moderate and six high findings) was
not changed by this implementation.

The authenticated Demo composer was verified read-only after deploy. The
Visual editor shows the bilingual local-device upload action, multiple-file
and drag/drop guidance, separate Daily Report/Inspection import, supported
formats, 10 MB per-image limit, and Draft-only rule. No file was uploaded and
no Demo record was changed during this verification. The extension-controlled
viewport screenshot path remains blocked by another Chrome extension UI.

## Legacy BOQ presentation follow-up — 2026-09-23

This frontend-only follow-up was deployed to Demo after simplifying how
Google Sheets-era BOQ data is presented. It did not run a migration, deploy the
backend, change IAM, or modify Demo records.

- Commit: `dbaa85036795e5ce15a963118dc39cd3fa03f73c`
- Image tag: `dbaa850-legacy-boq-history-demo`
- Image manifest-list digest:
  `sha256:977061a14300f3b42d91671529a65b2db59009e97cbf89e47568fef59ab9a8ab`
- Cloud Run platform image digest:
  `sha256:ecffc3b6341229a90325b89b7a6dcbf9bdf28a6736a88331de93411270ce3b19`
- Cloud Run revision: `projects-001-fe-00065-69c`, 100% traffic
- Predecessor and replacement revision `.spec` hashes, canonicalized without
  the container image: both
  `424db53aa69cd7c303edcfa4ef071cc46e77a95d105b5542023c7e54e93395e1`
- Demo frontend `/`, `/project`, and the Renovation The Mall detail route:
  HTTP 200
- New frontend revision ERROR-or-5xx logs since creation: zero
- Beta frontend remained `projects-001-fe-beta-00019-9k7` at 100% traffic.

Validation before rollout was 22 frontend tests passed, ESLint passed,
production build passed with the existing chunk-size warning, and
`git diff --check` passed.

Authenticated read-only browser UAT confirmed the new revision is serving.
The Renovation The Mall detail response currently classifies its active budget
as `LEGACY / NO_BUDGET_DATA`; therefore the compatibility workbench remains
visible for that project. The Native V2 behavior in this follow-up only hides
the legacy workbench when the active snapshot is V2 and there are no legacy
rows, or collapses it as read-only history when V2 coexists with legacy rows.
