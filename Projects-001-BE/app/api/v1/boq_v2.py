"""Phase 2 API for the feature-gated native BOQ draft workspace."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import AuthenticatedUser, require_admin_user, require_owner_user
from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.boq_v2_schema import (
    BOQV2CreateDocumentRequest,
    BOQV2RevisionResponse,
    BOQV2SaveDraftRequest,
    BOQV2WorkspaceResponse,
)
from app.schemas.responses import StandardResponse
from app.services.boq_document_service import (
    copy_boq_revision,
    create_boq_document,
    load_boq_revision,
    load_boq_workspace,
    save_boq_draft,
)
from app.services.boq_domain_service import BOQDomainError


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
    }:
        http_status = status.HTTP_409_CONFLICT
    else:
        http_status = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail: dict[str, object] = {"code": error.code, "message": error.message}
    if current_version is not None:
        detail["current_version"] = current_version
    return HTTPException(status_code=http_status, detail=detail)


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
