# Authorization matrix and test cases

Authorization is deny-by-default and evaluated after OAuth token validation by
re-resolving Product access. Token role/permission claims never grant access.

## Capability matrix

| Capability | Owner | Admin | Other roles |
|---|---|---|---|
| `mcp_access` | Implicit while active and External MCP is enabled | Explicit per-user entitlement | Deny |
| All projects | Yes | Only with `all_projects_read` | Deny |
| Assigned projects | All | Intersection of assigned IDs unless all-project grant | Deny |
| Finance | Yes | `financial_data_read` | Deny |
| Sensitive document body | Yes, unless `external_ai_blocked` | `sensitive_documents_read`, unless blocked | Deny |
| Infrastructure | Yes | `infrastructure_read` | Deny |
| Product Audit | Yes | `audit_log_read` | Deny |
| Enable External MCP / grant access | Product Settings only | Deny | Deny |

OAuth scopes are coarse client grants. Product permissions are the final gate;
having a scope never elevates Product access.

The Phase 2 Demo cohort is additionally constrained by Backend
`MCP_ALLOWED_ROLES=owner`. Admin behavior in this matrix describes the designed
post-Owner-pilot capability; it remains denied until that explicit rollout gate
is changed and the Admin pilot is approved.

## Mandatory cases

| Case | Expected result |
|---|---|
| Missing, malformed, expired or bad-signature token | HTTP 401 before tool execution |
| Correct issuer but Demo token presented to Beta resource | HTTP 401 |
| Token lacks `mcp:read` | HTTP 403 scope challenge |
| Active Owner, External MCP enabled | Foundation tools allowed |
| Active Owner, External MCP disabled | Deny |
| Active Admin without `mcp_access` | Deny |
| Active Admin with `mcp_access`, assigned Project A, reads A | Deny in Owner-only rollout; allow after approved Admin rollout |
| Same Admin reads Project B by guessed ID | `NOT_FOUND_OR_FORBIDDEN` |
| Admin with finance scope but no Product finance permission | Deny |
| Admin with Product finance permission but OAuth scope absent | Deny |
| Disabled/revoked account after a previously valid call | Next call denied after no more than the approved short cache TTL |
| Inspector/staff/subcontractor/customer/pending/public user | Deny all Product MCP tools |
| User-supplied role, permission or project in arguments | Ignore as untrusted; schema rejects unknown fields |
| Policy source unavailable | Fail closed; no business data returned |
| Sensitive content when mandatory audit emit fails | Fail closed |

## Project scope algorithm

1. Verify subject, issuer, audience/resource, expiry and OAuth scope.
2. Resolve the active Product principal from the Backend using service identity.
3. Require eligible role and `mcp_access`.
4. For Owner or `all_projects_read`, allow the requested existing Project.
5. Otherwise require the Project ID in the Backend-resolved assigned set.
6. Apply domain permission and record-level classification.
7. Audit the decision using opaque target IDs.
8. Only then read the source.
