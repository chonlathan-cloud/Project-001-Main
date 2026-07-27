"""
Daily Report API for subcontractors, Admin/Owner reviewers, and customers.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile, status
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token
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
from app.core.observability import log_event
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
    DailyReportMediaVisibilityUpdate,
    DailyReportMembershipUpsert,
    DailyReportNoWorkDayCreate,
    DailyReportNoWorkDayItem,
    DailyReportProjectItem,
    DailyReportProjectSettingsItem,
    DailyReportProjectSettingsUpdate,
    DailyReportPublishRequest,
    DailyReportQuestionCreate,
    DailyReportShareLinkItem,
    DailyReportShareLinkUpdate,
    DailyReportSubmissionCreate,
    DailyReportSubmissionItem,
    DailyReportSubmissionUpdate,
    DailyReportStaffNotificationItem,
    DailyReportVersionItem,
    PublicDailyReportItem,
)
from app.schemas.responses import StandardResponse
from app.services import daily_report_service
from app.services.daily_report_line_service import (
    deliver_published_report,
    handle_customer_webhook,
    notify_subcontractor_submission,
    refresh_line_destination_candidate_names,
    verify_customer_webhook_signature,
)
from app.services.daily_report_notification_service import (
    run_cycle_creation_scan,
    run_due_action_scan,
)
from app.services.gcs_storage_service import (
    delete_daily_report_media_storage,
    generate_signed_url_for_storage_key,
    upload_daily_report_media_to_storage,
)
from app.services.daily_report_thumbnail_service import (
    daily_report_thumbnail_storage_key,
)
from app.services.identity_service import get_admin_by_email, get_subcontractor, list_subcontractors

router = APIRouter(prefix="/daily-reports", tags=["Daily Reports"])
internal_router = APIRouter(prefix="/internal/daily-reports", tags=["Daily Report Tasks"])
DAILY_REPORT_STAFF_ROLES = {"admin", "owner"}
logger = logging.getLogger(__name__)

_PHOTO_CONTENT_TYPES = {
    "image/gif",
    "image/heic",
    "image/heif",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
_VIDEO_CONTENT_TYPES = {
    "video/3gpp",
    "video/mp4",
    "video/quicktime",
    "video/webm",
}
_VOICE_CONTENT_TYPES = {
    "audio/aac",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-m4a",
    "audio/x-wav",
}


def _actor_id(user: AuthenticatedUser) -> str:
    return user.email or user.subcontractor_id or user.customer_id or user.subject


def _primary_role(user: AuthenticatedUser) -> str:
    if user.has_role("owner"):
        return "owner"
    if user.has_role("admin"):
        return "admin"
    return str(user.role or "user")


def _staff_company_name(user: AuthenticatedUser) -> str | None:
    if not user.email:
        return None
    profile = get_admin_by_email(user.email)
    if profile is None:
        return None
    return str(profile.company or "").strip() or None


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


async def _signed_daily_report_media_access(media: dict) -> DailyReportMediaAccessResponse:
    settings = get_settings()
    original_url_task = generate_signed_url_for_storage_key(
        storage_key=media["storage_key"],
        expires_in_minutes=settings.signed_url_expires_minutes,
    )
    thumbnail_url_task = None
    if str(media.get("content_type") or "").startswith("image/"):
        thumbnail_url_task = generate_signed_url_for_storage_key(
            storage_key=daily_report_thumbnail_storage_key(media["storage_key"]),
            expires_in_minutes=settings.signed_url_expires_minutes,
        )
    if thumbnail_url_task is None:
        original_url = await original_url_task
        thumbnail_url = None
    else:
        original_url, thumbnail_url = await asyncio.gather(
            original_url_task,
            thumbnail_url_task,
        )
    return DailyReportMediaAccessResponse(
        media_id=media["id"],
        url=original_url,
        thumbnail_url=thumbnail_url,
        expires_in_minutes=settings.signed_url_expires_minutes,
    )


def _require_internal_task_auth(
    *,
    task_secret: str | None,
    authorization: str | None,
) -> None:
    settings = get_settings()
    if (
        settings.daily_report_internal_task_secret
        and task_secret
        and hmac.compare_digest(
            task_secret,
            settings.daily_report_internal_task_secret,
        )
    ):
        return

    scheduler_account = str(
        settings.daily_report_scheduler_service_account or ""
    ).strip().lower()
    scheduler_audience = str(settings.daily_report_scheduler_audience or "").strip()
    if scheduler_account and scheduler_audience and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            try:
                claims = google_id_token.verify_oauth2_token(
                    token,
                    GoogleAuthRequest(),
                    scheduler_audience,
                )
            except (GoogleAuthError, ValueError):
                claims = {}
            token_email = str(claims.get("email") or "").strip().lower()
            if token_email == scheduler_account and claims.get("email_verified") is not False:
                return

    if not settings.daily_report_internal_task_secret and not (
        scheduler_account and scheduler_audience
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Daily Report internal task authentication is not configured.",
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Daily Report task authentication.",
    )


async def _daily_report_scan_context(
    db: AsyncSession,
) -> tuple[list[dict], dict[str, list[str]]]:
    projects = list((await db.execute(select(Project))).scalars().all())
    active_projects = [
        {"id": str(project.id), "name": project.name, "status": project.status}
        for project in projects
        if str(project.status or "").upper() not in {"COMPLETED", "ARCHIVED"}
    ]
    project_subcontractors: dict[str, list[str]] = {}
    for subcontractor in list_subcontractors():
        if not subcontractor.is_active:
            continue
        for project_id in subcontractor.assigned_project_ids:
            project_subcontractors.setdefault(project_id, []).append(subcontractor.id)
    return active_projects, project_subcontractors


def _best_effort_global_failure_alert(*, failure_type: str, title: str) -> None:
    try:
        daily_report_service.ensure_global_staff_notification(
            notification_type=failure_type,
            title=title,
            message="ระบบบันทึกข้อผิดพลาดแล้ว กรุณาตรวจสอบ Cloud Monitoring และลองใหม่",
            discriminator=datetime.now(UTC).strftime("%Y%m%d%H"),
        )
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "daily_report_global_alert_persist_failed",
            notification_type=failure_type,
            error_category=type(exc).__name__,
        )


def _best_effort_project_failure_alert(
    *,
    project_id: str,
    report_date: str,
    failure_type: str,
    title: str,
    submission_id: str | None = None,
    discriminator: str | None = None,
) -> None:
    try:
        daily_report_service.ensure_staff_notification(
            project_id=project_id,
            report_date=report_date,
            notification_type=failure_type,
            title=title,
            message="ระบบบันทึกข้อผิดพลาดแล้ว กรุณาลองใหม่หรือตรวจสอบระบบ",
            submission_id=submission_id,
            discriminator=discriminator,
        )
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "daily_report_project_alert_persist_failed",
            project_id=project_id,
            submission_id=submission_id,
            notification_type=failure_type,
            error_category=type(exc).__name__,
        )


@router.post("/internal/deadline-tick", response_model=StandardResponse[dict])
@router.post("/internal/scan-due-actions", response_model=StandardResponse[dict])
@internal_router.post("/scan-due-actions", response_model=StandardResponse[dict])
async def daily_report_deadline_tick(
    x_daily_report_task_secret: str | None = Header(
        default=None,
        alias="X-Daily-Report-Task-Secret",
    ),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    _require_internal_task_auth(
        task_secret=x_daily_report_task_secret,
        authorization=authorization,
    )
    try:
        active_projects, project_subcontractors = await _daily_report_scan_context(db)
        result = await run_due_action_scan(
            projects=active_projects,
            fallback_project_subcontractors=project_subcontractors,
        )
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "daily_report_scheduler_failure",
            event_type="SCAN_DUE_ACTIONS",
            error_category=type(exc).__name__,
        )
        _best_effort_global_failure_alert(
            failure_type="SCHEDULER_FAILURE",
            title="ระบบตรวจรอบรายงานประจำวันไม่สำเร็จ",
        )
        raise
    log_event(
        logger,
        logging.INFO,
        "daily_report_due_scan_completed",
        projects_checked=result.get("projects_checked"),
        cycles_ready=result.get("cycles_ready"),
        notifications_sent=result.get("notifications_sent"),
        notifications_failed=result.get("notifications_failed"),
        status="SUCCESS",
    )
    return StandardResponse(data=result)


@router.post("/internal/create-due-cycles", response_model=StandardResponse[dict])
@internal_router.post("/create-due-cycles", response_model=StandardResponse[dict])
async def daily_report_create_due_cycles(
    x_daily_report_task_secret: str | None = Header(
        default=None,
        alias="X-Daily-Report-Task-Secret",
    ),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    _require_internal_task_auth(
        task_secret=x_daily_report_task_secret,
        authorization=authorization,
    )
    try:
        active_projects, project_subcontractors = await _daily_report_scan_context(db)
        result = await run_cycle_creation_scan(
            projects=active_projects,
            fallback_project_subcontractors=project_subcontractors,
        )
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "daily_report_scheduler_failure",
            event_type="CREATE_DUE_CYCLES",
            error_category=type(exc).__name__,
        )
        _best_effort_global_failure_alert(
            failure_type="SCHEDULER_FAILURE",
            title="ระบบสร้างรอบรายงานประจำวันไม่สำเร็จ",
        )
        raise
    log_event(
        logger,
        logging.INFO,
        "daily_report_cycle_scan_completed",
        projects_checked=result.get("projects_checked"),
        cycles_ready=result.get("cycles_ready"),
        status="SUCCESS",
    )
    return StandardResponse(data=result)


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
        log_event(
            logger,
            logging.WARNING,
            "line_webhook_signature_rejected",
            status="REJECTED",
        )
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
    result = await handle_customer_webhook(payload)
    log_event(
        logger,
        logging.INFO,
        "line_customer_webhook_processed",
        status="SUCCESS",
    )
    return StandardResponse(data=result)


@router.get("/line/destination-candidates", response_model=StandardResponse[list[dict]])
async def list_daily_report_line_destination_candidates(
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    candidates = daily_report_service.list_line_destination_candidates()
    return StandardResponse(
        data=await refresh_line_destination_candidate_names(candidates)
    )


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
    if daily_report_service.is_no_work_day(
        project_id=request.project_id,
        report_date=request.report_date,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This project date is marked as a no-work day.",
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
    submitted = daily_report_service.submit_submission(
        submission_id=submission_id,
        subcontractor_id=_require_subcontractor(user),
        actor_id=_actor_id(user),
    )
    notification_status = await notify_subcontractor_submission(
        submission=submitted,
        event_type=submitted["status"],
    )
    if notification_status == "FAILED":
        _best_effort_project_failure_alert(
            project_id=submitted["project_id"],
            report_date=submitted["report_date"],
            failure_type="LINE_SUBCONTRACTOR_NOTIFICATION_FAILURE",
            title="แจ้งผลรายงานให้ผู้รับเหมาไม่สำเร็จ",
            submission_id=submission_id,
            discriminator=f"{submission_id}-{submitted['status']}",
        )
    log_event(
        logger,
        logging.INFO if notification_status != "FAILED" else logging.ERROR,
        "daily_report_submission_received",
        project_id=submitted["project_id"],
        submission_id=submission_id,
        status=submitted["status"],
    )
    return StandardResponse(
        data=submitted
    )


def _media_type_and_limit(content_type: str) -> tuple[str, int]:
    settings = get_settings()
    if content_type in _PHOTO_CONTENT_TYPES:
        return "PHOTO", settings.daily_report_photo_max_bytes
    if content_type in _VIDEO_CONTENT_TYPES:
        return "VIDEO", settings.daily_report_video_max_bytes
    if content_type in _VOICE_CONTENT_TYPES:
        return "VOICE", settings.daily_report_audio_max_bytes
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported Daily Report image, video, or audio format.",
    )


async def _inspect_upload_with_limit(
    file: UploadFile,
    max_bytes: int,
) -> tuple[int, bytes]:
    total_bytes = 0
    signature_prefix = b""
    while chunk := await file.read(1024 * 1024):
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Uploaded media exceeds the {max_bytes // (1024 * 1024)}MB limit.",
            )
        if len(signature_prefix) < 32:
            signature_prefix = (signature_prefix + chunk)[:32]
    if total_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded media is empty.",
        )
    await file.seek(0)
    return total_bytes, signature_prefix


def _validate_media_signature(file_bytes: bytes, content_type: str) -> None:
    prefix = file_bytes[:32]
    is_valid = True
    if content_type in {"image/jpeg", "image/jpg"}:
        is_valid = prefix.startswith(b"\xff\xd8\xff")
    elif content_type == "image/png":
        is_valid = prefix.startswith(b"\x89PNG\r\n\x1a\n")
    elif content_type == "image/gif":
        is_valid = prefix.startswith((b"GIF87a", b"GIF89a"))
    elif content_type == "image/webp":
        is_valid = prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP"
    elif content_type in {"image/heic", "image/heif"}:
        is_valid = prefix[4:8] == b"ftyp"
    elif content_type in {"video/mp4", "video/quicktime", "video/3gpp"}:
        is_valid = prefix[4:8] == b"ftyp"
    elif content_type in {"video/webm", "audio/webm"}:
        is_valid = prefix.startswith(b"\x1a\x45\xdf\xa3")
    elif content_type in {"audio/mp4", "audio/x-m4a"}:
        is_valid = prefix[4:8] == b"ftyp"
    elif content_type == "audio/mpeg":
        is_valid = prefix.startswith(b"ID3") or (
            len(prefix) >= 2 and prefix[0] == 0xFF and prefix[1] & 0xE0 == 0xE0
        )
    elif content_type in {"audio/wav", "audio/x-wav"}:
        is_valid = prefix.startswith(b"RIFF") and prefix[8:12] == b"WAVE"
    elif content_type == "audio/ogg":
        is_valid = prefix.startswith(b"OggS")
    elif content_type == "audio/aac":
        is_valid = (
            len(prefix) >= 2 and prefix[0] == 0xFF and prefix[1] & 0xF6 == 0xF0
        )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded media content does not match its file type.",
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
    content_type = str(file.content_type or "application/octet-stream").lower().split(";", 1)[0]
    media_type, max_bytes = _media_type_and_limit(content_type)
    size_bytes, signature_prefix = await _inspect_upload_with_limit(file, max_bytes)
    _validate_media_signature(signature_prefix, content_type)
    media_id = daily_report_service.new_media_id()
    try:
        storage_key = await upload_daily_report_media_to_storage(
            project_id=submission["project_id"],
            report_date=submission["report_date"],
            submission_id=submission_id,
            media_id=media_id,
            file_obj=file.file,
            size_bytes=size_bytes,
            file_name=file.filename,
            content_type=content_type,
        )
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "daily_report_upload_failed",
            project_id=submission["project_id"],
            submission_id=submission_id,
            media_id=media_id,
            error_category=type(exc).__name__,
        )
        _best_effort_project_failure_alert(
            project_id=submission["project_id"],
            report_date=submission["report_date"],
            failure_type="UPLOAD_FAILURE",
            title="อัปโหลดหลักฐานรายงานไม่สำเร็จ",
            submission_id=submission_id,
            discriminator=media_id,
        )
        raise
    try:
        media = daily_report_service.record_media(
            media_id=media_id,
            submission_id=submission_id,
            project_id=submission["project_id"],
            owner_id=subcontractor_id,
            media_type=media_type,
            file_name=file.filename or media_id,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
        )
    except Exception as exc:
        await delete_daily_report_media_storage(storage_key)
        log_event(
            logger,
            logging.ERROR,
            "daily_report_upload_finalization_failed",
            project_id=submission["project_id"],
            submission_id=submission_id,
            media_id=media_id,
            error_category=type(exc).__name__,
        )
        _best_effort_project_failure_alert(
            project_id=submission["project_id"],
            report_date=submission["report_date"],
            failure_type="UPLOAD_FINALIZATION_FAILURE",
            title="บันทึกหลักฐานรายงานไม่สำเร็จ",
            submission_id=submission_id,
            discriminator=media_id,
        )
        raise
    log_event(
        logger,
        logging.INFO,
        "daily_report_upload_completed",
        project_id=submission["project_id"],
        submission_id=submission_id,
        media_id=media_id,
        size_bytes=size_bytes,
        status="SUCCESS",
    )
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
        await delete_daily_report_media_storage(media["storage_key"])
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
        visible = daily_report_service.is_media_published(
            media_id=media_id,
            project_id=media["project_id"],
        )
        if not visible:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Published report media not found.")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily Report media access is required.")
    return StandardResponse(data=await _signed_daily_report_media_access(media))


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


@router.post(
    "/reports/{report_id}/media",
    response_model=StandardResponse[DailyReportMediaItem],
)
async def upload_report_supplemental_media(
    report_id: str,
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    report = daily_report_service.get_report(report_id, include_sources=False)
    _assert_staff_project_access(user, report["project_id"])
    content_type = str(file.content_type or "application/octet-stream").lower().split(";", 1)[0]
    if content_type not in _PHOTO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supplemental customer evidence must be an image.",
        )
    max_bytes = get_settings().daily_report_photo_max_bytes
    size_bytes, signature_prefix = await _inspect_upload_with_limit(file, max_bytes)
    _validate_media_signature(signature_prefix, content_type)
    media_id = daily_report_service.new_media_id()
    storage_key = await upload_daily_report_media_to_storage(
        project_id=report["project_id"],
        report_date=report["report_date"],
        submission_id=f"staff-{report_id}",
        media_id=media_id,
        file_obj=file.file,
        size_bytes=size_bytes,
        file_name=file.filename,
        content_type=content_type,
    )
    try:
        media = daily_report_service.record_supplemental_media(
            media_id=media_id,
            report_id=report_id,
            project_id=report["project_id"],
            owner_id=_actor_id(user),
            uploader_name=user.display_name or user.email,
            media_type="PHOTO",
            file_name=file.filename or media_id,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
        )
    except Exception:
        await delete_daily_report_media_storage(storage_key)
        raise
    return StandardResponse(data={**media, "included_in_customer_report": True})


@router.patch(
    "/reports/{report_id}/media/{media_id}/visibility",
    response_model=StandardResponse[DailyReportItem],
)
async def update_report_media_visibility(
    report_id: str,
    media_id: str,
    request: DailyReportMediaVisibilityUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    current = daily_report_service.get_report(report_id, include_sources=False)
    _assert_staff_project_access(user, current["project_id"])
    daily_report_service.set_report_media_visibility(
        report_id=report_id,
        media_id=media_id,
        included=request.included,
        actor_id=_actor_id(user),
        actor_role=user.role,
    )
    return StandardResponse(data=daily_report_service.get_report(report_id))


@router.delete(
    "/reports/{report_id}/media/{media_id}",
    response_model=StandardResponse[DailyReportItem],
)
async def remove_report_supplemental_media(
    report_id: str,
    media_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    current = daily_report_service.get_report(report_id, include_sources=False)
    _assert_staff_project_access(user, current["project_id"])
    daily_report_service.remove_supplemental_media(
        report_id=report_id,
        media_id=media_id,
        actor_id=_actor_id(user),
        actor_role=user.role,
    )
    return StandardResponse(data=daily_report_service.get_report(report_id))


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
    project_settings = daily_report_service.get_project_settings(current["project_id"])
    configured_company_name = str(
        project_settings.get("reporting_company_name") or ""
    ).strip()
    reporting_company_name = configured_company_name or _staff_company_name(user)
    if reporting_company_name and not configured_company_name:
        daily_report_service.update_project_settings(
            project_id=current["project_id"],
            updates={"reporting_company_name": reporting_company_name},
            actor_id=_actor_id(user),
        )
    published = daily_report_service.publish_report(
        report_id=report_id,
        publication_note=request.publication_note,
        actor_id=_actor_id(user),
        actor_role=user.role,
        reporting_company_name=reporting_company_name,
    )
    delivery_status = await deliver_published_report(published)
    await asyncio.gather(
        *[
            notify_subcontractor_submission(
                submission=daily_report_service.get_submission(submission_id),
                event_type="ACCEPTED",
            )
            for submission_id in published.get("source_submission_ids") or []
        ]
    )
    log_event(
        logger,
        logging.INFO if delivery_status == "SENT" else logging.ERROR,
        "daily_report_publish_delivery_completed",
        project_id=published["project_id"],
        report_id=report_id,
        version=published.get("published_version"),
        status=delivery_status,
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
    settings = daily_report_service.get_project_settings(project_id)
    if not settings.get("reporting_company_name"):
        settings = {
            **settings,
            "reporting_company_name": _staff_company_name(user),
        }
    return StandardResponse(data=settings)


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
    "/projects/{project_id}/share-link",
    response_model=StandardResponse[DailyReportShareLinkItem],
)
async def get_daily_report_share_link(
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _project(db, project_id)
    _assert_staff_project_access(user, project_id)
    return StandardResponse(
        data=daily_report_service.get_customer_share_link_details(project_id)
    )


@router.put(
    "/projects/{project_id}/share-link",
    response_model=StandardResponse[DailyReportShareLinkItem],
)
async def update_daily_report_share_link(
    project_id: str,
    request: DailyReportShareLinkUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _project(db, project_id)
    _assert_staff_project_access(user, project_id)
    return StandardResponse(
        data=daily_report_service.update_customer_share_link(
            project_id=project_id,
            enabled=request.enabled,
            rotate=request.rotate,
            actor_id=_actor_id(user),
            actor_role=_primary_role(user),
        )
    )


@router.get(
    "/projects/{project_id}/no-work-days",
    response_model=StandardResponse[list[DailyReportNoWorkDayItem]],
)
async def list_daily_report_no_work_days(
    project_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _project(db, project_id)
    _assert_staff_project_access(user, project_id)
    return StandardResponse(data=daily_report_service.list_no_work_days(project_id=project_id))


@router.post(
    "/projects/{project_id}/no-work-days",
    response_model=StandardResponse[DailyReportNoWorkDayItem],
)
async def set_daily_report_no_work_day(
    project_id: str,
    request: DailyReportNoWorkDayCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _project(db, project_id)
    _assert_staff_project_access(user, project_id)
    return StandardResponse(
        data=daily_report_service.set_no_work_day(
            project_id=project_id,
            report_date=request.report_date,
            reason=request.reason,
            actor_id=_actor_id(user),
            actor_role=user.role,
        )
    )


@router.delete(
    "/projects/{project_id}/no-work-days/{report_date}",
    response_model=StandardResponse[DailyReportNoWorkDayItem],
)
async def clear_daily_report_no_work_day(
    project_id: str,
    report_date: date,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_staff(user)
    await _project(db, project_id)
    _assert_staff_project_access(user, project_id)
    return StandardResponse(
        data=daily_report_service.clear_no_work_day(
            project_id=project_id,
            report_date=report_date,
            actor_id=_actor_id(user),
            actor_role=user.role,
        )
    )


@router.get(
    "/notifications",
    response_model=StandardResponse[list[DailyReportStaffNotificationItem]],
)
async def list_daily_report_notifications(
    unread_only: bool = Query(default=False),
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    return StandardResponse(
        data=daily_report_service.list_staff_notifications(
            project_ids=_admin_project_ids(user),
            unread_only=unread_only,
        )
    )


@router.post(
    "/notifications/{notification_id}/read",
    response_model=StandardResponse[DailyReportStaffNotificationItem],
)
async def read_daily_report_notification(
    notification_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    _require_staff(user)
    visible = next(
        (
            item
            for item in daily_report_service.list_staff_notifications(
                project_ids=_admin_project_ids(user),
            )
            if item.get("id") == notification_id
        ),
        None,
    )
    if visible is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily report notification {notification_id} not found.",
        )
    return StandardResponse(
        data=daily_report_service.mark_staff_notification_read(
            notification_id=notification_id,
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


@router.get(
    "/public/reports",
    response_model=StandardResponse[list[PublicDailyReportItem]],
)
async def list_public_customer_reports(
    share_token: str = Header(default="", alias="X-Customer-Report-Share"),
):
    project_id = daily_report_service.resolve_customer_share_project(share_token)
    return StandardResponse(
        data=daily_report_service.list_public_customer_reports(project_id=project_id)
    )


@router.get(
    "/public/reports/{report_id}",
    response_model=StandardResponse[PublicDailyReportItem],
)
async def get_public_customer_report(
    report_id: str,
    share_token: str = Header(default="", alias="X-Customer-Report-Share"),
):
    project_id = daily_report_service.resolve_customer_share_project(share_token)
    return StandardResponse(
        data=daily_report_service.get_public_customer_report(
            project_id=project_id,
            report_id=report_id,
        )
    )


@router.get(
    "/public/media/{media_id}/signed-url",
    response_model=StandardResponse[DailyReportMediaAccessResponse],
)
async def get_public_customer_report_media_url(
    media_id: str,
    share_token: str = Header(default="", alias="X-Customer-Report-Share"),
):
    project_id = daily_report_service.resolve_customer_share_project(share_token)
    media = daily_report_service.get_media(media_id)
    visible = (
        media.get("project_id") == project_id
        and daily_report_service.is_media_published(
            media_id=media_id,
            project_id=project_id,
        )
    )
    if not visible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Published report media not found.",
        )
    return StandardResponse(data=await _signed_daily_report_media_access(media))


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
    question = daily_report_service.ask_report_question(
        report_id=report_id,
        customer_id=user.customer_id or "",
        question=request.question,
    )
    log_event(
        logger,
        logging.INFO,
        "daily_report_customer_question_created",
        project_id=report["project_id"],
        report_id=report_id,
        status="OPEN",
    )
    return StandardResponse(data=question)
