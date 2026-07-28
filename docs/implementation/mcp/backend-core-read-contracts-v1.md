# Backend Core read contracts v1

Status: repository implementation complete for Phase 2; not deployed.

The Product Backend is authoritative for user entitlement, project scope and
business meaning. MCP authenticates the external OAuth token, then calls these
contracts with a Google-signed service identity. It sends only the verified
OAuth `subject`, `issuer`, `client_id`, locked environment and curated read
parameters. Role, permission and assigned-project claims are never forwarded as
authority.

## Trust flow

1. MCP verifies the external JWT signature, issuer, audience/resource, expiry,
   required `mcp:read` scope and environment claim.
2. MCP obtains a Google ID token whose audience is the exact Backend service URL.
3. Backend verifies that ID token and requires the exact environment-specific
   MCP service-account email.
4. Backend maps the OAuth issuer/subject to exactly one active Admin directory
   record, applies the client and rollout allowlists, and resolves memberships.
5. Every business read repeats Backend authorization before querying SQL or
   Firestore. Missing and forbidden records collapse to the same response.

## Routes

All paths have the `/api/v1/internal/mcp` prefix and accept only `POST`.

| Route | Purpose |
|---|---|
| `/access-context:resolve` | Resolve current Product role, MCP permissions and project scope |
| `/search` | Bounded Phase 2 federated Projects/BOQ search |
| `/fetch` | Resolve an authorized stable reference |
| `/projects:list` | Cursor-paginated authorized project list |
| `/projects:get` | Canonical project detail and Product citation URL |
| `/projects:summary` | Project/BOQ summary, current or point-in-time |
| `/boq:current` | Current BOQ snapshot with exact THB strings |
| `/boq/versions:list` | Deterministic BOQ version manifests |
| `/boq/versions:get` | BOQ snapshot by version ID/number or `as_of` |
| `/boq/versions:compare` | Stable-line A/B comparison |
| `/project-access:list` | Minimized access facts for one authorized project |
| `/user-access:get` | Caller-visible user entitlement facts |

POST is used for read contracts so principal context and filters do not enter
URL/query logs. No route writes Business Data.

## Backend configuration

The Backend defaults to disabled and fail-closed:

| Variable | Phase 2 requirement |
|---|---|
| `MCP_INTERNAL_ENABLED` | `true` only after Backend service IAM is ready |
| `MCP_BACKEND_AUDIENCE` | Exact canonical Backend Cloud Run URL |
| `MCP_ALLOWED_SERVICE_ACCOUNTS` | Exact MCP runtime service-account email for this environment |
| `MCP_ALLOWED_CLIENT_IDS` | Explicit OAuth client IDs accepted in this environment |
| `MCP_ALLOWED_ROLES` | `owner` for the Phase 2 Owner pilot |
| `MCP_CURSOR_SECRET` | Environment-specific secret; JWT secret is migration fallback only |

Demo and Beta must use separate Backend URLs, MCP service accounts, OAuth
clients and configuration. Admin rollout requires a later approved change to
`MCP_ALLOWED_ROLES=owner,admin`; storing an Admin entitlement alone cannot bypass
the rollout gate.

## Product entitlement record

Firestore Admin directory records support these fail-closed fields:

- `external_mcp_enabled` — defaults to `false` for legacy and new records.
- `mcp_oauth_issuer` and `mcp_oauth_subject` — configured and cleared as a pair;
  application writes reject an existing pair and resolution fails closed if a
  duplicate is ever observed.
- `mcp_permissions` — allowlisted values only.
- `mcp_all_projects_read` — explicit Admin override; Owners already have all
  projects.

Only existing Owner-protected settings mutations can change these fields. OAuth
bindings can be revoked and cleared together. Admin directory responses hide the
OAuth issuer/subject from non-Owner callers.

## Project, cursor and BOQ semantics

- Invalid membership project IDs are discarded, never interpreted broadly.
- Admin project reads are the assigned-project intersection unless an explicit
  all-project grant exists.
- List cursors are HMAC-signed, operation/scope-bound and offset-capped.
- Canonical money is `{ "amount": "1234.50", "currency": "THB" }`.
- Project-list BOQ budget is the current root-level Customer BOQ sum, not a mix
  of Customer and Subcontractor values.
- BOQ manifests are Backend-owned deterministic projections of transaction-wide
  SCD2 `valid_from` boundaries. Legacy `NULL valid_from` rows map to the epoch
  boundary; MCP never invents version numbers.
- BOQ line IDs derive from normalized BOQ type, sheet and WBS item path, so a
  replaced SCD2 row remains comparable across versions.
- BOQ snapshots return at most 500 lines. Truncated snapshots/comparisons set the
  common `partial` flag and warning at the MCP boundary.
- Search treats wildcard characters literally and emits fetchable BOQ line
  references rather than raw SQL row IDs.
- Project access views include Admin-directory, customer and subcontractor
  memberships with typed opaque IDs (`admin.*`, `customer.*`,
  `subcontractor.*`) and omit email, phone, bank, KYC and login identifiers.

## Failure contract

- Disabled or incomplete service-auth configuration: HTTP `503`.
- Missing/invalid service token: HTTP `401`.
- Authenticated but wrong service account: HTTP `403`.
- Invalid closed-schema input/cursor: HTTP `400` or validation `422`.
- Missing and unauthorized record: HTTP `404` with no distinction.
- MCP maps these to the stable structured errors defined in the common Tool
  response contract.
- MCP applies a per-instance, per-verified-subject request limit before Product
  policy/data calls; Backend applies a separate service-token defense-in-depth
  limit. Distributed quota enforcement remains a live platform control.

## Live rollout gates still open

Repository completion does not authorize deployment. Before the Owner Demo
pilot, the team must provision the dedicated service account and invoker IAM,
configure a real OAuth issuer/client, bind a consenting Owner, deploy Backend
before MCP, run MCP Inspector and Owner desktop flows, execute the Golden set,
measure p95 latency, and confirm audit/IAM isolation. Beta remains blocked until
all Demo release gates pass.
