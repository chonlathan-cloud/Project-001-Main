"""
Pydantic V2 Schemas — BOQ Domain.
Matches LLD Section 2 API Contracts (Router 2 & 3) and TDD POST /boq/sync.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project_budget_schema import ProjectBudgetSnapshot


# ---------------------------------------------------------------------------
# Router 2: GET /api/v1/projects  (Project List)
# ---------------------------------------------------------------------------
class ProjectItem(BaseModel):
    """Single project in the list."""
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID = Field(..., alias="id")
    name: str
    project_type: str | None = None
    system_key: str | None = None
    status: str
    total_budget: float = 0.0
    progress_percent: float = 0.0
    spent: float = 0.0
    pending_amount: float = 0.0
    paid_amount: float = 0.0
    budget_snapshot: ProjectBudgetSnapshot | None = None


class ProjectListResponse(BaseModel):
    """Payload for GET /api/v1/projects."""
    projects: list[ProjectItem] = Field(default_factory=list)


class CreateProjectRequest(BaseModel):
    """Request body for creating a new project."""
    name: str = Field(..., min_length=1)
    project_type: str = Field(..., min_length=1)
    overhead_percent: float = 0.0
    profit_percent: float = 0.0
    vat_percent: float = 7.0
    contingency_budget: float = 0.0
    status: str = "ACTIVE"


class UpdateProjectRequest(BaseModel):
    """Request body for updating an existing project."""
    name: str | None = Field(default=None, min_length=1)
    project_type: str | None = Field(default=None, min_length=1)
    overhead_percent: float | None = None
    profit_percent: float | None = None
    vat_percent: float | None = None
    contingency_budget: float | None = None
    status: str | None = None


class ProjectDetailResponse(BaseModel):
    """Payload for GET/POST/PUT project detail responses."""
    project_id: UUID
    name: str
    project_type: str
    system_key: str | None = None
    overhead_percent: float = 0.0
    profit_percent: float = 0.0
    vat_percent: float = 0.0
    contingency_budget: float = 0.0
    status: str
    total_budget: float = 0.0
    budget_snapshot: ProjectBudgetSnapshot | None = None


# ---------------------------------------------------------------------------
# Router 3: GET /api/v1/projects/{id}/boq  (BOQ Tree — recursive)
# ---------------------------------------------------------------------------
class BOQTreeNode(BaseModel):
    """
    Recursive node representing a single BOQ item in the WBS hierarchy.
    `children` allows unlimited nesting (Level 1 → 2 → 3 …).
    """
    model_config = ConfigDict(from_attributes=True)

    sheet_name: Optional[str] = None
    boq_type: Optional[str] = None
    wbs_level: int
    description: Optional[str] = None
    item_no: Optional[str] = None
    qty: Optional[float] = None
    unit: Optional[str] = None

    # Budget breakdown
    total_budget: Optional[float] = None
    actual_spent: Optional[float] = None
    variance: Optional[str] = None
    material_budget: Optional[float] = None
    labor_budget: Optional[float] = None
    own_total_budget: Optional[float] = None
    own_material_budget: Optional[float] = None
    own_labor_budget: Optional[float] = None
    rollup_total_budget: Optional[float] = None
    rollup_material_budget: Optional[float] = None
    rollup_labor_budget: Optional[float] = None
    display_total_budget: Optional[float] = None
    display_material_budget: Optional[float] = None
    display_labor_budget: Optional[float] = None

    # Leaf-level pricing
    customer_price: Optional[float] = None
    subcontractor_price: Optional[float] = None
    margin_per_unit: Optional[float] = None

    # Recursive children
    children: list[BOQTreeNode] = Field(default_factory=list)


class BOQCompareNode(BaseModel):
    """Merged BOQ node used by the Project Detail compare view."""
    key: str
    sheet_name: Optional[str] = None
    wbs_level: int
    description: Optional[str] = None
    item_no: Optional[str] = None
    unit: Optional[str] = None
    customer_qty: Optional[float] = None
    subcontractor_qty: Optional[float] = None
    customer_total_budget: float = 0.0
    subcontractor_total_budget: float = 0.0
    customer_material_budget: float = 0.0
    subcontractor_material_budget: float = 0.0
    customer_labor_budget: float = 0.0
    subcontractor_labor_budget: float = 0.0
    variance: float = 0.0
    margin_percent: Optional[float] = None
    match_status: str = "MATCHED"
    children: list[BOQCompareNode] = Field(default_factory=list)


class BOQCompareSummary(BaseModel):
    """Top-level summary for the Customer vs Subcontractor BOQ comparison."""
    customer_total_budget: float = 0.0
    subcontractor_total_budget: float = 0.0
    total_variance: float = 0.0
    margin_percent: Optional[float] = None
    matched_count: int = 0
    customer_only_count: int = 0
    subcontractor_only_count: int = 0
    sheet_names: list[str] = Field(default_factory=list)


class BOQWbsSummaryItem(BaseModel):
    """Top-level WBS summary used for Project Detail charts."""
    key: str
    label: str
    sheet_name: Optional[str] = None
    customer_total_budget: float = 0.0
    subcontractor_total_budget: float = 0.0
    variance: float = 0.0
    margin_percent: Optional[float] = None
    customer_material_budget: float = 0.0
    subcontractor_material_budget: float = 0.0
    customer_labor_budget: float = 0.0
    subcontractor_labor_budget: float = 0.0
    match_status: str = "MATCHED"


class ProjectExecutionSummaryItem(BaseModel):
    """Execution-level financial state for Project Detail charts/cards."""
    key: str
    label: str
    amount: float = 0.0
    count: int = 0
    tone: str = "neutral"


class BOQTreeResponse(BaseModel):
    """Payload for GET /api/v1/projects/{id}/boq."""
    project_name: str
    boq_tree: list[BOQTreeNode] = Field(default_factory=list)
    customer_tree: list[BOQTreeNode] = Field(default_factory=list)
    subcontractor_tree: list[BOQTreeNode] = Field(default_factory=list)
    compare_tree: list[BOQCompareNode] = Field(default_factory=list)
    compare_summary: BOQCompareSummary = Field(default_factory=BOQCompareSummary)
    wbs_summary: list[BOQWbsSummaryItem] = Field(default_factory=list)
    execution_summary: list[ProjectExecutionSummaryItem] = Field(default_factory=list)
    active_budget_snapshot: ProjectBudgetSnapshot | None = None
    legacy_history_only: bool = False
