from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.fakes import make_settings


def test_demo_environment_profile_is_valid() -> None:
    settings = make_settings()
    assert settings.environment.value == "demo"
    assert settings.service_name == "projects-001-mcp"
    assert settings.allowed_host_patterns == ["testserver"]


def test_beta_environment_profile_is_valid() -> None:
    settings = make_settings("beta")
    assert settings.app_env == "prod-beta"
    assert settings.service_name == "projects-001-mcp-beta"
    assert settings.audit_read_max_days == 365


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("MCP_SERVICE_NAME", "projects-001-mcp-beta"),
        ("MCP_CLOUD_SQL_INSTANCE", "project001-489710:asia-southeast1:project-001-saas"),
        ("MCP_FIRESTORE_DATABASE_ID", "prod-beta"),
        ("MCP_ALLOWED_BUCKETS", "kyc_id_cards"),
        ("MCP_OAUTH_AUDIENCE", "https://different-resource.test"),
        ("MCP_RESOURCE_URL", "https://testserver/mcp?environment=beta"),
    ],
)
def test_environment_mismatch_fails_closed(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(**{field: value})


def test_symmetric_oauth_algorithm_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(MCP_OAUTH_ALGORITHMS="HS256")


def test_tool_rate_limit_is_bounded() -> None:
    with pytest.raises(ValidationError):
        make_settings(MCP_RATE_LIMIT_PER_MINUTE=1001)


def test_audit_retention_window_is_bounded() -> None:
    assert make_settings().audit_read_max_days == 90
    with pytest.raises(ValidationError):
        make_settings(MCP_AUDIT_READ_MAX_DAYS=366)


@pytest.mark.parametrize(
    ("environment", "days"),
    [("demo", 365), ("beta", 90)],
)
def test_audit_read_window_must_match_environment_retention(
    environment: str,
    days: int,
) -> None:
    with pytest.raises(ValidationError):
        make_settings(environment, MCP_AUDIT_READ_MAX_DAYS=days)
