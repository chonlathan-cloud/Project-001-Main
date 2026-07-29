from __future__ import annotations

from datetime import UTC, datetime

from mcp.server.auth.provider import AccessToken

from app.adapters.backend.client import BackendReadOperation
from app.audit.models import ProductAuditEvent
from app.config.settings import Environment, Settings
from app.policy.client import PolicyUnavailable
from app.policy.models import AccessContext


def make_settings(environment: str = "demo", **overrides: object) -> Settings:
    beta = environment == "beta"
    values: dict[str, object] = {
        "MCP_ENVIRONMENT": environment,
        "MCP_APP_ENV": "prod-beta" if beta else "production",
        "MCP_GCP_PROJECT_ID": "project001-489710",
        "MCP_GCP_REGION": "asia-southeast1",
        "MCP_SERVICE_NAME": "projects-001-mcp-beta" if beta else "projects-001-mcp",
        "MCP_RESOURCE_URL": (
            "https://beta.testserver/mcp" if beta else "https://testserver/mcp"
        ),
        "MCP_OAUTH_ISSUER": "https://issuer.test/",
        "MCP_OAUTH_AUDIENCE": (
            "https://beta.testserver/mcp" if beta else "https://testserver/mcp"
        ),
        "MCP_OAUTH_JWKS_URL": "https://issuer.test/jwks.json",
        "MCP_OAUTH_ALGORITHMS": "RS256",
        "MCP_OAUTH_REQUIRED_SCOPES": "mcp:read",
        "MCP_OAUTH_ENVIRONMENT_CLAIM": "app_env",
        "MCP_REQUIRE_ENVIRONMENT_CLAIM": True,
        "MCP_BACKEND_URL": "https://backend.test",
        "MCP_BACKEND_SERVICE_NAME": "projects-001-be-beta" if beta else "projects-001-be",
        "MCP_BACKEND_AUDIENCE": "https://backend.test",
        "MCP_BACKEND_ACCESS_CONTEXT_PATH": "/api/v1/internal/mcp/access-context:resolve",
        "MCP_BACKEND_TIMEOUT_SECONDS": 5,
        "MCP_CLOUD_SQL_INSTANCE": (
            "project001-489710:asia-southeast1:project-001-beta"
            if beta
            else "project001-489710:asia-southeast1:project-001"
        ),
        "MCP_FIRESTORE_DATABASE_ID": "prod-beta" if beta else "(default)",
        "MCP_ALLOWED_BUCKETS": (
            "kyc_id_cards-beta,temp_bills-beta,perm_bills-beta,"
            "project001-489710-work-inspection-beta,"
            "project001-489710-daily-reports-beta"
            if beta
            else "kyc_id_cards,temp_bills,perm_bills,"
            "project001-489710-work-inspection,"
            "project001-489710-daily-reports-demo"
        ),
        "MCP_AUDIT_LOG_NAME": "test_product_audit",
        "MCP_OPERATIONAL_LOG_NAME": "test_operational",
        "MCP_LOG_LEVEL": "INFO",
    }
    values.update(overrides)
    return Settings(**values)


class StaticTokenVerifier:
    def __init__(self, *, app_env: str = "production", scopes: list[str] | None = None) -> None:
        self.app_env = app_env
        self.scopes = scopes if scopes is not None else ["mcp:read"]

    async def verify_token(self, token: str) -> AccessToken | None:
        if token != "valid-token":
            return None
        return AccessToken(
            token=token,
            client_id="inspector-test-client",
            scopes=self.scopes,
            expires_at=4102444800,
            resource="https://testserver/mcp",
            subject="oauth-user-001",
            claims={
                "iss": "https://issuer.test",
                "sub": "oauth-user-001",
                "app_env": self.app_env,
                "client_channel": "inspector",
            },
        )


def owner_access(environment: Environment = Environment.DEMO) -> AccessContext:
    return AccessContext(
        contract_version="1.0",
        subject="oauth-user-001",
        issuer="https://issuer.test",
        client_id="inspector-test-client",
        user_id="user-owner-001",
        environment=environment,
        active=True,
        external_mcp_enabled=True,
        role="owner",
        permissions=set(),
        all_projects_read=True,
        assigned_project_ids=set(),
        authorization_revision="rev-owner-1",
        resolved_at=datetime.now(UTC),
    )


def admin_access(*permissions: str) -> AccessContext:
    return AccessContext(
        contract_version="1.0",
        subject="oauth-user-001",
        issuer="https://issuer.test",
        client_id="inspector-test-client",
        user_id="user-admin-001",
        environment=Environment.DEMO,
        active=True,
        external_mcp_enabled=True,
        role="admin",
        permissions=set(permissions),
        all_projects_read=False,
        assigned_project_ids={"10000000-0000-4000-8000-000000000001"},
        authorization_revision="rev-admin-1",
        resolved_at=datetime.now(UTC),
    )


class StaticPolicyClient:
    def __init__(self, access: AccessContext) -> None:
        self.access = access
        self.calls: list[dict[str, str]] = []

    async def resolve_access(
        self,
        *,
        subject: str,
        issuer: str,
        client_id: str,
        request_id: str,
    ) -> AccessContext:
        self.calls.append(
            {
                "subject": subject,
                "issuer": issuer,
                "client_id": client_id,
                "request_id": request_id,
            }
        )
        return self.access


class UnavailablePolicyClient:
    async def resolve_access(self, **_kwargs: str) -> AccessContext:
        raise PolicyUnavailable("test outage")


class MemoryAuditEmitter:
    def __init__(self, *, fail: bool = False) -> None:
        self.events: list[ProductAuditEvent] = []
        self.fail = fail

    async def emit(self, event: ProductAuditEvent) -> None:
        if self.fail:
            from app.audit.emitter import AuditUnavailable

            raise AuditUnavailable("test outage")
        self.events.append(event)


class StaticBackendReadClient:
    def __init__(self, responses: dict[BackendReadOperation, dict] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[dict] = []

    async def read(
        self,
        operation: BackendReadOperation,
        access: AccessContext,
        payload: dict,
    ) -> dict:
        self.calls.append(
            {"operation": operation, "access": access, "payload": payload}
        )
        return dict(self.responses.get(operation, {}))
