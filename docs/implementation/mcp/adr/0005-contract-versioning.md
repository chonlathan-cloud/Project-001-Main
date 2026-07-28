# ADR-0005: Contract versioning and compatibility

- Status: Accepted
- Date: 2026-07-28

## Decision

Tool envelopes and Backend internal reads begin at schema version `1.0`.
Published tool names and required fields are stable. Compatible releases may add
optional fields or enum values only when clients are required to ignore unknown
values. Breaking input/output or semantic changes require a new major schema and,
when client ambiguity is possible, a new tool name.

Services exchange versioned JSON/Pydantic/OpenAPI contracts and do not import each
other's source directories. Contract JSON Schema snapshots and examples are test
artifacts. Exact money remains a decimal string across service boundaries.

BOQ and Daily Report document versions are domain entities, not API schema
versions. Share-link state is a separate entity from document/report version.

