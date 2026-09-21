# Phase 6 data-bearing migration rehearsal — 2026-09-21

Result: **PASS — production-specific stamp and additive migration path proved
on an isolated data-bearing restore**

Production `project-001` was not stamped or migrated during this rehearsal.
No application was wired to the temporary instance, no V2 source was
activated, and the temporary instance was deleted after verification.

## Authority and target

- GCP project: `project001-489710`
- Region: `asia-southeast1`
- Source backup: `1789985068799`
- Temporary instance: `project-001-phase6-mig-20260921-1746`
- Operator recorded by Cloud SQL: `chonlathan@manee-son.com`
- Approval record commit: `4c8dff5`
- Approved migration path: stamp `20260915_0000`, then upgrade
  `20260915_0001` → `20260917_0002` → `20260917_0003`

Restore operation `d79ef0c4-6c85-4796-adf9-06c400000031` completed without
error from `2026-09-21T10:46:05.261Z` to `2026-09-21T10:51:34.429Z`.
The restored instance was PostgreSQL 18.6 in `asia-southeast1-c`, reported
`RUNNABLE`, and had deletion protection enabled during verification.

## Fail-closed pre-migration gate

The approved exact production profile passed before any schema write:

- profile status: `APPROVED`
- database: `project-001`
- PostgreSQL major: 18
- pgvector: `0.8.1`
- public tables: 15
- `boq_v2_*` tables: 0
- Alembic revisions: none
- budget-source table: absent
- schema fingerprint:
  `cb7206a7ef0a8d3c2a1cd0b864b1ef93a06c4f2ef5a5a36d6ac5743aef6c1b41`
- mismatches: none
- schema stable across the gate: true

The 15 legacy tables produced aggregate content SHA-256
`d8b85e3229f2c6d938cca9a1fe8a76991667d68a20ce45d8b2c7bc4d77d64eab`
before migration. Counts were 963 BOQ items, 8 projects, 14 installments, 8
transactions, 37 input requests, 3 fund allocations, 8 fund buckets, 7 fund
ledger entries, and the remaining table counts already recorded in the
recovery-readiness evidence.

## Migration transcript

The migration connected through a local Unix socket created by Cloud SQL Auth
Proxy. This avoided changing authorized networks. The explicit Alembic target
was supplied only through the subprocess environment; no URL or credential was
printed or stored.

| Step | Result | Duration |
| --- | --- | ---: |
| Stamp `20260915_0000` | passed | 1.963 s |
| Upgrade `20260915_0001` | passed | 3.481 s |
| Upgrade `20260917_0002` | passed | 7.188 s |
| Upgrade `20260917_0003` | passed | 5.988 s |
| Second `upgrade head` | no-op | 2.519 s |

`alembic current` returned `20260917_0003 (head)` both before and after the
second upgrade.

## Post-migration schema and data invariants

- public tables: 38
- V2 tables: exactly 22
- all V2 business tables: empty
- `boq_v2_project_budget_sources`: 0 rows
- invalid public indexes: 0
- unvalidated public constraints: 0
- schema verifier constraint/default rollback checks: passed
- post-migration schema fingerprint:
  `30759a530ce5bca72435cbcf900d2e221ae1a54033a66c24838906fb329da1ed`
- legacy table counts and all deterministic content hashes: unchanged
- post-migration legacy aggregate SHA-256:
  `d8b85e3229f2c6d938cca9a1fe8a76991667d68a20ce45d8b2c7bc4d77d64eab`

`alembic check` exited 255 as expected for the preserved production drift.
Its output contained only the approved allowlist categories: legacy BOQ
hierarchy fields/index, fund constraints/indexes/JSONB, input accounting and
FlowAccount nullability/type/comment differences, and the partial
`projects.system_key` uniqueness representation. No migration was generated
from this output and no preserved object was normalized.

## Application smoke against the migrated restore

The checked-in backend was exercised in-process against the restored database
under an Owner route context with `BOQ_V2_ENABLED=false`. Only GET/read paths
and the retired-sync compatibility response were invoked:

| Flow | Result |
| --- | --- |
| Health | 200 |
| Project list, 8 rows | 200 |
| Project detail | 200 |
| Dashboard summary | 200 |
| Fund bucket options, 8 rows | 200 |
| Fund allocations | 200 |
| Input projects, 8 rows | 200 |
| Input requests, 37 rows | 200 |
| Input admin summary | 200 |
| Daily Reports queue, 5 rows | 200 |
| Chat history, 0 rows | 200 |
| Integration settings | 200 |
| V2 workspace while disabled | 404 `BOQ_V2_ROLLOUT_DISABLED` |
| Legacy BOQ sync submission | 410 `BOQ_SYNC_RETIRED` |

The route smoke used a dependency-injected Owner identity and therefore did
not exercise cryptographic bearer-token verification. Authentication,
authorization, MCP, OCR, and FlowAccount network boundaries still require
post-deployment production smoke; no external write path was called here.

## Cleanup

The proxy was stopped and its Unix socket removed. Deletion protection was
disabled only on the temporary instance by operation
`986412db-2a7a-4cf2-91fb-25aa00000031`, completed at
`2026-09-21T10:59:54.520Z`. The temporary instance was then deleted by
operation `37b9dd01-7937-4c45-abbd-44c100000031`, completed at
`2026-09-21T11:02:18.656Z`.

Final checks confirmed:

- the temporary instance is absent;
- proxy ports `55434` and `55436` are free and the socket path is absent;
- production `project-001` remains `RUNNABLE`, unstamped, and protected from
  deletion; and
- backup `1789985068799` remains `SUCCESSFUL` and retained.

## Remaining gates

Production migration is technically rehearsed but was not executed. Before
production mutation, repeat the exact schema gate, verify no pending sync or
unexpected operations, and capture a final backup boundary. Compatibility
images must be built from a clean reviewed SHA and their immutable digests
recorded. The application project name `Renovation The Mall` still has no match
or UUID in the target database; this blocks later UAT/cutover, not the
feature-disabled compatibility migration/deployment.
