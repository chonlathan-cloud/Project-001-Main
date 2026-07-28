from __future__ import annotations

from typing import Any

from mcp.server.auth.provider import AccessToken

from app.tools.registry import DomainName, ToolDefinition
from app.tools.runtime import ToolPayload, ToolRuntime
from tests.fakes import MemoryAuditEmitter, StaticPolicyClient, make_settings, owner_access


def access_token() -> AccessToken:
    return AccessToken(
        token="test-token",  # noqa: S106 - inert test fixture, never a credential
        client_id="test-client",
        scopes=["mcp:read"],
        expires_at=4102444800,
        resource="https://testserver/mcp",
        subject="oauth-user-001",
        claims={
            "iss": "https://issuer.test",
            "sub": "oauth-user-001",
            "client_channel": "inspector",
        },
    )


def definition(*, sensitive: bool) -> ToolDefinition:
    return ToolDefinition(
        name="test_read",
        domain=DomainName.SYSTEM_CATALOG,
        required_permissions=frozenset({"mcp_access"}),
        planned_phase="test",
        implemented=True,
        sensitive=sensitive,
    )


async def test_sensitive_read_does_not_start_when_mandatory_audit_is_down(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr("app.tools.runtime.get_access_token", access_token)
    runtime = ToolRuntime(
        make_settings(),
        StaticPolicyClient(owner_access()),
        MemoryAuditEmitter(fail=True),
    )
    operation_called = False

    async def operation(_access: Any) -> ToolPayload:
        nonlocal operation_called
        operation_called = True
        return ToolPayload(data={"should_not": "be returned"})

    result = await runtime.execute(definition(sensitive=True), operation)

    assert operation_called is False
    assert result["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert "data" not in result


async def test_non_sensitive_read_is_marked_when_audit_is_degraded(monkeypatch: Any) -> None:
    monkeypatch.setattr("app.tools.runtime.get_access_token", access_token)
    runtime = ToolRuntime(
        make_settings(),
        StaticPolicyClient(owner_access()),
        MemoryAuditEmitter(fail=True),
    )

    async def operation(_access: Any) -> ToolPayload:
        return ToolPayload(data={"safe": "catalog"})

    result = await runtime.execute(definition(sensitive=False), operation)

    assert result["data"] == {"safe": "catalog"}
    assert result["warnings"][0]["code"] == "AUDIT_DEGRADED"
