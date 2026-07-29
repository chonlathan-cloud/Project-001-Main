from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.audit.emitter import StructuredAuditEmitter, redact
from app.audit.models import ProductAuditEvent
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
