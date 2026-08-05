"""Allowlisted Product Audit event contract."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config.settings import Environment

_CANONICAL_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_OPAQUE_RECORD_ID = re.compile(r"^rid_[0-9a-f]{24}$")


def opaque_target_record_id(value: str) -> str:
    """Return a stable, non-reversible audit correlation digest."""

    if _OPAQUE_RECORD_ID.fullmatch(value):
        return value
    normalized_value = value.casefold() if _CANONICAL_UUID.fullmatch(value) else value
    digest = hashlib.sha256(
        f"product-audit-record-v1:{normalized_value}".encode()
    ).hexdigest()[:24]
    return f"rid_{digest}"


class ProductAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_version: str = "1.0"
    event_id: str = Field(min_length=1, max_length=64)
    request_id: str = Field(min_length=1, max_length=128)
    timestamp: datetime
    environment: Environment
    client_channel: Literal["chatgpt", "codex", "internal_chat", "inspector", "unknown"]
    user_subject_id: str = Field(min_length=1, max_length=255)
    effective_role: str = Field(min_length=1, max_length=32)
    tool_name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    tool_version: str = "1.0"
    authorization_decision: Literal["allow", "deny", "error"]
    policy_reason_code: str = Field(min_length=1, max_length=64)
    target_domain: str = Field(min_length=1, max_length=64)
    target_record_ids: list[str] = Field(default_factory=list, max_length=20)
    target_version_ids: list[str] = Field(default_factory=list, max_length=20)
    sensitive_content: bool = False
    source_systems: list[str] = Field(default_factory=list, max_length=10)
    result_count: int = Field(default=0, ge=0)
    result_status: str = Field(min_length=1, max_length=32)
    latency_class: Literal["lt_1s", "1s_to_5s", "5s_to_15s", "gte_15s"]
    error_code: str | None = Field(default=None, max_length=64)

    @field_validator("target_record_ids")
    @classmethod
    def digest_record_ids(cls, values: list[str]) -> list[str]:
        return [opaque_target_record_id(value) for value in values]
