# Product MCP threat model v1

## Assets and trust boundaries

Protected assets include business records, private documents, financial/identity
data, authorization state, audit evidence, service credentials and environment
isolation. Trust boundaries are the external OAuth client, MCP resource server,
Product Backend, fallback data sources, GCP control plane and logging sinks.

## Threats and required controls

| Threat | Control | Verification |
|---|---|---|
| Forged/replayed/wrong-resource OAuth token | Signature, issuer, audience/resource, expiry, environment claim and required-scope validation | JWT vectors and cross-environment negatives |
| Confused deputy to Backend | Separate service identity; verified subject only; Backend re-resolves authorization; never forward inbound token | Delegation contract tests |
| Token role elevation | Ignore role/permission claims as authority | Authorization tests |
| Record enumeration | Scope before read; `NOT_FOUND_OR_FORBIDDEN`; opaque refs | Guessed/cross-project ID tests |
| Cross-environment or SaaS crossover | Fixed config map, separate identity, explicit denylist, no environment input | Config/preflight/IAM tests |
| Business mutation | No mutation tools; adapters expose bounded reads; read-only DB/IAM | Inventory and negative mutation tests |
| SQL/Firestore/GCS injection | No generic query/path input; allowlisted adapter methods | Contract schema and malicious input tests |
| Signed URL/path/secret leakage | Document Gateway; output redaction; forbidden-key tests | Security fixtures |
| Document prompt injection | Treat bytes/text as quoted data; never alter tool policy; bounded sections | Adversarial document fixtures |
| Oversized response/context abuse | Limits, cursors, timeouts, byte/page caps and rate limits | Boundary/load tests |
| Stale authorization after revoke | Per-call resolution or approved short cache with revocation SLA | Revoke-between-calls test |
| Source conflict hidden from user | Backend wins business semantics; emit `SOURCE_INCONSISTENCY` | Conflict fixture |
| Financial/version rounding or mixing | Decimal strings; explicit version A/B; no inferred version number | Exact fixtures |
| Audit/log exfiltration | Allowlisted structured fields; recursive redaction; no prompt/body/token | Log capture tests |
| Audit outage hides sensitive access | Sensitive access fail-closed; non-sensitive policy in ADR-0006 | Failure injection tests |
| SSRF through source adapters | Fixed configured origins; no arbitrary URL; redirects disabled | URL/config tests |
| Dependency/protocol drift | Exact runtime pins, compatibility suite and upgrade ADR | Lock/contract/protocol tests |

## Residual risks requiring live evidence

- Managed OAuth provider/client registration compatibility.
- Backend service-identity verification and replay bounds.
- Exact Firestore IAM granularity; adapters must compensate with allowlists.
- Cloud Logging audit bucket/view IAM and retention.
- Cloud Run service/account isolation from the excluded SaaS resources.

No residual risk is resolved by granting a broader role.

