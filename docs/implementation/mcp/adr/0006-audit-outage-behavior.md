# ADR-0006: Behavior during audit outage

- Status: Accepted for Foundation
- Date: 2026-07-28

## Decision

- Sensitive document/body access fails closed if its mandatory Product Audit
  event cannot be accepted by the configured emitter.
- Authorization denials and security events never expose data; emitter failure is
  also written to the separate operational logger/metric path.
- Non-sensitive discovery reads may proceed during an audit emitter failure only
  when the authorization decision was successfully resolved in the same request.
  The result is marked with an `AUDIT_DEGRADED` warning and no sensitive fields.
- Finance, user directory detail, audit-log reads and any future tool classified
  sensitive fail closed until explicitly reclassified with security approval.

This decision avoids turning a logging outage into a broad Product outage for
non-sensitive catalog metadata while preserving the absolute sensitive-audit
gate.

