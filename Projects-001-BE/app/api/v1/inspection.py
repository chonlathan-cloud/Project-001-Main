"""
Project-level inspection API.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import AuthenticatedUser, INSPECTION_STAFF_ROLES, get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.boq import Project
from app.schemas.inspection_schema import (
    InspectionCommentCreate,
    InspectionDefectCreate,
    InspectionDefectItem,
    InspectionDefectUpdate,
    InspectionEventItem,
    InspectionFileAccessResponse,
    InspectionFileItem,
    InspectionProjectCategoriesResponse,
    InspectionProjectCategoriesUpdate,
    InspectionReportLogCreate,
    InspectionReportLogItem,
    InspectionRoundCreate,
    InspectionRoundItem,
    InspectionRoundUpdate,
    InspectionStatusUpdate,
    InspectionSummaryResponse,
    InspectionZoneCreate,
    InspectionZoneItem,
    InspectionZoneUpdate,
)
from app.schemas.responses import StandardResponse
from app.services.gcs_storage_service import (
    delete_storage_key,
    generate_signed_url_for_storage_key,
    upload_inspection_file_to_storage,
)
from app.services.identity_service import get_subcontractor
from app.services import inspection_service

router = APIRouter(prefix="/inspection", tags=["Inspection"])


def _project_key(project_id: UUID | str) -> str:
    return str(project_id)


def _actor_id(user: AuthenticatedUser) -> str:
    return user.email or user.subcontractor_id or user.subject


def _actor_role(user: AuthenticatedUser) -> str:
    return user.role or ",".join(user.roles) or "unknown"


def _is_staff(user: AuthenticatedUser) -> bool:
    return user.has_any_role(INSPECTION_STAFF_ROLES)


def _is_subcontractor(user: AuthenticatedUser) -> bool:
    return user.has_role("subcontractor")


def _require_staff(user: AuthenticatedUser) -> None:
    if not _is_staff(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inspection staff access is required.",
        )


def _require_subcontractor_id(user: AuthenticatedUser) -> str:
    if not user.subcontractor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subcontractor session does not include subcontractor_id.",
        )
    return user.subcontractor_id


def _ensure_inspection_user(user: AuthenticatedUser) -> None:
    if _is_staff(user) or _is_subcontractor(user):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Inspection access is required.",
    )


async def _ensure_project_exists(db: AsyncSession, project_id: UUID) -> None:
    exists = (await db.execute(select(Project.id).where(Project.id == project_id))).scalar_one_or_none()
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found.",
        )


def _with_subcontractor_filter(user: AuthenticatedUser, filters: dict) -> dict:
    if _is_subcontractor(user):
        filters = dict(filters)
        filters["assigned_subcontractor_id"] = _require_subcontractor_id(user)
    return filters


def _assert_can_access_defect(user: AuthenticatedUser, defect: dict) -> None:
    if _is_staff(user):
        return
    if _is_subcontractor(user):
        inspection_service.assert_subcontractor_can_access_defect(
            defect,
            _require_subcontractor_id(user),
        )
        return
    _ensure_inspection_user(user)


def _resolve_subcontractor_name(subcontractor_id: str | None, explicit_name: str | None) -> str | None:
    if not subcontractor_id:
        return explicit_name
    profile = get_subcontractor(subcontractor_id)
    return explicit_name or profile.name


def _validate_upload(
    *,
    kind: str,
    file_bytes: bytes,
    content_type: str,
) -> None:
    settings = get_settings()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded inspection file is empty.",
        )

    if kind in {"PLAN_IMAGE", "BEFORE_PHOTO", "AFTER_PHOTO"} and not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inspection plans and photos must be image files.",
        )
    if kind == "REPORT_PDF" and content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report uploads must be PDF files.",
        )

    max_bytes = (
        settings.inspection_plan_max_bytes
        if kind == "PLAN_IMAGE"
        else settings.inspection_photo_max_bytes
        if kind in {"BEFORE_PHOTO", "AFTER_PHOTO"}
        else settings.inspection_plan_max_bytes
    )
    if len(file_bytes) > max_bytes:
        size_mb = max_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Inspection file exceeds the {size_mb:.0f}MB limit.",
        )


@router.get(
    "/projects/{project_id}/categories",
    response_model=StandardResponse[InspectionProjectCategoriesResponse],
)
async def get_inspection_categories(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    return StandardResponse(data=inspection_service.get_project_categories(_project_key(project_id)))


@router.put(
    "/projects/{project_id}/categories",
    response_model=StandardResponse[InspectionProjectCategoriesResponse],
)
async def update_inspection_categories(
    project_id: UUID,
    request: InspectionProjectCategoriesUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _ensure_project_exists(db, project_id)
    return StandardResponse(
        data=inspection_service.update_project_categories(
            project_id=_project_key(project_id),
            categories=request.categories,
            actor_id=_actor_id(user),
        )
    )


@router.get(
    "/projects/{project_id}/rounds",
    response_model=StandardResponse[list[InspectionRoundItem]],
)
async def list_inspection_rounds(
    project_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    subcontractor_id = _require_subcontractor_id(user) if _is_subcontractor(user) else None
    return StandardResponse(
        data=inspection_service.list_rounds(
            project_id=_project_key(project_id),
            subcontractor_id=subcontractor_id,
        )
    )


@router.post(
    "/projects/{project_id}/rounds",
    response_model=StandardResponse[InspectionRoundItem],
)
async def create_inspection_round(
    project_id: UUID,
    request: InspectionRoundCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _ensure_project_exists(db, project_id)
    return StandardResponse(
        data=inspection_service.create_round(
            project_id=_project_key(project_id),
            payload=request.model_dump(),
            actor_id=_actor_id(user),
        )
    )


@router.get(
    "/projects/{project_id}/rounds/{round_id}",
    response_model=StandardResponse[InspectionRoundItem],
)
async def get_inspection_round(
    project_id: UUID,
    round_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    round_item = inspection_service.get_round(_project_key(project_id), round_id)
    if _is_subcontractor(user):
        visible_rounds = inspection_service.list_rounds(
            project_id=_project_key(project_id),
            subcontractor_id=_require_subcontractor_id(user),
        )
        if round_id not in {item["id"] for item in visible_rounds}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This round has no assigned defects.")
    return StandardResponse(data=round_item)


@router.patch(
    "/projects/{project_id}/rounds/{round_id}",
    response_model=StandardResponse[InspectionRoundItem],
)
async def update_inspection_round(
    project_id: UUID,
    round_id: str,
    request: InspectionRoundUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _ensure_project_exists(db, project_id)
    return StandardResponse(
        data=inspection_service.update_round(
            project_id=_project_key(project_id),
            round_id=round_id,
            payload=request.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/projects/{project_id}/rounds/{round_id}/zones",
    response_model=StandardResponse[list[InspectionZoneItem]],
)
async def list_inspection_zones(
    project_id: UUID,
    round_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    subcontractor_id = _require_subcontractor_id(user) if _is_subcontractor(user) else None
    return StandardResponse(
        data=inspection_service.list_zones(
            project_id=_project_key(project_id),
            round_id=round_id,
            subcontractor_id=subcontractor_id,
        )
    )


@router.post(
    "/projects/{project_id}/rounds/{round_id}/zones",
    response_model=StandardResponse[InspectionZoneItem],
)
async def create_inspection_zone(
    project_id: UUID,
    round_id: str,
    request: InspectionZoneCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _ensure_project_exists(db, project_id)
    return StandardResponse(
        data=inspection_service.create_zone(
            project_id=_project_key(project_id),
            round_id=round_id,
            payload=request.model_dump(),
            actor_id=_actor_id(user),
        )
    )


@router.patch(
    "/projects/{project_id}/rounds/{round_id}/zones/{zone_id}",
    response_model=StandardResponse[InspectionZoneItem],
)
async def update_inspection_zone(
    project_id: UUID,
    round_id: str,
    zone_id: str,
    request: InspectionZoneUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _ensure_project_exists(db, project_id)
    return StandardResponse(
        data=inspection_service.update_zone(
            project_id=_project_key(project_id),
            round_id=round_id,
            zone_id=zone_id,
            payload=request.model_dump(exclude_unset=True),
        )
    )


@router.get(
    "/projects/{project_id}/rounds/{round_id}/defects",
    response_model=StandardResponse[list[InspectionDefectItem]],
)
async def list_inspection_defects(
    project_id: UUID,
    round_id: str,
    zone_id: str | None = None,
    status_filter: list[str] | None = Query(default=None, alias="status"),
    severity: list[str] | None = Query(default=None),
    category: str | None = None,
    assigned_subcontractor_id: str | None = None,
    search: str | None = None,
    due_before: str | None = None,
    overdue: bool = False,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    filters = _with_subcontractor_filter(
        user,
        {
            "zone_id": zone_id,
            "status": status_filter,
            "severity": severity,
            "category": category,
            "assigned_subcontractor_id": assigned_subcontractor_id,
            "search": search,
            "due_before": due_before,
            "overdue": overdue,
        },
    )
    return StandardResponse(
        data=inspection_service.list_defects(
            project_id=_project_key(project_id),
            round_id=round_id,
            filters=filters,
        )
    )


@router.post(
    "/projects/{project_id}/rounds/{round_id}/defects",
    response_model=StandardResponse[InspectionDefectItem],
)
async def create_inspection_defect(
    project_id: UUID,
    round_id: str,
    request: InspectionDefectCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _ensure_project_exists(db, project_id)
    payload = request.model_dump()
    payload["assigned_subcontractor_name"] = _resolve_subcontractor_name(
        payload.get("assigned_subcontractor_id"),
        payload.get("assigned_subcontractor_name"),
    )
    return StandardResponse(
        data=inspection_service.create_defect(
            project_id=_project_key(project_id),
            round_id=round_id,
            payload=payload,
            actor_id=_actor_id(user),
            actor_role=_actor_role(user),
        )
    )


@router.get(
    "/projects/{project_id}/rounds/{round_id}/defects/{defect_id}",
    response_model=StandardResponse[InspectionDefectItem],
)
async def get_inspection_defect(
    project_id: UUID,
    round_id: str,
    defect_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    defect = inspection_service.get_defect(_project_key(project_id), round_id, defect_id)
    _assert_can_access_defect(user, defect)
    return StandardResponse(data=defect)


@router.patch(
    "/projects/{project_id}/rounds/{round_id}/defects/{defect_id}",
    response_model=StandardResponse[InspectionDefectItem],
)
async def update_inspection_defect(
    project_id: UUID,
    round_id: str,
    defect_id: str,
    request: InspectionDefectUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _ensure_project_exists(db, project_id)
    payload = request.model_dump(exclude_unset=True)
    if "assigned_subcontractor_id" in payload:
        payload["assigned_subcontractor_name"] = _resolve_subcontractor_name(
            payload.get("assigned_subcontractor_id"),
            payload.get("assigned_subcontractor_name"),
        )
    return StandardResponse(
        data=inspection_service.update_defect(
            project_id=_project_key(project_id),
            round_id=round_id,
            defect_id=defect_id,
            payload=payload,
            actor_id=_actor_id(user),
            actor_role=_actor_role(user),
        )
    )


@router.post(
    "/projects/{project_id}/rounds/{round_id}/defects/{defect_id}/status",
    response_model=StandardResponse[InspectionDefectItem],
)
async def update_inspection_defect_status(
    project_id: UUID,
    round_id: str,
    defect_id: str,
    request: InspectionStatusUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    defect = inspection_service.get_defect(_project_key(project_id), round_id, defect_id)
    if _is_subcontractor(user):
        _assert_can_access_defect(user, defect)
        if request.status != "READY_FOR_REVIEW":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subcontractors can only mark assigned defects as Ready for Review.",
            )
    else:
        _require_staff(user)
    return StandardResponse(
        data=inspection_service.update_defect_status(
            project_id=_project_key(project_id),
            round_id=round_id,
            defect_id=defect_id,
            to_status=request.status,
            comment=request.comment,
            actor_id=_actor_id(user),
            actor_role=_actor_role(user),
        )
    )


@router.post(
    "/projects/{project_id}/rounds/{round_id}/defects/{defect_id}/comments",
    response_model=StandardResponse[InspectionEventItem],
)
async def add_inspection_comment(
    project_id: UUID,
    round_id: str,
    defect_id: str,
    request: InspectionCommentCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    defect = inspection_service.get_defect(_project_key(project_id), round_id, defect_id)
    _assert_can_access_defect(user, defect)
    return StandardResponse(
        data=inspection_service.create_comment_event(
            project_id=_project_key(project_id),
            round_id=round_id,
            defect_id=defect_id,
            comment=request.comment,
            actor_id=_actor_id(user),
            actor_role=_actor_role(user),
        )
    )


@router.get(
    "/projects/{project_id}/rounds/{round_id}/events",
    response_model=StandardResponse[list[InspectionEventItem]],
)
async def list_inspection_events(
    project_id: UUID,
    round_id: str,
    defect_id: str | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    if defect_id:
        defect = inspection_service.get_defect(_project_key(project_id), round_id, defect_id)
        _assert_can_access_defect(user, defect)
    elif _is_subcontractor(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subcontractors can view events only for assigned defects.",
        )
    return StandardResponse(
        data=inspection_service.list_events(
            project_id=_project_key(project_id),
            round_id=round_id,
            defect_id=defect_id,
        )
    )


@router.post(
    "/projects/{project_id}/rounds/{round_id}/files",
    response_model=StandardResponse[InspectionFileItem],
)
async def upload_inspection_file(
    project_id: UUID,
    round_id: str,
    kind: str = Form(...),
    zone_id: str | None = Form(default=None),
    defect_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    kind_value = kind.strip().upper().replace(" ", "_").replace("-", "_")

    if kind_value == "PLAN_IMAGE":
        _require_staff(user)
        if not zone_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="zone_id is required for plan images.")
    elif kind_value == "BEFORE_PHOTO":
        _require_staff(user)
        if not defect_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="defect_id is required for before photos.")
    elif kind_value == "AFTER_PHOTO":
        if not defect_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="defect_id is required for after photos.")
        defect = inspection_service.get_defect(_project_key(project_id), round_id, defect_id)
        _assert_can_access_defect(user, defect)
    else:
        _require_staff(user)

    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"
    _validate_upload(kind=kind_value, file_bytes=file_bytes, content_type=content_type)

    file_id = inspection_service.new_file_id()
    gcs_path = await upload_inspection_file_to_storage(
        project_id=_project_key(project_id),
        round_id=round_id,
        file_id=file_id,
        kind=kind_value,
        file_bytes=file_bytes,
        file_name=file.filename,
        content_type=content_type,
        zone_id=zone_id,
        defect_id=defect_id,
    )
    return StandardResponse(
        data=inspection_service.create_file_record(
            file_id=file_id,
            project_id=_project_key(project_id),
            round_id=round_id,
            kind=kind_value,
            gcs_path=gcs_path,
            content_type=content_type,
            size_bytes=len(file_bytes),
            original_filename=file.filename,
            uploaded_by=_actor_id(user),
            actor_role=_actor_role(user),
            zone_id=zone_id,
            defect_id=defect_id,
        )
    )


@router.get(
    "/files/{file_id}/signed-url",
    response_model=StandardResponse[InspectionFileAccessResponse],
)
async def get_inspection_file_signed_url(
    file_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _ensure_inspection_user(user)
    file_payload = inspection_service.get_file(file_id)
    if not _is_staff(user):
        defect_id = file_payload.get("defect_id")
        if defect_id:
            defect = inspection_service.get_defect(
                file_payload["project_id"],
                file_payload["round_id"],
                defect_id,
            )
            _assert_can_access_defect(user, defect)
        else:
            visible_defects = inspection_service.list_defects(
                project_id=file_payload["project_id"],
                round_id=file_payload["round_id"],
                filters={
                    "zone_id": file_payload.get("zone_id"),
                    "assigned_subcontractor_id": _require_subcontractor_id(user),
                },
            )
            if not visible_defects:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This inspection file is not visible to the current subcontractor.",
                )

    expires_in_minutes = get_settings().signed_url_expires_minutes
    signed_url = await generate_signed_url_for_storage_key(
        storage_key=file_payload["gcs_path"],
        expires_in_minutes=expires_in_minutes,
    )
    return StandardResponse(
        data=InspectionFileAccessResponse(
            file_id=file_id,
            signed_url=signed_url,
            expires_in_minutes=expires_in_minutes,
            content_type=file_payload.get("content_type"),
            original_filename=file_payload.get("original_filename"),
        )
    )


@router.delete("/files/{file_id}", response_model=StandardResponse[dict])
async def delete_inspection_file(
    file_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _ensure_inspection_user(user)
    file_payload = inspection_service.get_file(file_id)
    if not _is_staff(user):
        if file_payload.get("kind") != "AFTER_PHOTO" or not file_payload.get("defect_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inspection staff access is required.")
        defect = inspection_service.get_defect(
            file_payload["project_id"],
            file_payload["round_id"],
            file_payload["defect_id"],
        )
        _assert_can_access_defect(user, defect)

    await delete_storage_key(file_payload["gcs_path"])
    deleted = inspection_service.delete_file_record(file_id)
    return StandardResponse(data={"id": file_id, "deleted": True, "gcs_path": deleted.get("gcs_path")})


@router.get(
    "/projects/{project_id}/rounds/{round_id}/summary",
    response_model=StandardResponse[InspectionSummaryResponse],
)
async def get_inspection_summary(
    project_id: UUID,
    round_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_inspection_user(user)
    await _ensure_project_exists(db, project_id)
    subcontractor_id = _require_subcontractor_id(user) if _is_subcontractor(user) else None
    return StandardResponse(
        data=inspection_service.get_summary(
            project_id=_project_key(project_id),
            round_id=round_id,
            subcontractor_id=subcontractor_id,
        )
    )


@router.post(
    "/projects/{project_id}/rounds/{round_id}/report-logs",
    response_model=StandardResponse[InspectionReportLogItem],
)
async def create_inspection_report_log(
    project_id: UUID,
    round_id: str,
    request: InspectionReportLogCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _ensure_project_exists(db, project_id)
    return StandardResponse(
        data=inspection_service.create_report_log(
            project_id=_project_key(project_id),
            round_id=round_id,
            report_type=request.report_type,
            filters=request.filters,
            actor_id=_actor_id(user),
            actor_role=_actor_role(user),
        )
    )


@router.get(
    "/projects/{project_id}/rounds/{round_id}/report-logs",
    response_model=StandardResponse[list[InspectionReportLogItem]],
)
async def list_inspection_report_logs(
    project_id: UUID,
    round_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _ensure_project_exists(db, project_id)
    return StandardResponse(data=inspection_service.list_report_logs(_project_key(project_id), round_id))
