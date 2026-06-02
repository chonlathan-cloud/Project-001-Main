"""
Schemas for admin settings support screens.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SettingsIntegrationItem(BaseModel):
    key: str
    label: str
    category: str
    status: str
    status_label: str
    description: str
    display_value: str | None = None
    is_configured: bool = False
    read_only: bool = True
    required_envs: list[str] = Field(default_factory=list)


class SettingsIntegrationGroup(BaseModel):
    key: str
    label: str
    items: list[SettingsIntegrationItem] = Field(default_factory=list)


class SettingsIntegrationsResponse(BaseModel):
    groups: list[SettingsIntegrationGroup] = Field(default_factory=list)
    generated_at: datetime
    read_only: bool = True
