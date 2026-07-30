"""Validate the exact least-privilege IAM boundary for GCP metadata reads."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from typing import Any

REQUIRED_METADATA_PERMISSIONS = frozenset(
    {
        "artifactregistry.repositories.get",
        "cloudsql.instances.get",
        "datastore.databases.get",
        "logging.logEntries.list",
        "logging.views.get",
        "run.services.get",
        "storage.buckets.get",
    }
)


def _normalized_condition(expression: str) -> str:
    return " ".join(expression.split())


def role_has_exact_permissions(role: Mapping[str, Any]) -> bool:
    """Return whether a custom role contains only the approved metadata reads."""

    permissions = role.get("includedPermissions")
    if not isinstance(permissions, list) or any(
        not isinstance(permission, str) for permission in permissions
    ):
        return False
    if frozenset(permissions) != REQUIRED_METADATA_PERMISSIONS:
        return False
    if role.get("deleted") is True:
        return False
    return str(role.get("stage") or "").upper() not in {"DISABLED", "DEPRECATED"}


def policy_has_exact_binding(
    policy: Mapping[str, Any],
    *,
    role: str,
    member: str,
    condition_expression: str | None,
) -> bool:
    """Return whether a policy has the expected exact role/member/condition binding."""

    bindings = policy.get("bindings")
    if not isinstance(bindings, list):
        return False
    expected_condition = (
        _normalized_condition(condition_expression) if condition_expression else None
    )
    for binding in bindings:
        if not isinstance(binding, Mapping) or binding.get("role") != role:
            continue
        members = binding.get("members")
        if not isinstance(members, list) or member not in members:
            continue
        condition = binding.get("condition")
        if expected_condition is None:
            if not condition:
                return True
            continue
        if not isinstance(condition, Mapping):
            continue
        actual_expression = condition.get("expression")
        if isinstance(actual_expression, str) and (
            _normalized_condition(actual_expression) == expected_condition
        ):
            return True
    return False


def main(argv: Sequence[str] | None = None) -> int:
    """Validate a role or one policy binding from JSON on stdin."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        return 2
    if not isinstance(payload, Mapping) or not arguments:
        return 2

    if arguments == ["role"]:
        return 0 if role_has_exact_permissions(payload) else 1

    if arguments[0] == "binding" and len(arguments) in {3, 4}:
        condition_expression = arguments[3] if len(arguments) == 4 else None
        valid = policy_has_exact_binding(
            payload,
            role=arguments[1],
            member=arguments[2],
            condition_expression=condition_expression,
        )
        return 0 if valid else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
