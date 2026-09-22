"""Phase 2 API for the feature-gated native BOQ draft workspace."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import AuthenticatedUser, require_admin_user, require_owner_user
from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.boq_v2_schema import (
    BOQV2CreateDocumentRequest,
    BOQV2RevisionResponse,
    BOQV2SaveDraftRequest,
    BOQV2QuotationListResponse,
    BOQV2QuotationMediaResponse,
    BOQV2WorkspaceResponse,
)
from app.schemas.boq_quotation_schema import (
    BOQV2AcceptanceResponse,
    BOQV2CreateAlternativeRequest,
    BOQV2CreateChangeOrderRequest,
    BOQV2ExpectedVersionRequest,
    BOQV2ExportArtifactResponse,
    BOQV2ExportRequest,
    BOQV2MediaCandidate,
    BOQV2MediaImportRequest,
    BOQV2QuotationPreviewResponse,
    BOQV2RecordAcceptanceRequest,
    BOQV2TransitionRequest,
)
from app.schemas.responses import StandardResponse
from app.services.boq_document_service import (
    copy_boq_revision,
    create_boq_document,
    load_boq_revision,
    load_boq_workspace,
    list_quotations,
    save_boq_draft,
)
from app.services.boq_quotation_media_service import (
    delete_media,
    import_media,
    list_media_candidates,
    media_access,
    upload_media,
)
from app.services.boq_domain_service import BOQDomainError
from app.services.boq_export_service import (
    create_export_download,
    load_export_response,
    render_and_upload_export,
    request_export,
)
from app.services.boq_quotation_service import (
    create_alternative,
    create_change_order,
    create_preview_snapshot,
    issue_quotation,
    load_quotation_preview,
    record_acceptance,
    revise_quotation,
    transition_quotation,
)


router = APIRouter(tags=["Native BOQ V2"])
IdempotencyKey = Annotated[
    str,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=200,
        description="Caller-generated stable key for safe command retries",
    ),
]


def require_boq_v2_rollout() -> None:
    if not get_settings().boq_v2_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "BOQ_V2_ROLLOUT_DISABLED",
                "message": "Native BOQ is not enabled for this environment",
            },
        )


def _actor(user: AuthenticatedUser) -> str:
    return str(user.email or user.subject).strip()


async def _read_quotation_upload(file: UploadFile) -> bytes:
    limit = get_settings().boq_quotation_media_max_bytes
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > limit:
            raise BOQDomainError(
                "QUOTATION_MEDIA_TOO_LARGE",
                f"Quotation image exceeds the {limit // (1024 * 1024)}MB limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _domain_http_exception(
    error: BOQDomainError,
    *,
    current_version: int | None = None,
) -> HTTPException:
    if error.code.endswith("_NOT_FOUND"):
        http_status = status.HTTP_404_NOT_FOUND
    elif error.code in {
        "STALE_BOQ_VERSION",
        "IDEMPOTENCY_CONFLICT",
        "COMMAND_IN_PROGRESS",
        "IMMUTABLE_BOQ_REVISION",
        "FINANCIAL_DISCARD_CONFIRMATION_REQUIRED",
        "BOQ_NOT_AVAILABLE",
        "PHASE_2_MAIN_ONLY",
        "INVALID_REVISION_SOURCE",
        "INVALID_ACCEPTANCE_STATE",
        "INVALID_TRANSITION",
        "STALE_BASELINE_VERSION",
        "ACTIVE_BASELINE_REQUIRED",
        "BASELINE_REPLACEMENT_CONFIRMATION_REQUIRED",
        "CHANGE_ORDER_REPLACEMENT_MAPPING_INCOMPLETE",
        "DEDUCTION_EXCEEDS_REMAINING_SCOPE",
        "CHANGE_ORDER_TARGET_NOT_ACTIVE",
        "EXPORT_NOT_READY",
        "EXPORT_COST_PLAN_MISMATCH",
        "STALE_COST_PLAN_VERSION",
        "STALE_COST_SELECTION",
        "WORKING_COST_PLAN_REQUIRED",
        "OFFER_FULL_COVERAGE_REQUIRED",
        "OFFER_WARNING_CONFIRMATION_REQUIRED",
        "STALE_CATALOG_VERSION",
        "CATALOG_CODE_EXISTS",
        "QUOTATION_MEDIA_IN_USE",
        "QUOTATION_MEDIA_MISSING",
        "QUOTATION_MEDIA_HASH_MISMATCH",
        "QUOTATION_DOCUMENT_INVALID",
    }:
        http_status = status.HTTP_409_CONFLICT
    elif error.code == "QUOTATION_MEDIA_TOO_LARGE":
        http_status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif error.code == "QUOTATION_MEDIA_TYPE_INVALID":
        http_status = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    elif error.code in {"EXPORT_STORAGE_FAILED", "EXPORT_RENDER_FAILED"}:
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail: dict[str, object] = {"code": error.code, "message": error.message}
    if current_version is not None:
        detail["current_version"] = current_version
    return HTTPException(status_code=http_status, detail=detail)


@router.get(
    "/boq/quotations",
    response_model=StandardResponse[BOQV2QuotationListResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_native_boq_quotations(
    search: str | None = Query(default=None, max_length=200),
    status_filter: Literal[
        "DRAFT", "ISSUED", "ACCEPTED", "WITHDRAWN", "REJECTED", "SUPERSEDED"
    ]
    | None = Query(default=None, alias="status"),
    document_kind: Literal["MAIN", "ALTERNATIVE", "CHANGE_ORDER"] | None = Query(
        default=None
    ),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    if date_from and date_to and date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_DATE_RANGE",
                "message": "date_to cannot precede date_from",
            },
        )
    return StandardResponse(
        data=await list_quotations(
            db,
            search=search,
            status=status_filter,
            document_kind=document_kind,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/projects/{project_id}/boq-workspace",
    response_model=StandardResponse[BOQV2WorkspaceResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_boq_workspace(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        data = await load_boq_workspace(
            db,
            project_id,
            can_edit=user.has_role("owner"),
        )
        return StandardResponse(data=data)
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.get(
    "/boq/revisions/{revision_id}",
    response_model=StandardResponse[BOQV2RevisionResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_boq_revision(
    revision_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(data=await load_boq_revision(db, revision_id))
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.get(
    "/boq/revisions/{revision_id}/media-candidates",
    response_model=StandardResponse[list[BOQV2MediaCandidate]],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_native_boq_media_candidates(
    revision_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        revision = await load_boq_revision(db, revision_id)
        return StandardResponse(
            data=await list_media_candidates(project_id=revision.project_id)
        )
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.post(
    "/boq/revisions/{revision_id}/media",
    response_model=StandardResponse[BOQV2QuotationMediaResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def upload_native_boq_media(
    revision_id: UUID,
    expected_version: int = Form(..., ge=1),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        file_bytes = await _read_quotation_upload(file)
        data = await upload_media(
            db,
            revision_id=revision_id,
            expected_version=expected_version,
            actor=_actor(user),
            file_bytes=file_bytes,
            file_name=file.filename,
            content_type=file.content_type,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.post(
    "/boq/revisions/{revision_id}/media/import",
    response_model=StandardResponse[BOQV2QuotationMediaResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def import_native_boq_media(
    revision_id: UUID,
    request: BOQV2MediaImportRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await import_media(
            db,
            revision_id=revision_id,
            expected_version=request.expected_version,
            actor=_actor(user),
            origin_type=request.origin_type,
            origin_id=request.origin_id,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.delete(
    "/boq/revisions/{revision_id}/media/{media_id}",
    response_model=StandardResponse[dict],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def delete_native_boq_media(
    revision_id: UUID,
    media_id: UUID,
    request: BOQV2ExpectedVersionRequest,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await delete_media(
            db,
            revision_id=revision_id,
            media_id=media_id,
            expected_version=request.expected_version,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.get(
    "/boq/revisions/{revision_id}/media/{media_id}/signed-url",
    response_model=StandardResponse[BOQV2QuotationMediaResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_native_boq_media_signed_url(
    revision_id: UUID,
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(
            data=await media_access(
                db,
                revision_id=revision_id,
                media_id=media_id,
            )
        )
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.post(
    "/projects/{project_id}/boq/documents",
    response_model=StandardResponse[BOQV2RevisionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def create_native_boq_document(
    project_id: UUID,
    request: BOQV2CreateDocumentRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await create_boq_document(
            db,
            project_id=project_id,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "BOQ_WRITE_CONFLICT",
                "message": "The BOQ draft changed concurrently; reload and retry",
            },
        ) from error


@router.patch(
    "/boq/revisions/{revision_id}",
    response_model=StandardResponse[BOQV2RevisionResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def update_native_boq_draft(
    revision_id: UUID,
    request: BOQV2SaveDraftRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await save_boq_draft(
            db,
            revision_id=revision_id,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        current_version = None
        if error.code == "STALE_BOQ_VERSION":
            try:
                current_version = (await load_boq_revision(db, revision_id)).version
            except BOQDomainError:
                current_version = None
        raise _domain_http_exception(
            error,
            current_version=current_version,
        ) from error
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "BOQ_WRITE_CONFLICT",
                "message": "The BOQ draft changed concurrently; reload and retry",
            },
        ) from error


@router.post(
    "/projects/{project_id}/boq/revisions/{source_revision_id}/copy",
    response_model=StandardResponse[BOQV2RevisionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def copy_native_boq_revision(
    project_id: UUID,
    source_revision_id: UUID,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await copy_boq_revision(
            db,
            target_project_id=project_id,
            source_revision_id=source_revision_id,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "BOQ_WRITE_CONFLICT",
                "message": "The BOQ copy conflicted with another command; retry safely",
            },
        ) from error


@router.post(
    "/boq/revisions/{revision_id}/preview-snapshots",
    response_model=StandardResponse[BOQV2QuotationPreviewResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def create_native_boq_preview_snapshot(
    revision_id: UUID,
    request: BOQV2ExpectedVersionRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await create_preview_snapshot(
            db,
            revision_id=revision_id,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.get(
    "/boq/revisions/{revision_id}/preview",
    response_model=StandardResponse[BOQV2QuotationPreviewResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_native_boq_preview(
    revision_id: UUID,
    snapshot_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(
            data=await load_quotation_preview(
                db,
                revision_id=revision_id,
                snapshot_id=snapshot_id,
            )
        )
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.post(
    "/boq/revisions/{revision_id}/issue",
    response_model=StandardResponse[BOQV2RevisionResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def issue_native_boq_quotation(
    revision_id: UUID,
    request: BOQV2ExpectedVersionRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await issue_quotation(
            db,
            revision_id=revision_id,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "BOQ_WRITE_CONFLICT",
                "message": "The quotation changed concurrently; reload and retry",
            },
        ) from error


@router.post(
    "/boq/revisions/{revision_id}/revise",
    response_model=StandardResponse[BOQV2RevisionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def revise_native_boq_quotation(
    revision_id: UUID,
    request: BOQV2ExpectedVersionRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await revise_quotation(
            db,
            revision_id=revision_id,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "BOQ_WRITE_CONFLICT",
                "message": "The quotation revision conflicted; reload and retry",
            },
        ) from error


@router.post(
    "/boq/revisions/{revision_id}/alternatives",
    response_model=StandardResponse[BOQV2RevisionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def create_native_boq_alternative(
    revision_id: UUID,
    request: BOQV2CreateAlternativeRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await create_alternative(
            db,
            revision_id=revision_id,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "BOQ_WRITE_CONFLICT",
                "message": "The alternative conflicted with another command",
            },
        ) from error


@router.post(
    "/projects/{project_id}/boq/change-orders",
    response_model=StandardResponse[BOQV2RevisionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def create_native_boq_change_order(
    project_id: UUID,
    request: BOQV2CreateChangeOrderRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await create_change_order(
            db,
            project_id=project_id,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "BOQ_WRITE_CONFLICT",
                "message": "The active baseline changed; reload and retry",
            },
        ) from error


@router.post(
    "/boq/revisions/{revision_id}/record-acceptance",
    response_model=StandardResponse[BOQV2AcceptanceResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def record_native_boq_acceptance(
    revision_id: UUID,
    request: BOQV2RecordAcceptanceRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await record_acceptance(
            db,
            revision_id=revision_id,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "BOQ_WRITE_CONFLICT",
                "message": "Acceptance conflicted with the active baseline",
            },
        ) from error


async def _transition_native_boq(
    *,
    revision_id: UUID,
    action: str,
    request: BOQV2TransitionRequest,
    idempotency_key: str,
    db: AsyncSession,
    user: AuthenticatedUser,
) -> StandardResponse[BOQV2RevisionResponse]:
    try:
        data = await transition_quotation(
            db,
            revision_id=revision_id,
            action=action,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.post(
    "/boq/revisions/{revision_id}/withdraw",
    response_model=StandardResponse[BOQV2RevisionResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def withdraw_native_boq_quotation(
    revision_id: UUID,
    request: BOQV2TransitionRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    return await _transition_native_boq(
        revision_id=revision_id,
        action="WITHDRAW",
        request=request,
        idempotency_key=idempotency_key,
        db=db,
        user=user,
    )


@router.post(
    "/boq/revisions/{revision_id}/reject",
    response_model=StandardResponse[BOQV2RevisionResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def reject_native_boq_quotation(
    revision_id: UUID,
    request: BOQV2TransitionRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    return await _transition_native_boq(
        revision_id=revision_id,
        action="REJECT",
        request=request,
        idempotency_key=idempotency_key,
        db=db,
        user=user,
    )


@router.post(
    "/boq/revisions/{revision_id}/exports",
    response_model=StandardResponse[BOQV2ExportArtifactResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def export_native_boq_quotation(
    revision_id: UUID,
    request: BOQV2ExportRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        artifact = await request_export(
            db,
            revision_id=revision_id,
            request=request,
            actor=_actor(user),
            idempotency_key=idempotency_key,
        )
        await db.commit()
        data = await render_and_upload_export(
            db,
            revision_id=revision_id,
            artifact_id=artifact.id,
        )
        await db.commit()
        return StandardResponse(data=data)
    except BOQDomainError as error:
        if error.code.startswith("EXPORT_"):
            await db.commit()
        else:
            await db.rollback()
        raise _domain_http_exception(error) from error
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXPORT_WRITE_CONFLICT",
                "message": "Export request conflicted; retry with the same key",
            },
        ) from error


@router.get(
    "/boq/revisions/{revision_id}/exports/{artifact_id}",
    response_model=StandardResponse[BOQV2ExportArtifactResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_native_boq_export(
    revision_id: UUID,
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(
            data=await load_export_response(
                db,
                revision_id=revision_id,
                artifact_id=artifact_id,
            )
        )
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.get(
    "/boq/revisions/{revision_id}/exports/{artifact_id}/download",
    response_model=StandardResponse[BOQV2ExportArtifactResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def download_native_boq_export(
    revision_id: UUID,
    artifact_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(
            data=await create_export_download(
                db,
                revision_id=revision_id,
                artifact_id=artifact_id,
            )
        )
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error
