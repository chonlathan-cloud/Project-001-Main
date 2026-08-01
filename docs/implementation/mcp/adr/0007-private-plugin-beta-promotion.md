# ADR-0007: Private plugin package and digest promotion

Status: Accepted for Phase 6 repository implementation

## Decision

Package the private integration as `projects-001-product` using the current
plugin manifest, a registered ChatGPT app mapping, and the bundled
`projects-001-workflows` skill. The repository keeps `.app.json` unbound until
ChatGPT Developer mode creates the real `plugin_asdk_app...` ID. A validated
binding helper materializes the mapping; placeholder IDs are rejected.

Share the installed plugin only with the approved ChatGPT workspace Owner and
selected Admin groups. Workspace sharing is not public directory publication.

Promote to Beta only by immutable Artifact Registry digest after that exact
image passes Demo. Beta uses its own MCP service, service account, OAuth
resource/client boundary, Backend, database, buckets, audit view, and
operational view. The deployment helper must not rebuild a different Beta
image.

## Rationale

ChatGPT assigns the registered app connection ID outside the repository, so a
real mapping cannot be safely invented during source implementation. Digest
promotion makes the Beta artifact identical to the tested Demo artifact and
keeps rollback attributable. Product per-call authorization remains the final
gate even after a user installs the plugin.

## Consequences

- Repository validation can pass while live plugin binding and compatibility
  remain pending evidence.
- The app ID must be bound in the release copy before installation testing.
- The private package carries no credential and does not replace OAuth.
- Phase 7 public submission requires separate privacy, security, support, and
  business approval.
