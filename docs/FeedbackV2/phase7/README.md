# Phase 7 — Quotation Center & Document Composer

Phase 7 extends the BOQ V2 quotation lifecycle with a versioned, canonical
document-composition contract. It preserves the Phase 3 immutable snapshot and
export model while adding six ordered document sections and quotation-owned
visual media.

## Contract

- Historical snapshots without `schema_version` continue to render as the
  legacy `boq-v2-document-snapshot-v1` shape.
- New snapshots use `boq-v2-document-snapshot-v2` and freeze section order,
  bilingual headings, BOQ content, totals, payment terms, visual pages,
  captions, media identity, SHA-256, revision version, and calculation version.
- `SUMMARY` is enabled and first, `DETAILED_BOQ` is enabled, and an enabled
  `ACCEPTANCE` section is last. Visual pages contain 1–4 images using `SINGLE`,
  `TWO_UP`, or `FOUR_UP`.
- `document_pages` remains a deprecated compatibility projection. The section
  records are the source of truth for new drafts.
- Customer snapshot/export payloads never contain storage keys, cost plans,
  vendor data, margin, or internal notes.

## Media boundary

- Owner-only mutation endpoints accept uploads or import project-owned Daily
  Report/Inspection images.
- Imported assets are copied into private quotation-owned storage.
- JPEG, PNG, WebP, HEIC, and HEIF inputs are decoded, MIME/signature checked,
  orientation-normalized, stripped of metadata, and re-encoded as customer-safe
  JPEG renditions.
- Uploads are streamed with a default 10 MiB limit. Signed URLs are short-lived
  and scoped to a media record belonging to the requested revision.
- Issue and export fail closed on missing media or SHA-256 mismatch.

## Rollout boundary

This phase is authorized for isolated validation and the demo environment only.
No beta/production migration, deployment, IAM change, or production data change
is part of this implementation.

See [backend validation evidence](evidence/backend-validation-2026-09-22.md).
