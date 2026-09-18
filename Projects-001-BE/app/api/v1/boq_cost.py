"""Phase 4 internal vendor-cost and price-database API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import AuthenticatedUser, require_admin_user, require_owner_user
from app.api.v1.boq_v2 import _actor, _domain_http_exception, require_boq_v2_rollout
from app.core.database import get_db
from app.schemas.boq_cost_schema import (
    BOQV2CatalogHistoryResponse,
    BOQV2CatalogItemResponse,
    BOQV2CatalogItemUpdateRequest,
    BOQV2CatalogPageResponse,
    BOQV2CatalogPromoteRequest,
    BOQV2CatalogReuseRequest,
    BOQV2CostEstimateUpdateRequest,
    BOQV2CostPlanResponse,
    BOQV2CostPublishRequest,
    BOQV2CostPublishResponse,
    BOQV2OfferCreateRequest,
    BOQV2OfferResponse,
    BOQV2ReferencePriceRequest,
    BOQV2SelectionRequest,
    BOQV2SelectionResponse,
    BOQV2VendorCreateRequest,
    BOQV2VendorResponse,
)
from app.schemas.boq_v2_schema import BOQV2RevisionResponse
from app.schemas.responses import StandardResponse
from app.services.boq_catalog_service import (
    list_catalog_items,
    load_catalog_history,
    promote_catalog_item,
    reuse_catalog_item,
    update_catalog_item,
    update_reference_price,
)
from app.services.boq_cost_service import (
    create_offer,
    create_vendor,
    ensure_working_cost_plan,
    list_offers,
    list_selections,
    list_vendors,
    load_cost_plan,
    publish_cost_plan,
    select_offer,
    update_estimates,
)
from app.services.boq_domain_service import BOQDomainError


router = APIRouter(tags=["BOQ V2 Vendor Cost & Price Database"])
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=8, max_length=200),
]


async def _commit(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise BOQDomainError(
            "BOQ_WRITE_CONFLICT",
            "The resource changed concurrently; reload and retry safely",
        ) from error


@router.get(
    "/projects/{project_id}/vendors",
    response_model=StandardResponse[list[BOQV2VendorResponse]],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_vendors(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(data=await list_vendors(db, project_id))
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.post(
    "/projects/{project_id}/vendors",
    response_model=StandardResponse[BOQV2VendorResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def post_vendor(
    project_id: UUID,
    request: BOQV2VendorCreateRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await create_vendor(
            db, project_id=project_id, request=request,
            actor=_actor(user), idempotency_key=idempotency_key,
        )
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error

@router.get(
    "/projects/{project_id}/vendor-offers",
    response_model=StandardResponse[list[BOQV2OfferResponse]],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_vendor_offers(
    project_id: UUID,
    revision_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(data=await list_offers(db, project_id=project_id, revision_id=revision_id))
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.post(
    "/projects/{project_id}/boq/revisions/{revision_id}/vendor-offers",
    response_model=StandardResponse[BOQV2OfferResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def post_vendor_offer(
    project_id: UUID,
    revision_id: UUID,
    request: BOQV2OfferCreateRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await create_offer(
            db, project_id=project_id, revision_id=revision_id, request=request,
            actor=_actor(user), idempotency_key=idempotency_key,
        )
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.get(
    "/projects/{project_id}/cost-selections",
    response_model=StandardResponse[list[BOQV2SelectionResponse]],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_cost_selections(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(data=await list_selections(db, project_id))
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.post(
    "/projects/{project_id}/cost-selections",
    response_model=StandardResponse[BOQV2SelectionResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def post_cost_selection(
    project_id: UUID,
    request: BOQV2SelectionRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await select_offer(
            db, project_id=project_id, request=request,
            actor=_actor(user), idempotency_key=idempotency_key,
        )
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.get(
    "/projects/{project_id}/cost-plan",
    response_model=StandardResponse[BOQV2CostPlanResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_cost_plan(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(data=await load_cost_plan(db, project_id))
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.post(
    "/projects/{project_id}/cost-plan/working",
    response_model=StandardResponse[BOQV2CostPlanResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def open_working_cost_plan(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await ensure_working_cost_plan(db, project_id=project_id, actor=_actor(user))
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.patch(
    "/projects/{project_id}/cost-plan/estimates",
    response_model=StandardResponse[BOQV2CostPlanResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def patch_cost_estimates(
    project_id: UUID,
    request: BOQV2CostEstimateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await update_estimates(db, project_id=project_id, request=request, actor=_actor(user))
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.post(
    "/projects/{project_id}/cost-plan/publish",
    response_model=StandardResponse[BOQV2CostPublishResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def post_cost_plan_publish(
    project_id: UUID,
    request: BOQV2CostPublishRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await publish_cost_plan(
            db, project_id=project_id, request=request,
            actor=_actor(user), idempotency_key=idempotency_key,
        )
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.get(
    "/price-database/items",
    response_model=StandardResponse[BOQV2CatalogPageResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_price_database_items(
    q: str | None = None,
    category: str | None = None,
    item_status: str | None = Query(default="ACTIVE", alias="status", pattern="^(ACTIVE|ARCHIVED)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    return StandardResponse(
        data=await list_catalog_items(
            db, query=q, category=category, status=item_status,
            page=page, page_size=page_size,
        )
    )


@router.get(
    "/price-database/items/{item_id}",
    response_model=StandardResponse[BOQV2CatalogHistoryResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def get_price_database_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        return StandardResponse(data=await load_catalog_history(db, item_id))
    except BOQDomainError as error:
        raise _domain_http_exception(error) from error


@router.post(
    "/price-database/items/promote",
    response_model=StandardResponse[BOQV2CatalogItemResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def post_price_database_promotion(
    request: BOQV2CatalogPromoteRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await promote_catalog_item(db, request=request, actor=_actor(user))
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.patch(
    "/price-database/items/{item_id}",
    response_model=StandardResponse[BOQV2CatalogItemResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def patch_price_database_item(
    item_id: UUID,
    request: BOQV2CatalogItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await update_catalog_item(db, item_id=item_id, request=request, actor=_actor(user))
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.post(
    "/price-database/items/{item_id}/reference-prices",
    response_model=StandardResponse[BOQV2CatalogItemResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def post_reference_price(
    item_id: UUID,
    request: BOQV2ReferencePriceRequest,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await update_reference_price(db, item_id=item_id, request=request, actor=_actor(user))
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error


@router.post(
    "/price-database/items/{item_id}/reuse/{revision_id}",
    response_model=StandardResponse[BOQV2RevisionResponse],
    dependencies=[Depends(require_boq_v2_rollout)],
)
async def post_catalog_reuse(
    item_id: UUID,
    revision_id: UUID,
    request: BOQV2CatalogReuseRequest,
    idempotency_key: IdempotencyKey,
    db: AsyncSession = Depends(get_db),
    user: AuthenticatedUser = Depends(require_owner_user),
):
    try:
        data = await reuse_catalog_item(
            db, item_id=item_id, revision_id=revision_id, request=request,
            actor=_actor(user), idempotency_key=idempotency_key,
        )
        await _commit(db)
        return StandardResponse(data=data)
    except BOQDomainError as error:
        await db.rollback()
        raise _domain_http_exception(error) from error
