# Projects-001 Product MCP

Standalone, read-only Product MCP service for Projects-001. The service provides
a Streamable HTTP `/mcp` endpoint, OAuth resource-server validation, per-call
Product policy resolution, common envelopes, separated audit telemetry, and the
Phase 2 Core Business Owner Pilot tools.

## Current scope

Implemented tools:

- `get_system_catalog`
- `describe_domain`
- `get_current_access`
- `search`
- `fetch`
- `list_projects`
- `get_project`
- `get_project_summary`
- `get_boq_current`
- `list_boq_versions`
- `get_boq_version`
- `compare_boq_versions`
- `list_project_access`
- `get_user_access`

They require a valid OAuth access token and a successful response from the
service-authenticated Backend contracts. The MCP forwards only the verified OAuth
subject, issuer, client ID and locked environment; the Backend re-resolves role,
permissions and project scope for every call. Production has no auth bypass.

Phase 2 is configured as an Owner-only rollout by default. Admin support remains
implemented behind the Backend `MCP_ALLOWED_ROLES` rollout gate and must not be
enabled before the Admin pilot gate.

## Local setup

```bash
cd Projects-001-MCP
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.server.main:app --reload --port 8080
```

The example OAuth/backend URLs are intentionally non-functional. Configure a
standards-compliant Demo issuer and the service-authenticated Backend contract
before attempting authenticated calls.

## Verification

```bash
ruff check app tests
pytest
docker build --tag projects-001-mcp:local .
```

Deployment is intentionally separate from the Backend lifecycle. From the
repository root, copy the matching `mcp.deploy.*.example` and
`cloudrun-mcp*.env.yaml.example`, replace placeholders, then run
`./deploy_mcp.sh --preflight-only`. Omit `--preflight-only` only when a real
deployment has been explicitly approved.

## Security properties

- No Product session-token reuse and no inbound-token passthrough.
- Asymmetric OAuth JWT verification with issuer, audience/resource, expiry,
  environment and scope checks.
- Product authorization is re-resolved for each tool call.
- Owner-only rollout by default; future Admin access needs both rollout inclusion
  and explicit `mcp_access`.
- No environment input, generic query/path tool or business write.
- Bounded inputs plus per-verified-subject and Backend defense-in-depth rate
  limits.
- Audit and operational log schemas are separate and recursively redacted.

See `docs/implementation/mcp/` for contracts, ADRs and phase status.
