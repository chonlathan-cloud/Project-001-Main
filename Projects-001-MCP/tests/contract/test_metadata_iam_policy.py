from app.config.metadata_iam_policy import (
    REQUIRED_METADATA_PERMISSIONS,
    policy_has_exact_binding,
    role_has_exact_permissions,
)

ROLE = "projects/project001-489710/roles/projects001McpMetadataReader"
MEMBER = (
    "serviceAccount:projects-001-mcp-demo@"
    "project001-489710.iam.gserviceaccount.com"
)
CONDITION = (
    'resource.type == "sqladmin.googleapis.com/Instance" && '
    'resource.name == "projects/project001-489710/instances/project-001"'
)


def test_role_requires_exact_read_only_metadata_permissions() -> None:
    assert role_has_exact_permissions(
        {
            "includedPermissions": sorted(REQUIRED_METADATA_PERMISSIONS),
            "stage": "GA",
        }
    )


def test_role_rejects_missing_extra_or_disabled_permissions() -> None:
    permissions = sorted(REQUIRED_METADATA_PERMISSIONS)
    assert not role_has_exact_permissions(
        {"includedPermissions": permissions[:-1], "stage": "GA"}
    )
    assert not role_has_exact_permissions(
        {"includedPermissions": [*permissions, "storage.objects.get"], "stage": "GA"}
    )
    assert not role_has_exact_permissions(
        {"includedPermissions": permissions, "stage": "DISABLED"}
    )


def test_policy_accepts_exact_unconditional_resource_binding() -> None:
    policy = {"bindings": [{"role": ROLE, "members": [MEMBER]}]}
    assert policy_has_exact_binding(
        policy,
        role=ROLE,
        member=MEMBER,
        condition_expression=None,
    )


def test_policy_rejects_wrong_role_member_or_unexpected_condition() -> None:
    policy = {
        "bindings": [
            {
                "role": ROLE,
                "members": [MEMBER],
                "condition": {"expression": CONDITION},
            }
        ]
    }
    assert not policy_has_exact_binding(
        policy,
        role=ROLE,
        member=MEMBER,
        condition_expression=None,
    )
    assert not policy_has_exact_binding(
        policy,
        role=f"{ROLE}Typo",
        member=MEMBER,
        condition_expression=CONDITION,
    )
    assert not policy_has_exact_binding(
        policy,
        role=ROLE,
        member="serviceAccount:other@example.invalid",
        condition_expression=CONDITION,
    )


def test_policy_accepts_only_the_exact_normalized_condition() -> None:
    policy = {
        "bindings": [
            {
                "role": ROLE,
                "members": [MEMBER],
                "condition": {"expression": f"  {CONDITION}  "},
            }
        ]
    }
    assert policy_has_exact_binding(
        policy,
        role=ROLE,
        member=MEMBER,
        condition_expression=CONDITION,
    )
    assert not policy_has_exact_binding(
        policy,
        role=ROLE,
        member=MEMBER,
        condition_expression=CONDITION.replace("project-001", "project-001-beta"),
    )
