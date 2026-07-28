"""Separated Product Audit and operational telemetry emitters."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Protocol

from app.audit.models import ProductAuditEvent
from app.config.settings import Settings

SENSITIVE_KEY = re.compile(
    r"(?:access|refresh|session)?_?token|password|secret|private_?key|credential|"
    r"signed_?url|share_?token|storage_?key|gcs_?path|authorization",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"(?:gs://|https?://[^\s?]+\?[^\s]*(?:signature|token|credential)=|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----)",
    re.IGNORECASE,
)


class AuditUnavailable(RuntimeError):
    pass


class AuditEmitter(Protocol):
    async def emit(self, event: ProductAuditEvent) -> None: ...


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [redact(item) for item in value]
    if isinstance(value, str) and SENSITIVE_VALUE.search(value):
        return "[REDACTED]"
    return value


class StructuredAuditEmitter:
    def __init__(self, settings: Settings) -> None:
        self._audit_logger = logging.getLogger(settings.audit_log_name)
        self._operational_logger = logging.getLogger(settings.operational_log_name)

    async def emit(self, event: ProductAuditEvent) -> None:
        try:
            payload = {
                "log_type": "product_audit",
                **event.model_dump(mode="json", exclude_none=True),
            }
            self._audit_logger.info(json.dumps(redact(payload), separators=(",", ":")))
        except Exception as exc:
            self._operational_logger.error(
                json.dumps(
                    {
                        "log_type": "operational",
                        "event": "audit_emission_failure",
                        "request_id": event.request_id,
                        "tool_name": event.tool_name,
                    },
                    separators=(",", ":"),
                )
            )
            raise AuditUnavailable("Product Audit emission failed.") from exc

    def operational(self, event: str, **fields: Any) -> None:
        safe_fields = redact(fields)
        self._operational_logger.info(
            json.dumps(
                {"log_type": "operational", "event": event, **safe_fields},
                separators=(",", ":"),
                default=str,
            )
        )
