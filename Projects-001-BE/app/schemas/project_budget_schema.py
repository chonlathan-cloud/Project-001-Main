"""Internal project-budget read model shared by BOQ consumers."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


MoneyValue = Annotated[str, Field(pattern=r"^-?(0|[1-9][0-9]*)\.[0-9]{2}$")]
MoneyString = MoneyValue | None


class CostCompleteness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["COMPLETE", "INCOMPLETE", "LEGACY_UNVERIFIED", "NOT_APPLICABLE"]
    required_count: int = Field(ge=0)
    priced_count: int = Field(ge=0)
    missing_component_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> "CostCompleteness":
        if self.priced_count > self.required_count:
            raise ValueError("priced_count cannot exceed required_count")
        if self.state == "COMPLETE" and self.priced_count != self.required_count:
            raise ValueError("complete cost requires all required components priced")
        if self.state == "COMPLETE" and self.missing_component_ids:
            raise ValueError("complete cost cannot include missing components")
        return self


class ProjectBudgetSnapshot(BaseModel):
    """Canonical internal budget source; not a Phase 1 public API response."""

    model_config = ConfigDict(extra="forbid")

    source_kind: Literal["LEGACY", "V2"]
    status: Literal["READY", "NO_BUDGET_DATA", "NO_ACTIVE_BASELINE", "UNKNOWN_COST"]
    project_id: UUID
    currency: Literal["THB"] = "THB"
    baseline_id: UUID | None = None
    baseline_version: int | None = Field(default=None, ge=1)
    main_revision_id: UUID | None = None
    accepted_change_order_ids: list[UUID] = Field(default_factory=list)
    cost_plan_version: int | None = Field(default=None, ge=1)
    calculation_version: str
    activated_at: datetime | None = None
    net_sell_ex_vat: MoneyString = None
    original_estimated_cost: MoneyString = None
    agreed_cost: MoneyString = None
    forecast_cost: MoneyString = None
    forecast_margin: MoneyString = None
    cost_completeness: CostCompleteness
    forecast_basis: Literal[
        "LEGACY_SYNC", "ESTIMATED", "PARTLY_AGREED", "AGREED", "NONE"
    ]
    as_of: datetime

    @model_validator(mode="after")
    def validate_source_identity(self) -> "ProjectBudgetSnapshot":
        if self.source_kind == "LEGACY" and any(
            value is not None
            for value in (
                self.baseline_id,
                self.baseline_version,
                self.main_revision_id,
                self.cost_plan_version,
                self.activated_at,
            )
        ):
            raise ValueError("legacy snapshots cannot claim V2 baseline identity")
        if self.source_kind == "LEGACY":
            if self.status not in {"READY", "NO_BUDGET_DATA"}:
                raise ValueError("legacy snapshots use only legacy readiness states")
            expected_state = (
                "LEGACY_UNVERIFIED" if self.status == "READY" else "NOT_APPLICABLE"
            )
            if self.cost_completeness.state != expected_state:
                raise ValueError("legacy cost completeness must remain unverified")
            if self.forecast_cost is not None or self.forecast_margin is not None:
                raise ValueError("legacy snapshots do not claim verified forecast cost")
        if self.source_kind == "V2" and self.status == "NO_BUDGET_DATA":
            raise ValueError("NO_BUDGET_DATA applies only to the legacy source")
        if self.status == "UNKNOWN_COST" and self.forecast_margin is not None:
            raise ValueError("unknown cost cannot expose a full forecast margin")
        if self.status == "NO_ACTIVE_BASELINE" and self.source_kind != "V2":
            raise ValueError("NO_ACTIVE_BASELINE applies only to V2 source selection")
        if self.source_kind == "V2" and self.status in {"READY", "UNKNOWN_COST"}:
            if any(
                value is None
                for value in (
                    self.baseline_id,
                    self.baseline_version,
                    self.main_revision_id,
                    self.activated_at,
                    self.net_sell_ex_vat,
                )
            ):
                raise ValueError(
                    "active V2 snapshots require complete baseline identity"
                )
        if self.source_kind == "V2" and self.status == "READY":
            if self.cost_completeness.state != "COMPLETE":
                raise ValueError("ready V2 snapshots require complete cost")
            if self.forecast_cost is None or self.forecast_margin is None:
                raise ValueError("ready V2 snapshots require forecast cost and margin")
        if self.status == "UNKNOWN_COST":
            if self.cost_completeness.state != "INCOMPLETE":
                raise ValueError("unknown V2 cost requires incomplete cost state")
            if self.forecast_cost is not None:
                raise ValueError("unknown cost cannot expose a full forecast cost")
        return self


class ProjectBudgetReadContext(BaseModel):
    """Internal snapshot plus exact legacy compatibility projections."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    snapshot: ProjectBudgetSnapshot
    legacy_project_list_budget: str
    legacy_dashboard_budget: str
    legacy_fund_forecast_base: str
    legacy_chat_budget: str
    legacy_mcp_customer_budget: str
