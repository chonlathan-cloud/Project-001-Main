# Same-project legacy → V2 cutover and rollback runbook

## Preconditions

1. Confirm backup/restore readiness and migration head `20260917_0003` on the target environment.
2. Confirm the compatibility release is deployed and old BOQ sync submissions are frozen. No pending external worker may write legacy BOQ state after the preview.
3. Confirm the project ID is unchanged and inventory its legacy BOQ IDs plus finance/execution references.
4. Confirm an accepted MAIN (or accepted alternative), the intended accepted ADD/DEDUCT change orders, immutable snapshots, and a published cost plan exist.
5. Review `ProjectBudgetSnapshot`: baseline/version, revisions, cost-plan version, calculation version, sell total, completeness, forecast status and activation preview.
6. Do not require legacy and V2 totals to match. This is preservation and source selection, not reconciliation.

## Owner cutover

1. Owner reviews the native baseline preview and explicitly records/accepts the intended commercial state.
2. The source selection changes once from `LEGACY` to `V2` under the project budget lock. V2 replaces legacy as the active source; it is never added to the legacy total.
3. Verify Project list/detail, Dashboard, Funds, Chat and MCP return the same V2 source/baseline identity.
4. If cost is incomplete, verify sell budget remains known, Funds displays `UNKNOWN_COST`, and new outward allocation fails closed.
5. Verify incoming allocation and a valid reversal/correction still work.
6. Verify existing installment, transaction, input/payment, allocation and legacy BOQ IDs/counts are unchanged.
7. Verify an as-of read before activation resolves `LEGACY`; current/as-of after activation resolves the applicable V2 baseline.
8. Verify old legacy document/line references remain fetchable by history, Chat/Insights, finance and MCP paths.

The executable isolated rehearsal is `tests/postgres/verify_phase5_cutover.py`. It validates MAIN 1,200,000 + ADD 100,000 − DEDUCT 50,000 = active V2 1,250,000 while preserving a deliberately different 900,000 legacy budget and its archived finance reference. The transaction is rolled back.

## Rollback constraints

- Stop new V2 mutations first and restore a compatible application/configuration version.
- Preserve all V2 and legacy rows, immutable documents/artifacts, audit events and finance/allocation history.
- Do not drop tables, delete/expire legacy rows, replay payments, recreate transactions, reconcile totals, or remap historical relationships.
- Disabling a global UI flag does not safely change a project's source selection.
- Returning a project source to `LEGACY` requires an explicit Owner decision, impact preview and a separately audited operation. It may be unsafe after accepted V2 changes or allocations.
- If only a reader regression exists, roll back application reads while leaving the recorded source and data intact; repair forward after validating as-of/history behavior.
