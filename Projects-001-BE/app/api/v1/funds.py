"""Fund bucket read APIs and Owner-only immutable allocation mutations."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import AuthenticatedUser, require_admin_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.observability import log_event
from app.schemas.fund_schema import (
    CreateFundAllocationRequest,
    FundAllocationListResponse,
    FundAllocationResponse,
    FundBucketOption,
    FundSummaryResponse,
    ReverseFundAllocationRequest,
    SetOpeningBalanceRequest,
)
from app.schemas.responses import StandardResponse
from app.services.fund_service import (
    FundDomainError,
    calculate_fund_summary,
    get_allocation,
    list_allocations,
    list_bucket_options,
    post_allocation,
    reverse_allocation,
    set_operations_opening_balance,
)

router = APIRouter(tags=["Project Funds"])
logger = logging.getLogger(__name__)


def _actor(user: AuthenticatedUser) -> str:
    return str(user.email or user.subject)


async def require_fund_owner(
    user: AuthenticatedUser = Depends(require_admin_user),
) -> AuthenticatedUser:
    if not user.has_role("owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only the Owner can mutate Forecast Margin Allocations.",
            },
        )
    return user


def _require_mutations_enabled() -> None:
    if not get_settings().fund_allocation_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "FUND_ALLOCATION_DISABLED",
                "message": "Forecast Margin Allocation mutations are disabled for this environment.",
            },
        )


def _raise_domain_error(
    error: FundDomainError,
    *,
    actor: str,
    project_id: UUID | None = None,
    allocation_id: UUID | None = None,
) -> None:
    rejection_event = {
        "INSUFFICIENT_AVAILABLE_MARGIN": "fund_allocation.rejected_insufficient_margin",
        "STALE_FUND_BALANCE": "fund_allocation.rejected_stale_balance",
        "REVERSAL_WOULD_OVERDRAW_TARGET": "fund_allocation.rejected_reversal_overdraw",
    }.get(error.code, "fund_allocation.rejected")
    log_event(
        logger,
        logging.WARNING,
        rejection_event,
        actor=actor,
        project_id=str(project_id) if project_id else None,
        allocation_id=str(allocation_id) if allocation_id else None,
        error_code=error.code,
        status_code=error.status_code,
    )
    detail: dict[str, object] = {"code": error.code, "message": error.message}
    detail.update(error.context)
    raise HTTPException(status_code=error.status_code, detail=detail) from error


@router.get(
    "/fund-buckets/options",
    response_model=StandardResponse[list[FundBucketOption]],
)
async def get_fund_bucket_options(
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(data=await list_bucket_options(db))
    except FundDomainError as error:
        _raise_domain_error(error, actor=_actor(user))


@router.get(
    "/projects/{project_id}/funds/summary",
    response_model=StandardResponse[FundSummaryResponse],
)
async def get_project_fund_summary(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(data=await calculate_fund_summary(db, project_id))
    except FundDomainError as error:
        _raise_domain_error(error, actor=_actor(user), project_id=project_id)


@router.get(
    "/fund-allocations",
    response_model=StandardResponse[FundAllocationListResponse],
)
async def get_fund_allocations(
    project_id: UUID | None = Query(default=None),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(
            data=await list_allocations(
                db,
                project_id=project_id,
                cursor=cursor,
                limit=limit,
            )
        )
    except FundDomainError as error:
        _raise_domain_error(error, actor=_actor(user), project_id=project_id)


@router.get(
    "/fund-allocations/{allocation_id}",
    response_model=StandardResponse[FundAllocationResponse],
)
async def get_fund_allocation(
    allocation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(data=await get_allocation(db, allocation_id))
    except FundDomainError as error:
        _raise_domain_error(error, actor=_actor(user), allocation_id=allocation_id)


@router.post(
    "/fund-allocations",
    response_model=StandardResponse[FundAllocationResponse],
)
async def create_fund_allocation(
    request: CreateFundAllocationRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_fund_owner),
):
    _require_mutations_enabled()
    actor = _actor(user)
    try:
        allocation = await post_allocation(
            db,
            source_project_id=request.source_project_id,
            target_project_id=request.target_project_id,
            amount=request.amount,
            currency=request.currency,
            reason=request.reason,
            note=request.note,
            expected_source_balance_version=request.expected_source_balance_version,
            idempotency_key=request.idempotency_key,
            actor=actor,
        )
        log_event(
            logger,
            logging.INFO,
            "fund_allocation.created",
            actor=actor,
            allocation_id=str(allocation.id),
            allocation_reference=allocation.reference_no,
            project_id=str(request.source_project_id),
        )
        return StandardResponse(data=allocation)
    except FundDomainError as error:
        _raise_domain_error(error, actor=actor, project_id=request.source_project_id)


@router.post(
    "/fund-allocations/{allocation_id}/reverse",
    response_model=StandardResponse[FundAllocationResponse],
)
async def reverse_fund_allocation(
    allocation_id: UUID,
    request: ReverseFundAllocationRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_fund_owner),
):
    _require_mutations_enabled()
    actor = _actor(user)
    try:
        reversal = await reverse_allocation(
            db,
            allocation_id=allocation_id,
            reason=request.reason,
            idempotency_key=request.idempotency_key,
            expected_source_balance_version=request.expected_source_balance_version,
            actor=actor,
        )
        log_event(
            logger,
            logging.INFO,
            "fund_allocation.reversed",
            actor=actor,
            allocation_id=str(reversal.id),
            allocation_reference=reversal.reference_no,
        )
        return StandardResponse(data=reversal)
    except FundDomainError as error:
        _raise_domain_error(error, actor=actor, allocation_id=allocation_id)


@router.post(
    "/projects/{project_id}/funds/opening-balance",
    response_model=StandardResponse[FundSummaryResponse],
)
async def set_project_fund_opening_balance(
    project_id: UUID,
    request: SetOpeningBalanceRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_fund_owner),
):
    _require_mutations_enabled()
    actor = _actor(user)
    try:
        summary = await set_operations_opening_balance(
            db,
            project_id=project_id,
            amount=request.amount,
            activation_month=request.activation_month,
            reason=request.reason,
            idempotency_key=request.idempotency_key,
            actor=actor,
        )
        log_event(
            logger,
            logging.INFO,
            "operations_bucket.opening_forecast_balance_set",
            actor=actor,
            bucket_id=str(summary.bucket_id),
            project_id=str(project_id),
        )
        return StandardResponse(data=summary)
    except FundDomainError as error:
        _raise_domain_error(error, actor=actor, project_id=project_id)
