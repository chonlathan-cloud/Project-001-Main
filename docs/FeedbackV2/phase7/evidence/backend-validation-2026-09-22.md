# Phase 7 backend validation — 2026-09-22

## Isolation

- Branch: `feature`
- PostgreSQL: `pgvector/pgvector:pg16`, bound to `127.0.0.1:55432`
- Databases: `projects001_phase0_test` and temporary
  `projects001_phase7_fresh_test`
- Storage: Docker `tmpfs`
- No beta/production migration, deployment, data mutation, or IAM action was
  performed.

## Migration evidence

- Upgrade from Phase 6 head `20260917_0003` to `20260922_0004`: passed.
- Downgrade `20260922_0004` to `20260917_0003`: passed.
- Re-upgrade to `20260922_0004`: passed.
- Fresh database upgrade from Alembic base through `20260922_0004`: passed.
- Phase 7 schema fingerprint:
  `29a0553ea17dff78a549b9d9e6345b87a824c5215a350a365f5a10878a978913`
- Registered tables: 42; `boq_v2_*` tables: 26.

## Automated validation

```text
ruff check (Phase 7 affected backend and test files)
All checks passed!

python -m pytest -q tests/phase3 tests/phase7
12 passed in 6.80s

python -c "from main import app; print(app.title)"
Project_001 API
```

Covered behavior includes legacy v1 export compatibility, section rules,
visual layout limits, image normalization and EXIF removal, invalid MIME,
corrupt/oversized uploads, Owner/Admin mutation boundaries, optimistic version
conflict, cross-project media denial, immutable preview payloads, Quotation
Center listing, customer-data allowlisting, bilingual multi-page PDF rendering,
spreadsheet-native XLSX output, embedded visuals, captions, totals, and a
nonblank rendered first PDF page. It also covers rejection of issue when the
explicit reviewed preview belongs to an older revision version. Artifact
validation now asserts that the persisted bytes match the recorded SHA-256 and
that an idempotent export after creating a later revision returns the same
artifact identity and SHA-256.

## Artifact QA

- The canonical v2 renderer produced a six-page A4 bilingual customer PDF and
  a five-sheet XLSX from the same synthetic frozen snapshot.
- `pdfinfo`, `pdftotext`, and PNG inspection passed. Visual inspection exposed
  and fixed a literal HTML tag in Detailed BOQ specifications before the final
  demo backend deployment.
- Samples are stored under `evidence/samples/` with SHA-256 values recorded in
  the demo rollout evidence.

## Remaining gate

- Authenticated browser click-through and viewport screenshots remain blocked
  because Chrome reports another extension UI is open. Public route/health,
  automated contract tests, and rendered artifact checks are complete.
- The pre-existing Phase 6 evidence change remains outside Phase 7 commits.
