from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from starlette.testclient import TestClient

from app.adapters.gcp.client import (
    GoogleCloudOperationsClient,
    _safe_summary,
    build_application_error_filter,
)
from app.server.factory import create_app
from tests.fakes import (
    MemoryAuditEmitter,
    StaticBackendReadClient,
    StaticGcpOperationsClient,
    StaticPolicyClient,
    StaticTokenVerifier,
    admin_access,
    make_settings,
    owner_access,
)


def _rpc(name: str, arguments: dict | None = None) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments or {}},
    }


def _headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer valid-token",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }


def _call(
    name: str,
    arguments: dict | None,
    *,
    policy: StaticPolicyClient,
    gcp: StaticGcpOperationsClient,
    audit: MemoryAuditEmitter | None = None,
    backend: StaticBackendReadClient | None = None,
) -> dict:
    app = create_app(
        make_settings(),
        token_verifier=StaticTokenVerifier(),
        policy_client=policy,
        audit_emitter=audit or MemoryAuditEmitter(),
        backend_read_client=backend or StaticBackendReadClient(),
        gcp_operations_client=gcp,
    )
    with TestClient(app, base_url="https://testserver") as client:
        response = client.post("/mcp", headers=_headers(), json=_rpc(name, arguments))
    return response.json()["result"]["structuredContent"]


def test_admin_requires_infrastructure_permission_before_gcp_read() -> None:
    gcp = StaticGcpOperationsClient()
    result = _call(
        "get_system_health",
        {},
        policy=StaticPolicyClient(admin_access("mcp_access")),
        gcp=gcp,
    )

    assert result["error"]["code"] == "NOT_FOUND_OR_FORBIDDEN"
    assert gcp.calls == []


def test_cloud_run_alias_returns_only_safe_adapter_fields() -> None:
    gcp = StaticGcpOperationsClient(
        {
            "get_cloud_run_status": {
                "service_alias": "backend",
                "status": "available",
                "latest_ready_revision": "projects-001-be-00121-test",
                "ready_traffic_percent": 100,
                "condition": "CONDITION_SUCCEEDED",
                "last_updated_at": "2026-07-30T00:00:00Z",
                "source_read_at": "2026-07-30T00:00:01Z",
            }
        }
    )
    result = _call(
        "get_cloud_run_status",
        {"service_alias": "backend"},
        policy=StaticPolicyClient(admin_access("mcp_access", "infrastructure_read")),
        gcp=gcp,
    )

    assert result["data"]["service_alias"] == "backend"
    assert result["data"]["ready_traffic_percent"] == 100
    serialized = str(result).lower()
    assert "project-saas" not in serialized
    assert "serviceaccount" not in serialized
    assert "env" not in result["data"]


def test_application_error_range_is_bounded_before_logging_read() -> None:
    gcp = StaticGcpOperationsClient()
    now = datetime.now(UTC)
    result = _call(
        "search_application_errors",
        {
            "date_from": (now - timedelta(days=31)).isoformat(),
            "date_to": now.isoformat(),
        },
        policy=StaticPolicyClient(owner_access()),
        gcp=gcp,
    )

    assert result["error"]["code"] == "INVALID_INPUT"
    assert gcp.calls == []


def test_sensitive_application_error_read_fails_closed_when_audit_is_down() -> None:
    gcp = StaticGcpOperationsClient()
    now = datetime.now(UTC)
    result = _call(
        "search_application_errors",
        {
            "date_from": (now - timedelta(hours=1)).isoformat(),
            "date_to": now.isoformat(),
        },
        policy=StaticPolicyClient(owner_access()),
        gcp=gcp,
        audit=MemoryAuditEmitter(fail=True),
    )

    assert result["error"]["code"] == "SOURCE_UNAVAILABLE"
    assert gcp.calls == []


def test_logging_filter_contains_only_exact_product_services() -> None:
    settings = make_settings()
    now = datetime.now(UTC)
    result = build_application_error_filter(
        settings,
        date_from=now - timedelta(hours=1),
        date_to=now,
        service_alias=None,
        workflow="boq_sync",
        severities=["ERROR"],
    )

    assert 'service_name="projects-001-fe"' in result
    assert 'service_name="projects-001-be"' in result
    assert 'service_name="projects-001-mcp"' in result
    assert "project-saas-001" not in result
    assert "bigquery" not in result.lower()
    assert 'jsonPayload.workflow="boq_sync"' in result


def _phase5_tool_cases() -> list[tuple[str, dict]]:
    now = datetime.now(UTC)
    return [
        ("get_system_health", {}),
        ("get_gcp_resource_summary", {}),
        ("get_cloud_run_status", {"service_alias": "backend"}),
        (
            "search_application_errors",
            {
                "date_from": (now - timedelta(hours=1)).isoformat(),
                "date_to": now.isoformat(),
            },
        ),
        ("get_data_source_health", {}),
        (
            "get_processing_status",
            {"workflow": "boq_sync", "job_id": "job-demo-001"},
        ),
    ]


@pytest.mark.parametrize(("tool_name", "arguments"), _phase5_tool_cases())
def test_admin_allow_matrix_requires_both_mcp_and_infrastructure_permissions(
    tool_name: str,
    arguments: dict,
) -> None:
    gcp = StaticGcpOperationsClient()
    backend = StaticBackendReadClient()
    result = _call(
        tool_name,
        arguments,
        policy=StaticPolicyClient(admin_access("mcp_access", "infrastructure_read")),
        gcp=gcp,
        backend=backend,
    )

    assert result.get("error") is None
    assert len(gcp.calls) + len(backend.calls) == 1


@pytest.mark.parametrize(("tool_name", "arguments"), _phase5_tool_cases())
def test_admin_deny_matrix_stops_all_operations_before_source_reads(
    tool_name: str,
    arguments: dict,
) -> None:
    gcp = StaticGcpOperationsClient()
    backend = StaticBackendReadClient()
    result = _call(
        tool_name,
        arguments,
        policy=StaticPolicyClient(admin_access("mcp_access")),
        gcp=gcp,
        backend=backend,
    )

    assert result["error"]["code"] == "NOT_FOUND_OR_FORBIDDEN"
    assert gcp.calls == []
    assert backend.calls == []


def test_error_summary_redacts_credentials_urls_paths_pii_and_record_ids() -> None:
    result = _safe_summary(
        "Authorization: Bearer demo-secret at https://private.example/path "
        "for owner@example.com gs://private-bucket/object "
        "10000000-0000-4000-8000-000000000001"
    )

    lowered = result.lower()
    assert "demo-secret" not in lowered
    assert "private.example" not in lowered
    assert "owner@example.com" not in lowered
    assert "gs://" not in lowered
    assert "10000000-0000-4000-8000-000000000001" not in lowered


def test_application_error_search_reads_only_the_locked_operational_view() -> None:
    class CapturingClient(GoogleCloudOperationsClient):
        def __init__(self) -> None:
            super().__init__(make_settings())
            self.body: dict | None = None

        def _authorized_json(
            self,
            method: str,
            url: str,
            *,
            body: dict | None = None,
        ) -> dict:
            self.body = body
            return {"entries": []}

    client = CapturingClient()
    now = datetime.now(UTC)
    asyncio.run(
        client.search_application_errors(
            date_from=now - timedelta(hours=1),
            date_to=now,
            service_alias=None,
            workflow=None,
            severities=["ERROR"],
            cursor=None,
            limit=20,
        )
    )

    assert client.body is not None
    assert client.body["resourceNames"] == [make_settings().operational_log_view]
    assert "project-saas-001" not in client.body["filter"]
