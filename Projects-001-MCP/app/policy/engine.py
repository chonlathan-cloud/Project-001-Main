"""Deny-by-default Product MCP authorization policy."""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import Environment
from app.policy.models import AccessContext


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason_code: str


class PolicyEngine:
    ELIGIBLE_ROLES = frozenset({"owner", "admin"})

    def __init__(self, environment: Environment) -> None:
        self._environment = environment

    def authorize(
        self,
        access: AccessContext,
        *,
        required_permissions: frozenset[str],
        project_id: str | None = None,
    ) -> AuthorizationDecision:
        if access.environment != self._environment:
            return AuthorizationDecision(False, "environment_mismatch")
        if not access.active:
            return AuthorizationDecision(False, "account_inactive")
        if access.role not in self.ELIGIBLE_ROLES:
            return AuthorizationDecision(False, "role_not_eligible")
        if not access.external_mcp_enabled:
            return AuthorizationDecision(False, "external_mcp_disabled")

        if access.role != "owner":
            missing = required_permissions.difference(access.permissions)
            if missing:
                return AuthorizationDecision(False, "missing_product_permission")

        if project_id and access.role != "owner" and not access.all_projects_read:
            if project_id not in access.assigned_project_ids:
                return AuthorizationDecision(False, "project_not_in_scope")

        return AuthorizationDecision(True, "policy_allow")

