"""
Schemas for the Owner dashboard.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DashboardKpis(BaseModel):
    total_budget: float = 0.0
    actual_cost: float = 0.0
    pending_approval_count: int = 0
    pending_approval_amount: float = 0.0
    overdue_amount: float = 0.0
    total_profit_margin: str = "0.0%"
    active_project_count: int = 0
    cash_position: float = 0.0


class DashboardCashflowPoint(BaseModel):
    month: str
    income: float = 0.0
    expense: float = 0.0
    net: float = 0.0
    actual_income: float = 0.0
    actual_expense: float = 0.0
    committed_income: float = 0.0
    committed_expense: float = 0.0
    planned_income: float = 0.0


class DashboardZoneStatusItem(BaseModel):
    key: str
    label: str
    count: int = 0
    amount: float = 0.0
    tone: str = "neutral"


class DashboardRiskyProject(BaseModel):
    project_id: str
    project_name: str
    overdue_amount: float = 0.0
    overdue_count: int = 0
    pending_request_amount: float = 0.0
    pending_request_count: int = 0
    total_risk_amount: float = 0.0


class DashboardProjectHealthItem(BaseModel):
    project_id: str
    project_name: str
    status: str
    total_budget: float = 0.0
    actual_cost: float = 0.0
    pending_amount: float = 0.0
    overdue_amount: float = 0.0
    burn_percent: float = 0.0
    tone: str = "neutral"


class DashboardAttentionItem(BaseModel):
    key: str
    title: str
    description: str
    tone: str = "neutral"
    amount: float | None = None
    count: int | None = None
    path: str | None = None


class DashboardRecentAction(BaseModel):
    time: str
    action: str
    tone: str = "neutral"
    source_type: str = "system"


class DashboardSummaryResponse(BaseModel):
    kpis: DashboardKpis = Field(default_factory=DashboardKpis)
    monthly_cashflow: list[DashboardCashflowPoint] = Field(default_factory=list)
    zone_status: list[DashboardZoneStatusItem] = Field(default_factory=list)
    risky_projects: list[DashboardRiskyProject] = Field(default_factory=list)
    project_health: list[DashboardProjectHealthItem] = Field(default_factory=list)
    attention_items: list[DashboardAttentionItem] = Field(default_factory=list)
    recent_actions: list[DashboardRecentAction] = Field(default_factory=list)
