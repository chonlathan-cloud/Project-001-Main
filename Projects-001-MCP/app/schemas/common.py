"""Common Product MCP response and error contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.config.settings import Environment


def utc_now() -> datetime:
    return datetime.now(UTC)


class ErrorCode(StrEnum):
    UNAUTHENTICATED = "UNAUTHENTICATED"
    NOT_FOUND_OR_FORBIDDEN = "NOT_FOUND_OR_FORBIDDEN"
    INVALID_INPUT = "INVALID_INPUT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    PARTIAL_RESULT = "PARTIAL_RESULT"
    RATE_LIMITED = "RATE_LIMITED"
    UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"
    SOURCE_INCONSISTENCY = "SOURCE_INCONSISTENCY"
    READ_ONLY_POLICY_DENIED = "READ_ONLY_POLICY_DENIED"


class WarningItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=500)


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str = Field(min_length=1, max_length=64)
    record_id: str = Field(min_length=1, max_length=255)
    source_system: str = Field(min_length=1, max_length=64)
    version: str | None = Field(default=None, max_length=128)
    last_updated_at: datetime | None = None
    product_url: str | None = Field(default=None, max_length=2048)


class Pagination(BaseModel):
    model_config = ConfigDict(extra="forbid")

    returned_count: int = Field(ge=0)
    next_cursor: str | None = Field(default=None, max_length=1024)


class AccessScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    all_projects: bool = False
    project_ids: list[str] = Field(default_factory=list, max_length=1000)
    permissions_applied: list[str] = Field(default_factory=list, max_length=32)


class Freshness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_read_at: datetime
    cache_status: str = Field(default="miss", pattern="^(miss|hit|bypass)$")
    stale_after: datetime | None = None


class ToolError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str = Field(min_length=1, max_length=500)
    retryable: bool = False


class ToolResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    request_id: str = Field(min_length=1, max_length=128)
    environment: Environment
    generated_at: datetime = Field(default_factory=utc_now)
    data: Any = None
    sources: list[SourceReference] = Field(default_factory=list)
    pagination: Pagination | None = None
    access_scope: AccessScope = Field(default_factory=AccessScope)
    freshness: Freshness | None = None
    warnings: list[WarningItem] = Field(default_factory=list)
    partial: bool = False
    error: ToolError | None = None

    def as_transport_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

