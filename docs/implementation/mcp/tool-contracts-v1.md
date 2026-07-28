# Tool contracts v1

The authoritative machine-readable input schemas are in
`Projects-001-MCP/contracts/tool-input-schemas-v1.json`. Published tools use
these rules in addition to their individual schema.

## Naming and annotations

- Tool names are stable `snake_case` action names.
- Every tool has `readOnlyHint=true`, `destructiveHint=false`,
  `idempotentHint=true`, and `openWorldHint=false`.
- Input objects reject unknown fields.
- No input contains `environment`; the deployment locks the environment.
- No input accepts raw SQL, database/table names, Firestore paths, GCS paths,
  arbitrary URLs, Secret Manager identifiers, shell commands, or raw log queries.

## Common response

Successful tools return:

```json
{
  "schema_version": "1.0",
  "request_id": "opaque-request-id",
  "environment": "demo",
  "generated_at": "2026-07-28T00:00:00Z",
  "data": {},
  "sources": [],
  "pagination": null,
  "access_scope": {},
  "freshness": {},
  "warnings": [],
  "partial": false
}
```

Errors use the same identity fields plus a structured `error` object with one of
the approved codes. They never include stack traces, SQL, storage paths, tokens,
signed URLs or hidden identifiers.

## Stable references and pagination

- References use opaque `<domain>:<record-type>:<opaque-id>` values.
- BOQ line search hits use
  `projects_boq:boq_line:<project-uuid>.<stable-line-id>` and `fetch` re-checks
  Product authorization before resolving the current or requested version.
- Cursors are opaque, integrity-protected by the producing service and capped at
  1024 characters.
- List/search limits default to 20 and never exceed 100; log/document limits are
  lower where their schemas specify.
- A direct lookup outside the user's scope returns `NOT_FOUND_OR_FORBIDDEN`.

## Money and time

- Canonical money is `{ "amount": "1234.50", "currency": "THB" }`.
- Binary floating-point values are not canonical financial outputs.
- Timestamps are RFC 3339 UTC. Display timezone is metadata, not a reinterpretation
  of stored time.

## Compatibility

- Additive optional fields are allowed within schema version `1.x`.
- Removing/renaming fields, changing meaning, narrowing accepted input or changing
  an identifier requires a new tool/major schema version.
- Tool schemas are snapshot-tested before release.
- The SDK baseline and protocol upgrade decision are recorded in ADR-0002.
