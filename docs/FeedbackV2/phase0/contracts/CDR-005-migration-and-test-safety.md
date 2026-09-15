# CDR-005 — Migration and test safety

Status: **LOCKED**
Scope: Phase 0 harness and Phase 1 migration prerequisites

## Current-state decision

The repository does not have Alembic or another authoritative migration ledger.
Files under `scripts/migrations/` are independent SQL changes and some insert or
update application data. `create_missing_tables.py` is an ORM table creator, not
a version history. `seed_round1_data.py` drops tables and is destructive.

Therefore:

- Phase 0 does not run historical SQL scripts as a chain.
- Phase 0 builds the isolated baseline schema from current registered SQLAlchemy
  metadata after enabling `vector`.
- Phase 1 adopts Alembic and creates an explicit baseline/stamp procedure after a
  read-only comparison with each target environment.
- No environment is stamped merely because its tables “look close”. Differences
  must be recorded and reconciled first.

## Isolated test database contract

The checked-in harness uses `pgvector/pgvector:pg16` with:

- host binding `127.0.0.1:55432` only;
- database `projects001_phase0_test`;
- dedicated non-production credentials `phase0/phase0`;
- `tmpfs` PostgreSQL data (no shared/persistent volume);
- Docker Compose project `projects001_phase0`;
- explicit `PHASE0_DATABASE_URL` passed to scripts;
- refusal to bootstrap a non-loopback host, a database without `_test` suffix,
  or a database that already has public tables;
- no loading of `Projects-001-BE/.env` by controller/preflight logic.

Bootstrap creates the `vector` extension and current `Base.metadata` only. It
does not seed business data, run manual migrations, drop tables, or reset an
existing database. `down` removes only the named Compose project container; the
database itself is ephemeral.

## Schema preflight contract

`scripts/schema_preflight.py` is read-only. It inventories server/database,
extensions, public tables, columns, constraints, and indexes, normalizes the
result, and emits a SHA-256 fingerprint. Credentials are never printed.

Default safety permits loopback plus a database ending `_test` only. A future
`--allow-nonlocal-readonly` option may be used solely with separate explicit
environment authorization; it sets a read-only transaction and does not grant
permission to inspect production by itself.

Before any Phase 1 migration is run against an external environment, evidence
must include:

1. masked target identity and PostgreSQL major version;
2. installed `vector` version;
3. fingerprint/inventory compared with expected current ORM and known SQL drift;
4. backup/restore readiness and deployment authority;
5. exact Alembic current/head state or an approved first-time stamp plan;
6. proof that no destructive/implicit data backfill is part of upgrade.

## Phase 1 Alembic rules

- Add Alembic as a focused dependency/configuration change.
- First revision is additive and can upgrade an empty integration database as
  well as an explicitly stamped current-schema database.
- Import every model in migration metadata registration; startup and autogenerate
  checks must not omit tables silently.
- Use PostgreSQL-compatible constraints/indexes and deterministic names.
- Data backfills, if later required, are explicit, bounded, restartable, audited,
  and separate from table creation where practical.
- Existing projects default to `LEGACY`; migration must not activate V2 or alter
  existing numeric results.
- Production downgrade is not the rollback strategy. Rollback disables new
  mutations/restores compatible application code while preserving additive data.
  Dropping V2 tables or silently reverting an active budget source is prohibited.

## Required migration tests for Phase 1

- empty PostgreSQL 16 + pgvector upgrade to head;
- current-baseline schema stamp/upgrade rehearsal;
- second upgrade is a no-op;
- application import/startup after upgrade;
- constraints/indexes/enums/fingerprint match expected metadata;
- legacy rows and current public golden outputs remain unchanged;
- no V2 source becomes active from migration alone;
- archived BOQ-linked finance remains queryable;
- downgrade policy is documented and destructive downgrade is not exercised
  against shared or production data.
