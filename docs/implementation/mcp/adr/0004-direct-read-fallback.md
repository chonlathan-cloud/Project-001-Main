# ADR-0004: Direct source fallback policy

- Status: Accepted
- Date: 2026-07-28

## Decision

Backend business contracts are always primary. A direct source fallback may be
added only for a named tool after all of these are true:

1. The source-of-truth owner and exact bounded query are documented.
2. The tool accepts no query/path input that can alter the source target.
3. A dedicated environment-specific identity has read-only IAM/database grants.
4. Project/domain policy is enforced before source access.
5. Result limits, timeout, redaction, source metadata and conflict behavior are
   contract-tested.
6. The adapter cannot reach excluded SaaS or the other environment.

Product MCP will not ship generic SQL, Firestore path, GCS path or `gcloud`
tools. If Backend and raw source disagree, the Backend business result remains
primary and the response carries `SOURCE_INCONSISTENCY`; MCP does not merge or
repair the records.

