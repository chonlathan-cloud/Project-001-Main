"""
Router 2 & 3: Project List, Project Detail, BOQ Tree, BOQ Sync.
"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.database import get_db
from app.models.boq import BOQItem, Project
from app.models.finance import Installment  # noqa: F401
from app.schemas.boq_schema import (
    BOQTreeNode,
    BOQTreeResponse,
    CreateProjectRequest,
    ProjectDetailResponse,
    ProjectItem,
    ProjectListResponse,
    SheetTabsRequest,
    SheetTabsResponse,
    SyncBOQRequest,
    SyncBOQBatchRequest,
    SyncBOQBatchJobResponse,
    SyncBOQBatchResponse,
    SyncBOQResponse,
    UpdateProjectRequest,
)
from app.schemas.responses import StandardResponse
from app.services.boq_sync_job_service import (
    create_boq_sync_job,
    get_boq_sync_job,
    run_boq_sync_job,
    serialize_boq_sync_job,
)
from app.services.boq_sync_service import fetch_google_sheet_tabs, sync_boq_sheet

router = APIRouter(prefix="/projects", tags=["Projects & BOQ"])


def _to_project_list_item(project: Project) -> ProjectItem:
    return ProjectItem(
        id=project.id,
        name=project.name,
        project_type=project.project_type,
        status=project.status,
        total_budget=float(project.contingency_budget or 0),
        progress_percent=0.0,  # TODO: calculate from installments
    )


def _to_project_detail(project: Project) -> ProjectDetailResponse:
    return ProjectDetailResponse(
        project_id=project.id,
        name=project.name,
        project_type=project.project_type,
        overhead_percent=float(project.overhead_percent or 0),
        profit_percent=float(project.profit_percent or 0),
        vat_percent=float(project.vat_percent or 0),
        contingency_budget=float(project.contingency_budget or 0),
        status=project.status,
    )


# ---------------------------------------------------------------------------
# Router 2: GET /api/v1/projects
# ---------------------------------------------------------------------------
@router.get("", response_model=StandardResponse[list[ProjectItem]])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """Return all projects with basic info and progress."""
    try:
        result = await db.execute(select(Project).options(noload("*")))
        projects = result.scalars().all()

        items = [_to_project_list_item(project) for project in projects]
        return StandardResponse(data=items)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 2: POST /api/v1/projects
# ---------------------------------------------------------------------------
@router.post("", response_model=StandardResponse[ProjectDetailResponse])
async def create_project(
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project before connecting BOQ sources."""
    try:
        project = Project(
            name=request.name.strip(),
            project_type=request.project_type.strip(),
            overhead_percent=Decimal(str(request.overhead_percent)),
            profit_percent=Decimal(str(request.profit_percent)),
            vat_percent=Decimal(str(request.vat_percent)),
            contingency_budget=Decimal(str(request.contingency_budget)),
            status=request.status.strip().upper(),
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

        return StandardResponse(data=_to_project_detail(project))

    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 2: PUT /api/v1/projects/{id}
# ---------------------------------------------------------------------------
@router.put("/{project_id}", response_model=StandardResponse[ProjectDetailResponse])
async def update_project(
    project_id: UUID,
    request: UpdateProjectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update project fields such as name or financial settings."""
    try:
        result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=project_id)
        )
        project = result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )

        updates = request.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field is required to update a project.",
            )

        for field, value in updates.items():
            if field in {"overhead_percent", "profit_percent", "vat_percent", "contingency_budget"}:
                setattr(project, field, Decimal(str(value)))
            elif isinstance(value, str):
                cleaned = value.strip()
                setattr(project, field, cleaned.upper() if field == "status" else cleaned)
            else:
                setattr(project, field, value)

        await db.commit()
        await db.refresh(project)

        return StandardResponse(data=_to_project_detail(project))

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 3: GET /api/v1/projects/{id}
# ---------------------------------------------------------------------------
@router.get("/{project_id}", response_model=StandardResponse[ProjectDetailResponse])
async def get_project_detail(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return basic project information."""
    try:
        result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=project_id)
        )
        project = result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )

        return StandardResponse(data=_to_project_detail(project))

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 3: GET /api/v1/projects/{id}/boq  (Tree / Nested)
# ---------------------------------------------------------------------------
def _build_boq_tree(items: list[BOQItem], parent_id=None) -> list[BOQTreeNode]:
    """Recursively build a nested BOQ tree from flat ORM records."""
    nodes = []
    for item in items:
        if item.parent_id == parent_id:
            children = _build_boq_tree(items, parent_id=item.id)
            node = BOQTreeNode(
                wbs_level=item.wbs_level,
                description=item.description,
                item_no=item.item_no,
                qty=float(item.qty) if item.qty else None,
                unit=item.unit,
                total_budget=float(item.grand_total or 0),
                material_budget=float(item.total_material or 0),
                labor_budget=float(item.total_labor or 0),
                material_unit_price=float(item.material_unit_price or 0),
                labor_unit_price=float(item.labor_unit_price or 0),
                children=children,
            )
            nodes.append(node)
    return nodes


