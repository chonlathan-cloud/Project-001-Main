from __future__ import annotations

import json

import httpx
import pytest

from app.adapters.backend.client import (
    BackendNotFoundOrForbidden,
    BackendReadClient,
    BackendReadOperation,
)
from tests.fakes import make_settings, owner_access


class StaticServiceIdentity:
    async def get_token(self, audience: str) -> str:
        assert audience == "https://backend.test"
        return "service-identity-token"


async def test_backend_read_uses_curated_path_and_no_authority_claims() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {"items": [], "returned_count": 0, "next_cursor": None},
            },
        )

    client = BackendReadClient(
        make_settings(),
        token_provider=StaticServiceIdentity(),
        transport=httpx.MockTransport(handler),
    )
    result = await client.read(
        BackendReadOperation.LIST_PROJECTS,
        owner_access(),
        {
            "statuses": [],
            "cursor": None,
            "limit": 20,
            "subject": "attacker-controlled-subject",
            "issuer": "https://attacker.invalid",
            "client_id": "attacker-client",
            "environment": "beta",
        },
    )

    assert result["items"] == []
    assert captured["path"] == "/api/v1/internal/mcp/projects:list"
    assert captured["authorization"] == "Bearer service-identity-token"
    assert captured["body"] == {
        "contract_version": "1.0",
        "subject": "oauth-user-001",
        "issuer": "https://issuer.test",
        "client_id": "inspector-test-client",
        "environment": "demo",
        "statuses": [],
        "cursor": None,
        "limit": 20,
    }
    assert "role" not in captured["body"]
    assert "permissions" not in captured["body"]
    assert "assigned_project_ids" not in captured["body"]


async def test_backend_read_collapses_forbidden_and_missing() -> None:
    client = BackendReadClient(
        make_settings(),
        token_provider=StaticServiceIdentity(),
        transport=httpx.MockTransport(lambda _request: httpx.Response(404)),
    )
    with pytest.raises(BackendNotFoundOrForbidden):
        await client.read(
            BackendReadOperation.GET_PROJECT,
            owner_access(),
            {"project_id": "10000000-0000-4000-8000-000000000001"},
        )
