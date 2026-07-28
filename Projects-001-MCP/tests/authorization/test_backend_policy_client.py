from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx

from app.policy.client import BackendPolicyClient
from tests.fakes import make_settings


class StaticServiceIdentity:
    async def get_token(self, audience: str) -> str:
        assert audience == "https://backend.test"
        return "service-identity-token"


async def test_backend_policy_uses_service_identity_and_verified_coordinates_only() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": {
                    "contract_version": "1.0",
                    "subject": "oauth-user-001",
                    "issuer": "https://issuer.test",
                    "client_id": "codex-client",
                    "user_id": "user-001",
                    "environment": "demo",
                    "active": True,
                    "external_mcp_enabled": True,
                    "role": "admin",
                    "permissions": ["mcp_access"],
                    "all_projects_read": False,
                    "assigned_project_ids": [],
                    "authorization_revision": "rev-1",
                    "resolved_at": datetime.now(UTC).isoformat(),
                }
            },
        )

    client = BackendPolicyClient(
        make_settings(),
        token_provider=StaticServiceIdentity(),
        transport=httpx.MockTransport(handler),
    )
    access = await client.resolve_access(
        subject="oauth-user-001",
        issuer="https://issuer.test",
        client_id="codex-client",
        request_id="request-001",
    )
    assert access.role == "admin"
    assert captured["authorization"] == "Bearer service-identity-token"
    assert captured["body"] == {
        "contract_version": "1.0",
        "subject": "oauth-user-001",
        "issuer": "https://issuer.test",
        "client_id": "codex-client",
        "environment": "demo",
    }
    assert "role" not in captured["body"]
    assert "permissions" not in captured["body"]
