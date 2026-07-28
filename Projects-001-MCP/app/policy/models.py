"""Product authorization context resolved by the Backend."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config.settings import Environment


class AccessContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_version: str = Field(pattern=r"^1\.[0-9]+$")
    subject: str = Field(min_length=1, max_length=255)
    issuer: str = Field(min_length=8, max_length=2048)
    client_id: str = Field(min_length=1, max_length=255)
    user_id: str = Field(min_length=1, max_length=255)
    environment: Environment
    active: bool
    external_mcp_enabled: bool
    role: str = Field(min_length=1, max_length=32)
    permissions: set[str] = Field(default_factory=set, max_length=32)
    all_projects_read: bool = False
    assigned_project_ids: set[str] = Field(default_factory=set, max_length=1000)
    authorization_revision: str = Field(min_length=1, max_length=128)
    resolved_at: datetime

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: object) -> str:
        return str(value or "").strip().lower()

    @field_validator("permissions", "assigned_project_ids", mode="before")
    @classmethod
    def normalize_sets(cls, value: object) -> set[str]:
        if not isinstance(value, list | set | tuple):
            return set()
        return {str(item).strip() for item in value if str(item).strip()}
