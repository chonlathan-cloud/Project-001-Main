"""
Pydantic V2 Schemas — BOQ Domain.
Matches LLD Section 2 API Contracts (Router 2 & 3) and TDD POST /boq/sync.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Router 2: GET /api/v1/projects  (Project List)
# ---------------------------------------------------------------------------
class ProjectItem(BaseModel):
    """Single project in the list."""
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID = Field(..., alias="id")
    name: str
    project_type: str | None = None
    status: str
    total_budget: float = 0.0
    progress_percent: float = 0.0


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
    overhead_percent: float = 0.0
    profit_percent: float = 0.0
    vat_percent: float = 0.0
    contingency_budget: float = 0.0
    status: str


# ---------------------------------------------------------------------------
# Router 3: GET /api/v1/projects/{id}/boq  (BOQ Tree — recursive)
# ---------------------------------------------------------------------------
class BOQTreeNode(BaseModel):
    """
    Recursive node representing a single BOQ item in the WBS hierarchy.
    `children` allows unlimited nesting (Level 1 → 2 → 3 …).
    """
    model_config = ConfigDict(from_attributes=True)

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

    # Leaf-level pricing
    customer_price: Optional[float] = None
    subcontractor_price: Optional[float] = None
    margin_per_unit: Optional[float] = None

    # Recursive children
    children: list[BOQTreeNode] = Field(default_factory=list)


class BOQTreeResponse(BaseModel):
    """Payload for GET /api/v1/projects/{id}/boq."""
    project_name: str
    boq_tree: list[BOQTreeNode] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# POST /api/v1/boq/sync  (TDD Router 2)
# ---------------------------------------------------------------------------
class SyncBOQRequest(BaseModel):
    """Request body for syncing BOQ from Google Sheets."""
    project_id: UUID
    boq_type: str = Field(..., pattern="^(CUSTOMER|SUBCONTRACTOR)$")
    sheet_url: str
    sheet_name: str = Field(..., min_length=1)


class SyncBOQResponse(BaseModel):
    """Payload returned after BOQ sync is triggered."""
    project_id: UUID
    project_name: str
    boq_type: str
    sheet_url: str
    sheet_name: str
    status: str
    inserted_items: int = 0
    version_closed_items: int = 0
    synced_at: str
    message: str


class SheetTabsRequest(BaseModel):
    """Request body for previewing workbook tabs before sync."""
    sheet_url: str


class SheetTabItem(BaseModel):
    """Single worksheet in a Google Sheets workbook."""
    name: str
    syncable: bool
    default_selected: bool


class SheetTabsResponse(BaseModel):
    """Workbook tab preview payload."""
    sheet_url: str
    tabs: list[SheetTabItem] = Field(default_factory=list)


class SyncBOQBatchRequest(BaseModel):
    """Request body for syncing multiple BOQ tabs in one action."""
    project_id: UUID
    boq_type: str = Field(..., pattern="^(CUSTOMER|SUBCONTRACTOR)$")
    sheet_url: str
    sheet_names: list[str] = Field(default_factory=list)


class SyncBOQBatchItemResponse(BaseModel):
    """Per-tab result from batch BOQ sync."""
    sheet_name: str
    status: str
    inserted_items: int = 0
    version_closed_items: int = 0
    synced_at: str | None = None
    message: str


class SyncBOQBatchResponse(BaseModel):
    """Payload returned after a multi-tab BOQ sync attempt."""
    project_id: UUID
    project_name: str
    boq_type: str
    sheet_url: str
    status: str
    total_requested_tabs: int = 0
    total_completed_tabs: int = 0
    total_failed_tabs: int = 0
    synced_at: str
    results: list[SyncBOQBatchItemResponse] = Field(default_factory=list)


class SyncBOQBatchJobResponse(BaseModel):
    """Queued or in-progress batch sync job status."""
    job_id: str
    project_id: UUID
    project_name: str
    boq_type: str
    sheet_url: str
    status: str
    total_requested_tabs: int = 0
    total_completed_tabs: int = 0
    total_failed_tabs: int = 0
    current_sheet_name: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    message: str
    results: list[SyncBOQBatchItemResponse] = Field(default_factory=list)
