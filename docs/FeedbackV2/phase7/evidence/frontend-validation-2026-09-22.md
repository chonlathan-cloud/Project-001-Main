# Phase 7 frontend validation — 2026-09-22

## Design sources

- Google Stitch API was enabled only in GCP project `project001-489710` after
  explicit approval.
- Stitch authentication and connector diagnostics passed. The inspected
  `Projects-001 Admin Portal` project uses primary `#4f6f64`, an earthy
  modernist direction, and Inter typography.
- The supplied BOQ Hub prototype was inspected for workflow and information
  architecture: dense Quotation Center, six-section composer, direct A4
  preview, visual pages, captions, navigation, zoom, and frozen export flow.
- `Design/DESIGN.md` remains authoritative for RAYADEE visual language; the UI
  does not copy the prototype's separate styling or metric-card dashboard.

## Implemented surface

- Search/filter/paginated `/quotations` Center with lifecycle status and primary
  document action.
- Stable composer deep links that pin revision and optional snapshot.
- Six-section rail with required-section rules, keyboard-operable ordering,
  enabled state, bilingual editor copy, and Native BOQ source link.
- Quotation-owned media upload/import/library, captions, BOQ scope association,
  visual page layout/reorder, missing-media and partial-upload states.
- Canonical multi-page A4 preview with page navigation, zoom, repeated identity
  footer, mobile fit behavior, read-only exact snapshot mode, PDF/XLSX exports,
  and renamed draft/frozen actions.
- Candidate media dialog traps focus, closes on Escape, and restores focus.

## Automated validation

```text
npm test
18 passed

npm run lint
passed

npm run build
passed
```

The Vite build retains the pre-existing warning for chunks over 500 kB. Phase 7
screens are route-level lazy chunks; no new build error was introduced.

## Demo status

- Frontend revision `projects-001-fe-00064-8xt` serves 100% of demo traffic.
- `/` and `/quotations` return HTTP 200; the final revision has no ERROR-level
  Cloud Run logs in the bounded post-deploy query.
- Frontend runtime spec hash is unchanged from the prior demo revision after
  excluding the image reference.
- The authenticated Demo composer was inspected through the native Chrome
  accessibility surface after deploy. The Visual editor exposes the primary
  bilingual `Upload from this device` action, multiple-file/drop guidance, the
  separate Daily Report/Inspection import path, and the 10 MB/Draft-only rules.
- The browser extension automation surface still reports another extension UI
  is open, so no new viewport screenshot set was captured. No file was uploaded
  and no Demo business record was changed during this read-only walkthrough.

## Device-upload follow-up

- Commit `aa6da55d412aeb34aa54acb92c437e31e6d40b16` makes local-device upload
  the primary Visual action and keeps project-media import as a secondary path.
- Multiple selected or dropped files upload sequentially under the existing
  optimistic version contract. Successful files automatically enable the
  Visual section and fill `TWO_UP` pages; five files therefore compose as
  `2 + 2 + 1` rather than requiring a manual add step.
- Per-file progress, partial failure, retry of failed files, dirty-draft save,
  and post-upload composition failure messaging are covered by the UI logic.
- Accepted local formats remain JPEG, PNG, WebP, HEIC, and HEIF, with the
  existing backend normalization, private quotation ownership, MIME/decode
  validation, metadata stripping, and 10 MB limit unchanged.