@router.get("/{project_id}/boq", response_model=StandardResponse[BOQTreeResponse])
async def get_project_boq(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return BOQ data as a nested WBS tree for the frontend to render."""
    try:
        # Verify project exists
        proj_result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=project_id)
        )
        project = proj_result.scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found.",
            )

        # Fetch all BOQ items for this project (current versions only)
        items_result = await db.execute(
            select(BOQItem)
            .options(noload("*"))
            .filter_by(project_id=project_id)
            .filter(BOQItem.valid_to.is_(None))
            .order_by(BOQItem.wbs_level, BOQItem.item_no)
        )
        all_items = items_result.scalars().all()

        tree = _build_boq_tree(all_items, parent_id=None)

        return StandardResponse(
            data=BOQTreeResponse(project_name=project.name, boq_tree=tree)
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch BOQ: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Router 2: POST /api/v1/boq/sync  (uses AI to parse Google Sheet)
# ---------------------------------------------------------------------------
@router.post("/boq/sync", response_model=StandardResponse[SyncBOQResponse])
async def sync_boq(
    request: SyncBOQRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Sync BOQ from a Google Sheet URL.
    Flow: Fetch one tab → Gemini parses WBS → Save to DB (SCD Type 2).
    """
    try:
        result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=request.project_id)
        )
        project = result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {request.project_id} not found.",
            )

        data = await sync_boq_sheet(
            session=db,
            project=project,
            boq_type=request.boq_type,
            sheet_url=request.sheet_url,
            sheet_name=request.sheet_name,
        )
        return StandardResponse(data=SyncBOQResponse(**data))

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync BOQ: {exc}",
        ) from exc


@router.post("/boq/tabs", response_model=StandardResponse[SheetTabsResponse])
async def preview_boq_tabs(request: SheetTabsRequest):
    """Preview workbook tabs so the frontend can batch select syncable BOQ tabs."""
    try:
        tabs = await fetch_google_sheet_tabs(request.sheet_url)
        return StandardResponse(
            data=SheetTabsResponse(
                sheet_url=request.sheet_url,
                tabs=tabs,
            )
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview Google Sheet tabs: {exc}",
        ) from exc


@router.post("/boq/sync-batch", response_model=StandardResponse[SyncBOQBatchJobResponse])
async def sync_boq_batch(
    request: SyncBOQBatchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Queue a background job that syncs multiple BOQ tabs from the same workbook."""
    try:
        result = await db.execute(
            select(Project).options(noload("*")).filter_by(id=request.project_id)
        )
        project = result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {request.project_id} not found.",
            )

        job = await create_boq_sync_job(
            project_id=project.id,
            project_name=project.name,
            boq_type=request.boq_type,
            sheet_url=request.sheet_url,
            sheet_names=request.sheet_names,
        )
        background_tasks.add_task(run_boq_sync_job, job["job_id"])
        return StandardResponse(data=serialize_boq_sync_job(job))

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync BOQ tabs: {exc}",
        ) from exc


@router.get("/boq/sync-jobs/{job_id}", response_model=StandardResponse[SyncBOQBatchJobResponse])
async def get_sync_boq_batch_job(job_id: str):
    """Return current status and per-tab progress for a queued BOQ batch sync job."""
    try:
        job = await get_boq_sync_job(job_id)
        return StandardResponse(data=serialize_boq_sync_job(job))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch BOQ sync job {job_id}: {exc}",
        ) from exc
