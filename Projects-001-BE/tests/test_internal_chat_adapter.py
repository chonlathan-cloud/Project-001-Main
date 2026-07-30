from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.deps.auth import AuthenticatedUser
from app.core.config import Settings
from app.schemas.mcp_schema import McpDashboardSummaryRequest
from app.services.internal_chat_adapter import (
    analyze_internal_chat_question,
    resolve_internal_chat_access,
)
from app.services.mcp_read_service import _authorize


def settings() -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="test",
        FRONTEND_BASE_URL="https://product.test",
        JWT_SECRET_KEY="unit-test-only",  # noqa: S106 - inert fixture
        MCP_CURSOR_SECRET="cursor-test-only",  # noqa: S106 - inert fixture
    )


def user() -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="session-user-001",
        role="owner",
        roles=("owner",),
        email="owner@example.com",
    )


def entry(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "id": "owner-001",
        "email": "owner@example.com",
        "role": "owner",
        "is_active": True,
        "mcp_permissions": [],
        "mcp_all_projects_read": False,
        "updated_at": datetime(2026, 7, 30, tzinfo=UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_internal_chat_reresolves_directory_access_without_external_enablement() -> None:
    with (
        patch(
            "app.services.internal_chat_adapter.get_admin_by_email",
            return_value=entry(),
        ),
        patch(
            "app.services.internal_chat_adapter.daily_report_service."
            "list_membership_project_ids",
            return_value=[],
        ),
    ):
        access = resolve_internal_chat_access(user())

    assert access.active is True
    assert access.role == "owner"
    assert access.all_projects_read is True
    assert access.authorization_revision


def test_internal_chat_admin_requires_shared_finance_permissions() -> None:
    admin_user = AuthenticatedUser(
        subject="session-admin-001",
        role="admin",
        roles=("admin",),
        email="admin@example.com",
    )
    with patch(
        "app.services.internal_chat_adapter.get_admin_by_email",
        return_value=entry(
            id="admin-001",
            email="admin@example.com",
            role="admin",
            mcp_permissions=["mcp_access"],
        ),
    ):
        with pytest.raises(HTTPException) as error:
            resolve_internal_chat_access(admin_user)

    assert error.value.status_code == 403


def test_internal_chat_dashboard_facts_match_shared_contract_exactly() -> None:
    contract = {
        "items": [{"project_id": "10000000-0000-4000-8000-000000000001"}],
        "totals": {
            "budget": {"amount": "1000.10", "currency": "THB"},
            "actual": {"amount": "250.05", "currency": "THB"},
            "remaining": {"amount": "750.05", "currency": "THB"},
            "pending_requested": {"amount": "20.02", "currency": "THB"},
            "net_approved_cashflow": {"amount": "-200.02", "currency": "THB"},
        },
        "returned_count": 1,
        "calculation_method": "shared-dashboard-v1",
        "source_references": [
            {
                "domain": "finance_payments",
                "record_id": "10000000-0000-4000-8000-000000000001",
                "source_system": "product_backend",
            }
        ],
        "source_read_at": datetime(2026, 7, 30, tzinfo=UTC),
    }
    access = SimpleNamespace(authorization_revision="revision-001")
    with (
        patch(
            "app.services.internal_chat_adapter.resolve_internal_chat_access",
            return_value=access,
        ),
        patch(
            "app.services.internal_chat_adapter.get_dashboard_summary",
            new=AsyncMock(return_value=contract),
        ) as shared_contract,
    ):
        result = asyncio.run(
            analyze_internal_chat_question(
                object(),
                user=user(),
                question="สรุป cash flow",
                settings=settings(),
            )
        )

    shared_contract.assert_awaited_once()
    values = {item["id"]: item["value"] for item in result["metrics"]}
    assert values == {
        "budget": "THB 1000.10",
        "actual": "THB 250.05",
        "remaining": "THB 750.05",
        "pending": "THB 20.02",
        "cashflow": "THB -200.02",
    }
    assert result["grounding"] == {
        "contract": "get_dashboard_summary",
        "calculation_method": "shared-dashboard-v1",
        "authorization_revision": "revision-001",
    }


def test_shared_authorizer_accepts_internal_context_without_external_flag() -> None:
    request = McpDashboardSummaryRequest(
        subject="session-user-001",
        issuer="https://internal.projects-001.invalid",
        client_id="internal_chat",
        environment="demo",
    )
    access = SimpleNamespace(
        active=True,
        external_mcp_enabled=False,
        role="admin",
        permissions={"mcp_access", "financial_data_read"},
        all_projects_read=True,
        assigned_project_ids=set(),
    )

    resolved = _authorize(
        request,
        required_permissions=frozenset({"financial_data_read"}),
        access_context=access,
    )

    assert resolved is access
