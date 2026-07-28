from __future__ import annotations

from app.config.settings import Environment
from app.policy.engine import PolicyEngine
from tests.fakes import admin_access, owner_access


def test_owner_has_implicit_mcp_permissions() -> None:
    decision = PolicyEngine(Environment.DEMO).authorize(
        owner_access(),
        required_permissions=frozenset({"mcp_access", "financial_data_read"}),
        project_id="any-project",
    )
    assert decision.allowed


def test_admin_requires_explicit_permission() -> None:
    decision = PolicyEngine(Environment.DEMO).authorize(
        admin_access("mcp_access"),
        required_permissions=frozenset({"mcp_access", "financial_data_read"}),
    )
    assert not decision.allowed
    assert decision.reason_code == "missing_product_permission"


def test_admin_is_limited_to_assigned_projects() -> None:
    policy = PolicyEngine(Environment.DEMO)
    access = admin_access("mcp_access")
    allowed = policy.authorize(
        access,
        required_permissions=frozenset({"mcp_access"}),
        project_id="10000000-0000-4000-8000-000000000001",
    )
    denied = policy.authorize(
        access,
        required_permissions=frozenset({"mcp_access"}),
        project_id="20000000-0000-4000-8000-000000000002",
    )
    assert allowed.allowed
    assert not denied.allowed
    assert denied.reason_code == "project_not_in_scope"


def test_ineligible_role_is_denied() -> None:
    access = admin_access("mcp_access").model_copy(update={"role": "inspector"})
    decision = PolicyEngine(Environment.DEMO).authorize(
        access,
        required_permissions=frozenset({"mcp_access"}),
    )
    assert not decision.allowed
    assert decision.reason_code == "role_not_eligible"

