# Phase 6 recovery-readiness evidence — 2026-09-21

Result: **PASS — recovery prerequisite satisfied; later production stages remain
on hold pending separate authorization**

Completed by `2026-09-21T10:20:15Z` against GCP project
`project001-489710`, Cloud SQL instance `project-001`, in
`asia-southeast1`. The operator recorded by Cloud SQL was
`chonlathan@manee-son.com`.

## Authority boundary

Business Owner Chonlathan Wisetwongsa approved only:

- automated backups retained for 30 backup runs;
- PITR retained for 7–14 days;
- a fresh pre-cutover backup retained for at least 30–90 days; and
- an isolated restore drill, including deletion of only the temporary drill
  instance after evidence was captured.

Deployment, baseline stamping, migration, V2 enablement, UAT writes, project
cutover, and source activation were explicitly withheld until this drill
passed. Passing this drill does not itself authorize those actions.

## Backup and PITR configuration

The first request for 14 transaction-log retention days was rejected by the
Cloud SQL API with HTTP 400 before mutation because this Enterprise instance
accepts at most 7 days. Seven days is within the Owner-approved 7–14 day range,
so the operation was retried with 7 days.

Cloud SQL update operation
`4e075804-e5f5-4452-b7bd-2e8e00000031` completed successfully:

- start: `2026-09-21T10:00:36.141Z`
- end: `2026-09-21T10:04:02.434Z`
- automated backups: enabled
- backup window: `14:00 UTC` (existing window preserved)
- retained automated backups: `30`, retention unit `COUNT`
- PITR: enabled
- transaction-log retention: `7` days
- transaction-log storage: `CLOUD_STORAGE`
- source instance state after all work: `RUNNABLE`
- source deletion protection after all work: enabled
- source settings version after all work: `232`

## Fresh pre-cutover backup

Cloud SQL backup operation `a4139256-040d-4193-9bcd-2cc200000031` completed
successfully and produced:

- backup ID: `1789985068799`
- type: `ON_DEMAND`
- status: `SUCCESSFUL`
- location: `asia`
- start: `2026-09-21T10:04:28.810Z`
- end: `2026-09-21T10:06:00.966Z`
- description:
  `phase6-pre-cutover-62e5661-retain-not-before-2026-12-20`
- operational do-not-delete-before date: `2026-12-20` (90 days)

A standard Cloud SQL on-demand backup has no per-backup retention flag and is
retained until it is manually deleted. The backup was confirmed present and
successful after drill cleanup. It must not be manually deleted before the
date above.

## Isolated restore drill

Backup `1789985068799` was restored to temporary instance
`project-001-phase6-drill-20260921-1706`. No application was wired to this
instance.

Restore operation `a91fe354-bb8a-4d6b-88cc-e37a00000031`:

- type: `RESTORE_VOLUME`
- start: `2026-09-21T10:07:33.668Z`
- end: `2026-09-21T10:13:10.407Z`
- result: `DONE`, no error
- restored state: `RUNNABLE`
- PostgreSQL: 18
- region/zone: `asia-southeast1` / `asia-southeast1-c`

The restored instance was accessed only through a Cloud SQL Auth Proxy bound
to `127.0.0.1:55436`. The source comparison proxy was bound to
`127.0.0.1:55434`. Database credentials were read locally into subprocess
environment only and were not printed or written to evidence.

## Schema verification

`Projects-001-BE/scripts/phase6_schema_gate.py --allow-nonlocal-readonly`
passed against the restored database using the approved exact schema profile:

- database: `project-001`
- PostgreSQL major: `18`
- pgvector: `0.8.1`
- public tables: `15`
- `boq_v2_*` tables: `0`
- Alembic revisions: none
- budget-source table: absent
- schema fingerprint:
  `cb7206a7ef0a8d3c2a1cd0b864b1ef93a06c4f2ef5a5a36d6ac5743aef6c1b41`
- schema stable across the gate: true
- mismatches: none
- mutation authorized by the gate: false

## Data-integrity comparison

Source and restore were compared concurrently using read-only,
repeatable-read transactions. For every public table, the verifier compared
the row count and a deterministic content hash built from sorted
`md5(row_to_json(row)::text)` values. No row contents or business identifiers
were emitted.

| Table | Source rows | Restored rows | Count | Content hash |
| --- | ---: | ---: | --- | --- |
| `boq_items` | 963 | 963 | match | match |
| `chat_history` | 0 | 0 | match | match |
| `fund_allocations` | 3 | 3 | match | match |
| `fund_audit_events` | 5 | 5 | match | match |
| `fund_buckets` | 8 | 8 | match | match |
| `fund_ledger_entries` | 7 | 7 | match | match |
| `input_option_suggestions` | 8 | 8 | match | match |
| `input_payment_confirmations` | 1 | 1 | match | match |
| `input_payment_reference_counters` | 2 | 2 | match | match |
| `input_payments` | 4 | 4 | match | match |
| `input_request_line_items` | 161 | 161 | match | match |
| `input_requests` | 37 | 37 | match | match |
| `installments` | 14 | 14 | match | match |
| `projects` | 8 | 8 | match | match |
| `transactions` | 8 | 8 | match | match |

Both inventories produced aggregate SHA-256
`d8b85e3229f2c6d938cca9a1fe8a76991667d68a20ce45d8b2c7bc4d77d64eab`.
Table names, row counts, and all content hashes matched.

## Cleanup and final state

After verification:

1. both local proxies were stopped;
2. deletion protection was disabled only on the temporary drill instance by
   update operation `3e203ba6-8d6a-43d3-9d5b-897900000031`, completed at
   `2026-09-21T10:17:03.910Z`;
3. the temporary instance was deleted by operation
   `dada1c2f-0db9-4b38-86d7-00d500000031`, completed at
   `2026-09-21T10:19:30.371Z`; and
4. exact-name inventory confirmed the temporary instance was absent, ports
   `55434` and `55436` were free, the source remained `RUNNABLE` with deletion
   protection enabled, and backup `1789985068799` remained `SUCCESSFUL`.

No deployment, schema migration, IAM change, application write, source flip,
finance replay, legacy-history rewrite, or production cutover occurred.

## Remaining release holds

Recovery readiness is no longer a stop condition. Phase 6 is still not
authorized to proceed because:

- no immutable backend/frontend/MCP release identity has been approved;
- the production database remains unstamped and has no V2 tables;
- the current deployed backend still has the known Dashboard/V2 schema
  incompatibility;
- the intended application project UUID/name has not been designated; and
- migration, compatibility deployment, production UAT writes, sync freeze,
  Owner preview approval, cutover, and source activation each require explicit
  authority.
