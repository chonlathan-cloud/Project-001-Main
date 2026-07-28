# ADR-0001: MCP-to-Backend delegated user context

- Status: Accepted for Foundation
- Date: 2026-07-28

## Decision

The MCP calls a versioned Backend resolver at
`POST /api/v1/internal/mcp/access-context:resolve` using the MCP Cloud Run
service identity. The body contains only verified identity coordinates:

```json
{
  "contract_version": "1.0",
  "subject": "oauth-subject",
  "issuer": "https://issuer.example",
  "client_id": "oauth-client-id",
  "environment": "demo"
}
```

The Backend authenticates and allowlists the calling service account, binds it to
the environment, maps `(issuer, subject)` to the Product user, and returns active
state, eligible role, MCP entitlements, domain permissions, assigned projects and
an authorization revision. The MCP never sends user-controlled role, permissions,
email-as-authority, or project grants.

The external bearer token is never forwarded. If the resolver is unavailable or
returns an invalid contract, MCP fails closed.

## Consequences

- A new Backend internal read contract is required before a real user tool call.
- Service-to-service identity and user authorization remain separate controls.
- Revocation takes effect per call, or within a future explicitly approved cache
  TTL keyed by subject and authorization revision.

