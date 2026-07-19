"""
Daily Report API for subcontractors, Admin/Owner reviewers, and customers.
"""

from __future__ import annotations

import asyncio
import hmac
import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import (
    AuthenticatedUser,
    get_current_user,
    require_customer_user,
    require_owner_user,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.models.boq import Project
from app.schemas.daily_report_schema import (
    DailyReportAcknowledgementCreate,
    DailyReportChangeRequest,
    DailyReportCustomerActionItem,
    DailyReportDraftUpdate,
    DailyReportItem,
    DailyReportLineDestinationItem,
    DailyReportLineDestinationUpdate,
    DailyReportMediaAccessResponse,
    DailyReportMediaItem,
    DailyReportMembershipUpsert,
    DailyReportProjectItem,
    DailyReportProjectSettingsItem,
    DailyReportProjectSettingsUpdate,
    DailyReportPublishRequest,
    DailyReportQuestionCreate,
    DailyReportSubmissionCreate,
    DailyReportSubmissionItem,
    DailyReportSubmissionUpdate,
    DailyReportVersionItem,
)
from app.schemas.responses import StandardResponse
from app.services import daily_report_service
from app.services.daily_report_line_service import (
    deliver_published_report,
    handle_customer_webhook,
    notify_subcontractor_submission,
    verify_customer_webhook_signature,
)
from app.services.daily_report_notification_service import run_deadline_tick
from app.services.gcs_storage_service import (
    delete_storage_key,
    generate_signed_url_for_storage_key,
    upload_daily_report_media_to_storage,
)
from app.services.identity_service import get_subcontractor, list_subcontractors

router = APIRouter(prefix="/daily-reports", tags=["Daily Reports"])
DAILY_REPORT_STAFF_ROLES = {"admin", "owner"}


def _actor_id(user: AuthenticatedUser) -> str:
    return user.email or user.subcontractor_id or user.customer_id or user.subject


def _require_staff(user: AuthenticatedUser) -> None:
    if not user.has_any_role(DAILY_REPORT_STAFF_ROLES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Daily Report Admin or Owner access is required.",
        )


def _require_subcontractor(user: AuthenticatedUser) -> str:
    if not user.has_role("subcontractor") or not user.subcontractor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subcontractor access is required.",
        )
    return user.subcontractor_id


def _admin_project_ids(user: AuthenticatedUser) -> set[str] | None:
    if user.has_role("owner"):
        return None
    _require_staff(user)
    principal_id = user.email or user.subject
    return set(
        daily_report_service.list_membership_project_ids(
            principal_type="admin",
            principal_id=principal_id,
        )
    )


def _assert_staff_project_access(user: AuthenticatedUser, project_id: str) -> None:
    project_ids = _admin_project_ids(user)
    if project_ids is not None and project_id not in project_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Admin is not assigned to the project.",
        )


def _assert_customer_project_access(user: AuthenticatedUser, project_id: str) -> None:
    if not user.customer_id or not daily_report_service.has_project_membership(
        project_id=project_id,
        principal_type="customer",
        principal_id=user.customer_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This customer is not assigned to the project.",
        )


async def _project(db: AsyncSession, project_id: str) -> Project:
    try:
        parsed_id = UUID(project_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id must be a UUID.",
        ) from exc
    item = (await db.execute(select(Project).where(Project.id == parsed_id))).scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found.",
        )
    return item


async def _visible_projects(
    db: AsyncSession,
    *,
    project_ids: set[str] | None,
    active_only: bool = True,
) -> list[DailyReportProjectItem]:
    projects = list((await db.execute(select(Project))).scalars().all())
    items = [
        DailyReportProjectItem(id=str(project.id), name=project.name, status=project.status)
        for project in projects
        if (project_ids is None or str(project.id) in project_ids)
        and (not active_only or str(project.status or "").upper() not in {"COMPLETED", "ARCHIVED"})
    ]
    return sorted(items, key=lambda item: item.name.lower())


