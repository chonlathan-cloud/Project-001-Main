# ADR-0003: Product Audit storage and query

- Status: Accepted architecture; live bucket/view pending
- Date: 2026-07-28

## Decision

Product Audit and operational telemetry use separate structured logger names and
log types. Product Audit is routed by Cloud Logging to a dedicated environment-
specific log bucket with append-only retention (Demo 90 days, Beta 365 days).
Operational logs retain 30 days and may be sampled; audit/security events may not.

Runtime emits only the approved event schema. Tokens, prompts, full responses,
document bodies, signed URLs, storage paths and unredacted financial/identity
details are prohibited and recursively redacted before serialization.

`search_audit_events` and `get_audit_event` will query a dedicated read view using
allowlisted fields and server-built filters. The runtime writer identity does not
gain broad log-read permission; read access is granted separately when the Audit
tool phase starts.

