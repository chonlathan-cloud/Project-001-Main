from __future__ import annotations

from app.audit.emitter import redact


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