@router.post("/internal/deadline-tick", response_model=StandardResponse[dict])
async def daily_report_deadline_tick(
    x_daily_report_task_secret: str | None = Header(
        default=None,
        alias="X-Daily-Report-Task-Secret",
    ),
    db: AsyncSession = Depends(get_db),
):
    expected_secret = get_settings().daily_report_internal_task_secret
    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Daily Report internal task authentication is not configured.",
        )
    if not x_daily_report_task_secret or not hmac.compare_digest(
        x_daily_report_task_secret,
        expected_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Daily Report task authentication.",
        )

    projects = list((await db.execute(select(Project))).scalars().all())
    active_projects = [
        {"id": str(project.id), "name": project.name}
        for project in projects
        if str(project.status or "").upper() not in {"COMPLETED", "ARCHIVED"}
    ]
    project_subcontractors: dict[str, list[str]] = {}
    for subcontractor in list_subcontractors():
        if not subcontractor.is_active:
            continue
        for project_id in subcontractor.assigned_project_ids:
            project_subcontractors.setdefault(project_id, []).append(subcontractor.id)
    return StandardResponse(
        data=await run_deadline_tick(
            projects=active_projects,
            fallback_project_subcontractors=project_subcontractors,
        )
    )


@router.post("/line/customer/webhook", response_model=StandardResponse[dict])
async def customer_line_webhook(
    request: Request,
    x_line_signature: str | None = Header(default=None, alias="X-Line-Signature"),
):
    body = await request.body()
    if not verify_customer_webhook_signature(
        body=body,
        signature=x_line_signature or "",
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid LINE webhook signature.",
        )
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid LINE webhook payload.",
        ) from exc
    return StandardResponse(data=await handle_customer_webhook(payload))


