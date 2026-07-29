# Phase 3 Demo release evidence

Evidence date: 2026-07-29
Environment: Demo (`project001-489710`, `asia-southeast1`)
Pilot role: Owner only
Repository commit: `a19fe99`

This report closes the live Demo rollout for Finance, Payment and the bounded
Document Gateway. It contains no OAuth token, secret, prompt, document body,
private file content, storage path or business-record identifier.

## Repository verification

| Check | Result | Evidence |
|---|---:|---|
| Backend regression | Pass | 100 tests passed |
| MCP regression | Pass | 58 tests passed |
| Phase 3 evaluator | Pass | 5/5 cases, 100%, all gates true |
| Finance fixture exactness | Pass | Exact Decimal strings and arithmetic passed |
| Document defenses | Pass | Limits, redaction, blocked-content, unsupported-content and prompt-injection cases passed |
| Lint and patch hygiene | Pass | Scoped Backend Ruff, MCP Ruff and `git diff --check` passed |
| Production images | Pass | Backend and MCP images built successfully before rollout |

## Database safety and migration

- An on-demand Demo Cloud SQL backup completed successfully before migration:
  backup `1785313726449`, description
  `pre-phase3-mcp-demo-a19fe99-20260729`.
- The additive migration
  `Projects-001-BE/scripts/migrations/20260729_mcp_document_gateway.sql` was
  applied only to the Demo `project-001` database.
- `input_requests.external_ai_blocked` is present as `boolean NOT NULL DEFAULT
  false`.
- The post-migration check found 36 existing rows and zero blocked rows. No
  business row was updated by the rollout.

The migration is backward-compatible with the previous Backend revision. An
application rollback therefore does not require dropping the column. Restoring
the database backup is an emergency, disruptive operation and was not performed.

## Runtime configuration

The Demo Backend revision has the approved bounded values:

| Variable | Value |
|---|---:|
| `MCP_DOCUMENT_MAX_BYTES` | 10485760 |
| `MCP_DOCUMENT_MAX_PAGES` | 50 |
| `MCP_DOCUMENT_MAX_CHARS` | 20000 |
| `MCP_DOCUMENT_SCAN_LIMIT` | 250 |

`MCP_INTERNAL_ENABLED=true` and `MCP_ALLOWED_ROLES=owner` remain in effect.
No Beta configuration or IAM binding changed.

## Deployment evidence

| Service | Previous revision | Ready revision | Verification |
|---|---|---|---|
| Backend | `projects-001-be-00118-v6v` | `projects-001-be-00119-f7r` | Health 200; unauthenticated internal MCP request denied; zero ERROR entries |
| Product MCP | `projects-001-mcp-00004-mn4` | `projects-001-mcp-00005-xxq` | Health 200; unauthenticated initialize 401; zero ERROR entries |

Backend was deployed and verified before Product MCP. The MCP service still had
revision-pinned traffic from the earlier rollback drill, so the new revision was
created without receiving traffic. The rollout explicitly moved 100% of Demo
traffic to `projects-001-mcp-00005-xxq`, then re-ran health and authorization
checks. Service identities remained unchanged.

## Live Owner evidence

The existing consenting Demo Owner completed OAuth through direct Codex. Only
compact, non-sensitive facts were retained from the calls.

| Gate | Result | Evidence |
|---|---:|---|
| Access and catalog | Pass | Demo Owner binding active; all-project scope; 10 domains; all seven Phase 3 tools advertised |
| Project financial summary | Pass | Exact THB Decimal strings, calculation metadata and source metadata returned |
| Financial record search | Pass | Authorized search returned a bounded typed record set |
| Payment read | Pass | One existing Demo fixture resolved as `PAID` without sensitive financial fields |
| Payment document status | Pass | Receipt and accounting readiness status returned without signed URL, path, bank data or credential |
| Document search | Pass | One authorized opaque document reference selected from a bounded result |
| Document metadata | Pass | Metadata resolved without filename, storage path or signed URL leakage |
| Bounded document content | Pass | 305 characters returned with the untrusted-content label; no prompt-injection indicator in the selected fixture |
| External-AI boundary | Pass | Selected live fixture was not blocked; blocked and fail-closed paths remain covered by automated tests because this rollout was not authorized to mutate business rows |
| Sensitive response boundary | Pass | No bank account, signed URL, storage key/path, token, secret, credential or private key appeared in retained results |

## Audit, privacy and latency

- 18 bounded Product Audit events were inspected; 16 belonged to Phase 3 tool
  executions.
- All seven Phase 3 tools appeared in Product Audit. Sensitive tools recorded
  both `started` and terminal success evidence.
- All inspected decisions were `allow`; every event was classified `lt_1s`.
- Audit payloads contained zero forbidden key occurrences and zero email values.
- A bounded scan of 188 MCP log entries found zero access-token, refresh-token,
  password, client-secret, private-key, signed-URL, storage-key/path,
  document-body or prompt-body markers.
- 24 successful MCP POST requests produced p50 0.175 seconds, p95 0.843 seconds
  and maximum 0.934 seconds. The simple-read target is at most 5 seconds.
- The deployed Backend and MCP revisions each had zero `severity>=ERROR`
  entries in the bounded rollout window.

## Rollback

Application rollback targets were preserved:

```bash
gcloud run services update-traffic projects-001-be \
  --project project001-489710 \
  --region asia-southeast1 \
  --to-revisions=projects-001-be-00118-v6v=100

gcloud run services update-traffic projects-001-mcp \
  --project project001-489710 \
  --region asia-southeast1 \
  --to-revisions=projects-001-mcp-00004-mn4=100
```

These commands were recorded but not executed during the Phase 3 rollout. The
Phase 2 rollback drill already verified the Cloud Run traffic procedure.

## Release decision

Phase 3 is complete in Demo for the Owner-only pilot. Phase 4 repository work may
begin. This decision does not authorize Admin rollout, Beta promotion, IAM
changes or new business-data mutation.
