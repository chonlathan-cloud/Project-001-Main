from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.audit.client import (
    AuditReadInvalidInput,
    _safe_event,
    build_audit_filter,
)
from tests.fakes import make_settings


def test_audit_filter_is_server_built_and_resource_scoped() -> None:
    result = build_audit_filter(
        make_settings(),
        date_from=datetime(2026, 7, 1, tzinfo=UTC),
        date_to=datetime(2026, 7, 29, tzinfo=UTC),
        tool_names=["read_document_content"],
        decisions=["allow"],
        domain="gcs_files",
        subject_id="user-admin-001",
    )

    assert 'resource.type="cloud_run_revision"' in result
    assert 'resource.labels.service_name="projects-001-mcp"' in result
    assert 'jsonPayload.log_type="product_audit"' in result
    assert 'jsonPayload.tool_name="read_document_content"' in result
    assert 'textPayload:"\\\"tool_name\\\":\\\"read_document_content\\\""' in result
    assert 'jsonPayload.authorization_decision="allow"' in result
    assert 'textPayload:"\\\"authorization_decision\\\":\\\"allow\\\""' in result
    assert 'jsonPayload.target_domain="gcs_files"' in result
    assert 'textPayload:"\\\"target_domain\\\":\\\"gcs_files\\\""' in result
    assert 'jsonPayload.user_subject_id="user-admin-001"' in result
    assert 'textPayload:"\\\"user_subject_id\\\":\\\"user-admin-001\\\""' in result
    assert "SELECT" not in result


def test_audit_filter_rejects_quoted_values() -> None:
    with pytest.raises(AuditReadInvalidInput):
        build_audit_filter(
            make_settings(),
            date_from=datetime(2026, 7, 1, tzinfo=UTC),
            date_to=datetime(2026, 7, 29, tzinfo=UTC),
            tool_names=['read_document_content" OR true'],
            decisions=[],
            domain=None,
            subject_id=None,
        )


def test_audit_event_parser_allowlists_contract_fields_only() -> None:
    event = {
        "log_type": "product_audit",
        "event_version": "1.0",
        "event_id": "audit_event_001",
        "request_id": "request-001",
        "timestamp": "2026-07-29T00:00:00Z",
        "environment": "demo",
        "client_channel": "inspector",
        "user_subject_id": "user-admin-001",
        "effective_role": "admin",
        "tool_name": "read_document_content",
        "tool_version": "1.0",
        "authorization_decision": "allow",
        "policy_reason_code": "policy_allow",
        "target_domain": "gcs_files",
        "target_record_ids": ["doc_opaque_001"],
        "target_version_ids": [],
        "sensitive_content": True,
        "source_systems": ["product_backend"],
        "result_count": 1,
        "result_status": "success",
        "latency_class": "lt_1s",
        "error_code": None,
        "document_body": "must never leave the adapter",
        "prompt": "also forbidden",
    }
    result = _safe_event({"jsonPayload": event})

    assert result is not None
    assert result["event_id"] == "audit_event_001"
    assert "document_body" not in result
    assert "prompt" not in result


def test_audit_event_parser_accepts_cloud_run_logger_prefixed_text_payload() -> None:
    text_payload = (
        "INFO:projects_001_mcp_product_audit_demo:"
        '{"log_type":"product_audit","event_version":"1.0",'
        '"event_id":"audit_event_002","request_id":"request-002",'
        '"timestamp":"2026-07-29T00:00:00Z","environment":"demo",'
        '"client_channel":"inspector","user_subject_id":"owner-001",'
        '"effective_role":"owner","tool_name":"list_daily_reports",'
        '"tool_version":"1.0","authorization_decision":"allow",'
        '"policy_reason_code":"policy_allow","target_domain":"daily_reports",'
        '"target_record_ids":[],"target_version_ids":[],"sensitive_content":false,'
        '"source_systems":["product_backend"],"result_count":1,'
        '"result_status":"success","latency_class":"lt_1s"}'
    )

    result = _safe_event({"textPayload": text_payload})

    assert result is not None
    assert result["event_id"] == "audit_event_002"
    assert result["tool_name"] == "list_daily_reports"