@router.get("/line/destination-candidates", response_model=StandardResponse[list[dict]])
async def list_daily_report_line_destination_candidates(
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    return StandardResponse(data=daily_report_service.list_line_destination_candidates())


@router.get("/me/projects", response_model=StandardResponse[list[DailyReportProjectItem]])
async def list_my_daily_report_projects(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.has_role("subcontractor"):
        profile = get_subcontractor(_require_subcontractor(user))
        project_ids: set[str] | None = set(profile.assigned_project_ids)
    elif user.has_role("customer"):
        if not user.customer_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer identity is missing.")
        project_ids = set(
            daily_report_service.list_membership_project_ids(
                principal_type="customer",
                principal_id=user.customer_id,
            )
        )
    elif user.has_any_role(DAILY_REPORT_STAFF_ROLES):
        project_ids = _admin_project_ids(user)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily Report access is required.")
    return StandardResponse(data=await _visible_projects(db, project_ids=project_ids))


@router.get("/me/submissions", response_model=StandardResponse[list[DailyReportSubmissionItem]])
async def list_my_submissions(user: AuthenticatedUser = Depends(get_current_user)):
    subcontractor_id = _require_subcontractor(user)
    return StandardResponse(
        data=daily_report_service.list_submissions(subcontractor_id=subcontractor_id)
    )


@router.post("/me/submissions", response_model=StandardResponse[DailyReportSubmissionItem])
async def create_my_submission(
    request: DailyReportSubmissionCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subcontractor_id = _require_subcontractor(user)
    profile = get_subcontractor(subcontractor_id)
    if request.project_id not in profile.assigned_project_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This subcontractor is not assigned to the project.",
        )
    project = await _project(db, request.project_id)
    if str(project.status or "").upper() in {"COMPLETED", "ARCHIVED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Daily reports cannot be created for a completed project.",
        )
    project_settings = daily_report_service.get_project_settings(request.project_id)
    if not project_settings.get("enabled", True):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Daily reporting is disabled for this project.",
        )
    return StandardResponse(
        data=daily_report_service.create_submission(
            project_id=request.project_id,
            project_name=project.name,
            report_date=request.report_date,
            subcontractor_id=subcontractor_id,
            subcontractor_name=profile.name,
            actor_id=_actor_id(user),
        )
    )


@router.patch(
    "/me/submissions/{submission_id}",
    response_model=StandardResponse[DailyReportSubmissionItem],
)
async def update_my_submission(
    submission_id: str,
    request: DailyReportSubmissionUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
):
    return StandardResponse(
        data=daily_report_service.update_submission(
            submission_id=submission_id,
            subcontractor_id=_require_subcontractor(user),
            updates=request.model_dump(exclude_unset=True),
            actor_id=_actor_id(user),
        )
    )


@router.post(
    "/me/submissions/{submission_id}/submit",
    response_model=StandardResponse[DailyReportSubmissionItem],
)
async def submit_my_submission(
    submission_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    return StandardResponse(
        data=daily_report_service.submit_submission(
            submission_id=submission_id,
            subcontractor_id=_require_subcontractor(user),
            actor_id=_actor_id(user),
        )
    )


def _validate_media(file_bytes: bytes, content_type: str) -> tuple[str, int]:
    settings = get_settings()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded media is empty.")
    if content_type.startswith("image/"):
        return "PHOTO", settings.daily_report_photo_max_bytes
    if content_type.startswith("video/"):
        return "VIDEO", settings.daily_report_video_max_bytes
    if content_type.startswith("audio/"):
        return "VOICE", settings.daily_report_audio_max_bytes
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Daily Report media must be an image, video, or audio file.",
    )


@router.post(
    "/me/submissions/{submission_id}/media",
    response_model=StandardResponse[DailyReportMediaItem],
)
async def upload_submission_media(
    submission_id: str,
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
):
    subcontractor_id = _require_subcontractor(user)
    submission = daily_report_service.get_submission(submission_id)
    if submission.get("subcontractor_id") != subcontractor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This submission belongs to another subcontractor.")
    content_type = str(file.content_type or "application/octet-stream").lower()
    file_bytes = await file.read()
    media_type, max_bytes = _validate_media(file_bytes, content_type)
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{media_type.title()} exceeds the {max_bytes // (1024 * 1024)}MB limit.",
        )
    media_id = daily_report_service.new_media_id()
    storage_key = await upload_daily_report_media_to_storage(
        project_id=submission["project_id"],
        report_date=submission["report_date"],
        submission_id=submission_id,
        media_id=media_id,
        file_bytes=file_bytes,
        file_name=file.filename,
        content_type=content_type,
    )
    try:
        media = daily_report_service.record_media(
            media_id=media_id,
            submission_id=submission_id,
            project_id=submission["project_id"],
            owner_id=subcontractor_id,
            media_type=media_type,
            file_name=file.filename or media_id,
            content_type=content_type,
            size_bytes=len(file_bytes),
            storage_key=storage_key,
        )
    except Exception:
        await delete_storage_key(storage_key)
        raise
    return StandardResponse(data=media)


@router.delete("/me/media/{media_id}", response_model=StandardResponse[dict])
async def delete_submission_media(
    media_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    media = daily_report_service.delete_media(
        media_id=media_id,
        owner_id=_require_subcontractor(user),
    )
    if media.get("storage_key"):
        await delete_storage_key(media["storage_key"])
    return StandardResponse(data={"id": media_id, "deleted": True})


@router.get("/media/{media_id}/signed-url", response_model=StandardResponse[DailyReportMediaAccessResponse])
async def get_daily_report_media_url(
    media_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    media = daily_report_service.get_media(media_id)
    if user.has_role("subcontractor"):
        if media.get("owner_id") != _require_subcontractor(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This media belongs to another subcontractor.")
    elif user.has_any_role(DAILY_REPORT_STAFF_ROLES):
        _assert_staff_project_access(user, media["project_id"])
    elif user.has_role("customer"):
        _assert_customer_project_access(user, media["project_id"])
        visible = any(
            media.get("submission_id") in (report.get("source_submission_ids") or [])
            for report in daily_report_service.list_reports(
                project_ids={media["project_id"]},
            )
            if int(report.get("published_version") or 0) > 0
        )
        if not visible:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Published report media not found.")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily Report media access is required.")
    settings = get_settings()
    return StandardResponse(
        data=DailyReportMediaAccessResponse(
            media_id=media_id,
            url=await generate_signed_url_for_storage_key(
                storage_key=media["storage_key"],
                expires_in_minutes=settings.signed_url_expires_minutes,
            ),
            expires_in_minutes=settings.signed_url_expires_minutes,
        )
    )


@router.get("/queue", response_model=StandardResponse[list[DailyReportItem]])
async def list_review_queue(
    report_status: str | None = Query(default=None, alias="status"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    statuses = {report_status.upper()} if report_status else None
    return StandardResponse(
        data=daily_report_service.list_reports(
            project_ids=_admin_project_ids(user),
            statuses=statuses,
        )
    )


@router.get("/reports/{report_id}", response_model=StandardResponse[DailyReportItem])
async def get_report_for_review(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    report = daily_report_service.get_report(report_id)
    _assert_staff_project_access(user, report["project_id"])
    return StandardResponse(data=report)


@router.patch("/reports/{report_id}", response_model=StandardResponse[DailyReportItem])
async def update_report_for_review(
    report_id: str,
    request: DailyReportDraftUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    current = daily_report_service.get_report(report_id, include_sources=False)
    _assert_staff_project_access(user, current["project_id"])
    return StandardResponse(
        data=daily_report_service.update_report_draft(
            report_id=report_id,
            updates=request.model_dump(exclude_unset=True),
            actor_id=_actor_id(user),
            actor_role=user.role,
        )
    )


@router.post("/reports/{report_id}/request-changes", response_model=StandardResponse[DailyReportItem])
async def request_report_changes(
    report_id: str,
    request: DailyReportChangeRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    current = daily_report_service.get_report(report_id, include_sources=False)
    _assert_staff_project_access(user, current["project_id"])
    updated = daily_report_service.request_changes(
        report_id=report_id,
        reason=request.reason,
        submission_ids=request.submission_ids,
        actor_id=_actor_id(user),
        actor_role=user.role,
    )
    target_ids = request.submission_ids or list(current.get("source_submission_ids") or [])
    await asyncio.gather(
        *[
            notify_subcontractor_submission(
                submission=daily_report_service.get_submission(submission_id),
                event_type="CHANGES_REQUESTED",
                reason=request.reason,
            )
            for submission_id in target_ids
        ]
    )
    return StandardResponse(data=updated)


@router.post("/reports/{report_id}/publish", response_model=StandardResponse[DailyReportItem])
async def publish_daily_report(
    report_id: str,
    request: DailyReportPublishRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    current = daily_report_service.get_report(report_id, include_sources=False)
    _assert_staff_project_access(user, current["project_id"])
    published = daily_report_service.publish_report(
        report_id=report_id,
        publication_note=request.publication_note,
        actor_id=_actor_id(user),
        actor_role=user.role,
    )
    await deliver_published_report(published)
    await asyncio.gather(
        *[
            notify_subcontractor_submission(
                submission=daily_report_service.get_submission(submission_id),
                event_type="ACCEPTED",
            )
            for submission_id in published.get("source_submission_ids") or []
        ]
    )
    return StandardResponse(data=daily_report_service.get_report(report_id))


@router.post("/reports/{report_id}/correction", response_model=StandardResponse[DailyReportItem])
async def start_report_correction(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    current = daily_report_service.get_report(report_id, include_sources=False)
    _assert_staff_project_access(user, current["project_id"])
    return StandardResponse(
        data=daily_report_service.start_correction(
            report_id=report_id,
            actor_id=_actor_id(user),
            actor_role=user.role,
        )
    )


@router.post("/reports/{report_id}/retry-delivery", response_model=StandardResponse[DailyReportItem])
async def retry_daily_report_delivery(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    report = daily_report_service.get_report(report_id, include_sources=False)
    _assert_staff_project_access(user, report["project_id"])
    if int(report.get("published_version") or 0) < 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a published report can be delivered.",
        )
    await deliver_published_report(daily_report_service.get_customer_report(report_id))
    return StandardResponse(data=daily_report_service.get_report(report_id))


@router.get("/reports/{report_id}/versions", response_model=StandardResponse[list[DailyReportVersionItem]])
async def list_report_versions(
    report_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    report = daily_report_service.get_report(report_id, include_sources=False)
    _assert_staff_project_access(user, report["project_id"])
    return StandardResponse(data=daily_report_service.list_versions(report_id))


@router.get("/projects/{project_id}/settings", response_model=StandardResponse[DailyReportProjectSettingsItem])
async def get_daily_report_project_settings(
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _project(db, project_id)
    _assert_staff_project_access(user, project_id)
    return StandardResponse(data=daily_report_service.get_project_settings(project_id))


@router.put("/projects/{project_id}/settings", response_model=StandardResponse[DailyReportProjectSettingsItem])
async def update_daily_report_project_settings(
    project_id: str,
    request: DailyReportProjectSettingsUpdate,
    user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    await _project(db, project_id)
    return StandardResponse(
        data=daily_report_service.update_project_settings(
            project_id=project_id,
            updates=request.model_dump(exclude_unset=True),
            actor_id=_actor_id(user),
        )
    )


@router.get(
    "/projects/{project_id}/line-destination",
    response_model=StandardResponse[DailyReportLineDestinationItem],
)
async def get_daily_report_line_destination(
    project_id: str,
    user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    await _project(db, project_id)
    return StandardResponse(data=daily_report_service.get_line_destination_config(project_id))


@router.put(
    "/projects/{project_id}/line-destination",
    response_model=StandardResponse[DailyReportLineDestinationItem],
)
async def update_daily_report_line_destination(
    project_id: str,
    request: DailyReportLineDestinationUpdate,
    user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    await _project(db, project_id)
    return StandardResponse(
        data=daily_report_service.update_line_destination(
            project_id=project_id,
            line_target_id=request.line_target_id,
            target_type=request.target_type,
            is_active=request.is_active,
            actor_id=_actor_id(user),
        )
    )


@router.put("/memberships", response_model=StandardResponse[dict])
async def upsert_daily_report_membership(
    request: DailyReportMembershipUpsert,
    user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    await _project(db, request.project_id)
    return StandardResponse(
        data=daily_report_service.upsert_project_membership(
            project_id=request.project_id,
            principal_type=request.principal_type,
            principal_id=request.principal_id,
            is_active=request.is_active,
            actor_id=_actor_id(user),
        )
    )


@router.get("/customer/reports", response_model=StandardResponse[list[DailyReportItem]])
async def list_customer_reports(user: AuthenticatedUser = Depends(require_customer_user)):
    project_ids = set(
        daily_report_service.list_membership_project_ids(
            principal_type="customer",
            principal_id=user.customer_id or "",
        )
    )
    return StandardResponse(
        data=daily_report_service.list_customer_reports(project_ids=project_ids)
    )


@router.get("/customer/reports/{report_id}", response_model=StandardResponse[DailyReportItem])
async def get_customer_report(
    report_id: str,
    user: AuthenticatedUser = Depends(require_customer_user),
):
    report = daily_report_service.get_customer_report(report_id)
    _assert_customer_project_access(user, report["project_id"])
    return StandardResponse(data=report)


@router.post(
    "/customer/reports/{report_id}/acknowledgements",
    response_model=StandardResponse[DailyReportCustomerActionItem],
)
async def acknowledge_customer_report(
    report_id: str,
    request: DailyReportAcknowledgementCreate,
    user: AuthenticatedUser = Depends(require_customer_user),
):
    report = daily_report_service.get_report(report_id, include_sources=False)
    _assert_customer_project_access(user, report["project_id"])
    return StandardResponse(
        data=daily_report_service.acknowledge_report(
            report_id=report_id,
            customer_id=user.customer_id or "",
            note=request.note,
        )
    )


@router.post(
    "/customer/reports/{report_id}/questions",
    response_model=StandardResponse[DailyReportCustomerActionItem],
)
async def ask_customer_report_question(
    report_id: str,
    request: DailyReportQuestionCreate,
    user: AuthenticatedUser = Depends(require_customer_user),
):
    report = daily_report_service.get_report(report_id, include_sources=False)
    _assert_customer_project_access(user, report["project_id"])
    return StandardResponse(
        data=daily_report_service.ask_report_question(
            report_id=report_id,
            customer_id=user.customer_id or "",
            question=request.question,
        )
    )
