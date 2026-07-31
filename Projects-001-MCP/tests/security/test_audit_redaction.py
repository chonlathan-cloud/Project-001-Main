from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.audit.emitter import StructuredAuditEmitter, redact
from app.audit.models import ProductAuditEvent, opaque_target_record_id
from tests.fakes import make_settings


def test_recursive_redaction_removes_secret_fields_and_urls() -> None:
    payload = {
        "access_token": "token-value",
        "nested": {
            "signed_url": "https://storage.test/object?signature=abc",
            "safe": "value",
        },
        "items": ["gs://private-bucket/object", "safe text"],
    }
    result = redact(payload)
    assert result["access_token"] == "[REDACTED]"
    assert result["nested"]["signed_url"] == "[REDACTED]"
    assert result["nested"]["safe"] == "value"
    assert result["items"][0] == "[REDACTED]"


def test_redaction_preserves_audit_decision_but_not_authorization_data() -> None:
    payload = {
        "authorization_decision": "allow",
        "authorization": "Bearer token-value",
        "authorization_header": "Bearer token-value",
    }

    result = redact(payload)

    assert result["authorization_decision"] == "allow"
    assert result["authorization"] == "[REDACTED]"
    assert result["authorization_header"] == "[REDACTED]"


async def test_structured_audit_emitter_preserves_authorization_decision(caplog) -> None:
    emitter = StructuredAuditEmitter(make_settings())
    event = ProductAuditEvent(
        event_id="event-001",
        request_id="request-001",
        timestamp=datetime.now(UTC),
        environment="demo",
        client_channel="inspector",
        user_subject_id="subject-001",
        effective_role="owner",
        tool_name="get_current_access",
        authorization_decision="allow",
        policy_reason_code="POLICY_ALLOWED",
        target_domain="users_access",
        result_status="success",
        latency_class="lt_1s",
    )

    with caplog.at_level(logging.INFO, logger="test_product_audit"):
        await emitter.emit(event)

    payload = json.loads(caplog.records[-1].message)
    assert payload["authorization_decision"] == "allow"
    assert payload["log_type"] == "product_audit"


def test_product_audit_replaces_canonical_record_uuid_with_stable_opaque_id() -> None:
    record_uuid = "5b9adc9e-6150-4689-a5b5-c924e38c3017"
    event = ProductAuditEvent(
        event_id="event-uuid-001",
        request_id="request-uuid-001",
        timestamp=datetime.now(UTC),
        environment="demo",
        client_channel="inspector",
        user_subject_id="subject-001",
        effective_role="owner",
        tool_name="get_project",
        authorization_decision="allow",
        policy_reason_code="POLICY_ALLOWED",
        target_domain="projects_boq",
        target_record_ids=[record_uuid, "project-safe-alias"],
        result_status="success",
        latency_class="lt_1s",
    )

    assert event.target_record_ids == [
        opaque_target_record_id(record_uuid),
        "project-safe-alias",
    ]
    assert event.target_record_ids[0].startswith("rid_")
    assert record_uuid not in event.model_dump_json()
