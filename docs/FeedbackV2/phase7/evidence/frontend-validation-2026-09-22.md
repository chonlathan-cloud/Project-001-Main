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
16 passed

npm run lint
passed

npm run build
passed
```

The Vite build retains the pre-existing warning for chunks over 500 kB. Phase 7
screens are route-level lazy chunks; no new build error was introduced.

## Pending demo evidence

- Rendered screenshots at 1440, 1024, 768, and 390 px.
- Authenticated demo walkthrough from BOQ through visual composition, preview,
  issue, and customer PDF/XLSX export.
- Artifact inspection and immutable SHA-256 check.
- Demo configuration/revision/image digest record.
