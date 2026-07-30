from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.schemas.mcp_schema import McpPrincipalRequest
from app.services.identity_service import _ensure_valid_mcp_configuration
from app.services.mcp_access_service import resolve_mcp_access


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "production",
        "MCP_INTERNAL_ENABLED": True,
        "MCP_ALLOWED_CLIENT_IDS": "inspector-test-client",
        "MCP_ALLOWED_ROLES": "owner,admin",
        "JWT_SECRET_KEY": "unit-test-only",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def request(**overrides: object) -> McpPrincipalRequest:
    values: dict[str, object] = {
        "subject": "oauth-user-001",
        "issuer": "https://issuer.test",
        "client_id": "inspector-test-client",
        "environment": "demo",
    }
    values.update(overrides)
    return McpPrincipalRequest(**values)


def admin_entry(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "id": "admin-001",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True,
        "external_mcp_enabled": True,
        "mcp_permissions": ["mcp_access"],
        "mcp_all_projects_read": False,
        "updated_at": datetime(2026, 7, 28, tzinfo=UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_unmapped_principal_fails_closed() -> None:
    with patch(
        "app.services.mcp_access_service.get_admin_by_mcp_principal",
        return_value=None,
    ):
        access = resolve_mcp_access(request(), settings=settings())

    assert access.active is False
    assert access.external_mcp_enabled is False
    assert access.role == "pending"
    assert access.assigned_project_ids == []


def test_admin_access_comes_only_from_directory_and_memberships() -> None:
    with (
        patch(
            "app.services.mcp_access_service.get_admin_by_mcp_principal",
            return_value=admin_entry(),
        ),
        patch(
            "app.services.mcp_access_service.daily_report_service.list_membership_project_ids",
            return_value=["10000000-0000-4000-8000-000000000001"],
        ),
    ):
        access = resolve_mcp_access(request(), settings=settings())

    assert access.active is True
    assert access.role == "admin"
    assert access.permissions == ["mcp_access"]
    assert access.all_projects_read is False
    assert access.assigned_project_ids == ["10000000-0000-4000-8000-000000000001"]
    assert len(access.authorization_revision) == 24


def test_owner_has_all_projects_but_still_requires_external_enablement() -> None:
    with (
        patch(
            "app.services.mcp_access_service.get_admin_by_mcp_principal",
            return_value=admin_entry(role="owner", external_mcp_enabled=False),
        ),
        patch(
            "app.services.mcp_access_service.daily_report_service.list_membership_project_ids",
            return_value=["ignored-project"],
        ),
    ):
        access = resolve_mcp_access(request(), settings=settings())

    assert access.all_projects_read is True
    assert access.assigned_project_ids == []
    assert access.external_mcp_enabled is False


def test_wrong_client_or_environment_fails_closed_without_directory_lookup() -> None:
    with patch(
        "app.services.mcp_access_service.get_admin_by_mcp_principal"
    ) as lookup:
        wrong_client = resolve_mcp_access(
            request(client_id="unapproved-client"),
            settings=settings(),
        )
        wrong_environment = resolve_mcp_access(
            request(environment="beta"),
            settings=settings(),
        )

    assert wrong_client.active is False
    assert wrong_environment.active is False
    lookup.assert_not_called()


def test_owner_only_rollout_disables_admin_even_when_directory_flag_is_enabled() -> None:
    with (
        patch(
            "app.services.mcp_access_service.get_admin_by_mcp_principal",
            return_value=admin_entry(),
        ),
        patch(
            "app.services.mcp_access_service.daily_report_service.list_membership_project_ids",
            return_value=[],
        ),
    ):
        access = resolve_mcp_access(
            request(),
            settings=settings(MCP_ALLOWED_ROLES="owner"),
        )

    assert access.active is True
    assert access.role == "admin"
    assert access.external_mcp_enabled is False


def test_external_revocation_is_re_resolved_on_the_next_access_call() -> None:
    enabled = admin_entry(
        external_mcp_enabled=True,
        mcp_permissions=["mcp_access", "infrastructure_read"],
    )
    revoked = admin_entry(
        external_mcp_enabled=False,
        mcp_permissions=[],
        updated_at=datetime(2026, 7, 30, tzinfo=UTC),
    )
    with (
        patch(
            "app.services.mcp_access_service.get_admin_by_mcp_principal",
            side_effect=[enabled, revoked],
        ) as lookup,
        patch(
            "app.services.mcp_access_service.daily_report_service."
            "list_membership_project_ids",
            return_value=[],
        ),
    ):
        before = resolve_mcp_access(request(), settings=settings())
        after = resolve_mcp_access(request(), settings=settings())

    assert lookup.call_count == 2
    assert before.external_mcp_enabled is True
    assert set(before.permissions) == {"infrastructure_read", "mcp_access"}
    assert after.external_mcp_enabled is False
    assert after.permissions == []
    assert before.authorization_revision != after.authorization_revision


def test_invalid_membership_project_ids_are_excluded_from_authorization_scope() -> None:
    valid_project_id = "10000000-0000-4000-8000-000000000001"
    with (
        patch(
            "app.services.mcp_access_service.get_admin_by_mcp_principal",
            return_value=admin_entry(),
        ),
        patch(
            "app.services.mcp_access_service.daily_report_service.list_membership_project_ids",
            return_value=["not-a-project-id", valid_project_id, valid_project_id],
        ),
    ):
        access = resolve_mcp_access(request(), settings=settings())

    assert access.assigned_project_ids == [valid_project_id]


@pytest.mark.parametrize(
    ("enabled", "issuer", "subject"),
    [
        (False, "https://issuer.test", None),
        (False, None, "oauth-user-001"),
        (True, None, None),
    ],
)
def test_mcp_entitlement_requires_an_atomic_oauth_binding(
    enabled: bool,
    issuer: str | None,
    subject: str | None,
) -> None:
    with pytest.raises(HTTPException) as error:
        _ensure_valid_mcp_configuration(
            enabled=enabled,
            issuer=issuer,
            subject=subject,
        )

    assert error.value.status_code == 400


def test_rollout_roles_reject_non_product_mcp_roles() -> None:
    with pytest.raises(ValueError):
        settings(MCP_ALLOWED_ROLES="owner,inspector")
