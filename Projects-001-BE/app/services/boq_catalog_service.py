"""Explicit BOQ V2 catalog, reference-price, history, and reuse operations."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boq import Project
from app.models.boq_v2 import (
    BOQV2AuditEvent,
    BOQV2CatalogItem,
    BOQV2CatalogPriceVersion,
    BOQV2PriceObservation,
    BOQV2RevisionSnapshot,
    BOQV2ScopeNode,
)
from app.schemas.boq_cost_schema import (
    BOQV2CatalogHistoryResponse,
    BOQV2CatalogItemResponse,
    BOQV2CatalogItemUpdateRequest,
    BOQV2CatalogPageResponse,
    BOQV2CatalogPriceResponse,
    BOQV2CatalogPromoteRequest,
    BOQV2CatalogReuseRequest,
    BOQV2PriceObservationResponse,
    BOQV2ReferencePriceRequest,
)
from app.schemas.boq_v2_schema import (
    BOQV2CostComponentDraft,
    BOQV2SaveDraftRequest,
    BOQV2ScopeNodeDraft,
)
from app.services.boq_document_service import load_boq_revision, save_boq_draft
from app.services.boq_domain_service import BOQDomainError, acquire_project_budget_locks
from app.services.boq_calculation_service import money


def _timestamp(value: datetime | None) -> str:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _rate(value: object) -> str:
    return f"{Decimal(str(value)):.4f}"


async def record_sell_observations_from_snapshot(
    db: AsyncSession,
    *,
    snapshot: BOQV2RevisionSnapshot,
    observation_kind: str,
    source_event_type: str,
    source_event_id: UUID,
    observed_at: datetime,
) -> None:
    """Record one immutable business-event observation per sell component.

    The logical lineage root, not revision row identity, is the sample key so
    copied/revised rows do not become independent samples merely through edit
    history. Offered and accepted events remain distinct observation kinds.
    """

    for node in snapshot.customer_payload.get("scope", []):
        if node.get("node_kind") != "ITEM" or node.get("inclusion_state") == "EXCLUDED":
            continue
        logical_id = UUID(str(node["logical_id"]))
        lineage_root = UUID(str(node.get("source_logical_id") or node["logical_id"]))
        quantity = Decimal(str(node.get("quantity") or 0))
        for component_type, field in (
            ("MATERIAL", "sell_material_unit_rate"),
            ("LABOR", "sell_labor_unit_rate"),
        ):
            raw_rate = node.get(field)
            if raw_rate is None:
                continue
            event_key = f"{source_event_type.lower()}:{source_event_id}:{logical_id}:{component_type}"
            exists = (
                await db.execute(
                    select(BOQV2PriceObservation.id).where(
                        BOQV2PriceObservation.event_key == event_key
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue
            rate = Decimal(str(raw_rate))
            catalog_item_id = node.get("catalog_item_id")
            db.add(
                BOQV2PriceObservation(
                    id=uuid4(), event_key=event_key,
                    sample_key=f"sell:{lineage_root}:{component_type}",
                    observation_kind=observation_kind,
                    project_id=snapshot.project_id, document_id=snapshot.document_id,
                    revision_id=snapshot.revision_id,
                    scope_node_id=UUID(str(node["id"])), logical_item_id=logical_id,
                    component_type=component_type,
                    catalog_item_id=UUID(str(catalog_item_id)) if catalog_item_id else None,
                    source_event_type=source_event_type, source_event_id=source_event_id,
                    observed_at=observed_at, quantity=quantity, unit=node.get("unit"),
                    specification=node.get("specification"), tax_basis="EXCLUSIVE_VAT",
                    currency="THB", unit_rate=rate, total=money(quantity * rate),
                    vendor_id=None, lineage_root_id=lineage_root,
                )
            )


async def _project_exists(db: AsyncSession, project_id: UUID) -> None:
    if (await db.execute(select(Project.id).where(Project.id == project_id))).scalar_one_or_none() is None:
        raise BOQDomainError("PROJECT_NOT_FOUND", "Project was not found")


def _price_response(row: BOQV2CatalogPriceVersion) -> BOQV2CatalogPriceResponse:
    return BOQV2CatalogPriceResponse(
        id=row.id, price_kind=row.price_kind, version=row.version,
        amount=_rate(row.amount), tax_basis=row.tax_basis,
        effective_date=row.effective_date, source_observation_id=row.source_observation_id,
        reason=row.reason, current=row.is_current, created_at=_timestamp(row.created_at),
    )


async def _item_response(db: AsyncSession, item: BOQV2CatalogItem) -> BOQV2CatalogItemResponse:
    prices = list(
        (
            await db.execute(
                select(BOQV2CatalogPriceVersion)
                .where(
                    BOQV2CatalogPriceVersion.catalog_item_id == item.id,
                    BOQV2CatalogPriceVersion.is_current.is_(True),
                )
                .order_by(BOQV2CatalogPriceVersion.price_kind)
            )
        ).scalars().all()
    )
    observation_count, distinct_count = (
        await db.execute(
            select(
                func.count(BOQV2PriceObservation.id),
                func.count(func.distinct(BOQV2PriceObservation.sample_key)),
            ).where(BOQV2PriceObservation.catalog_item_id == item.id)
        )
    ).one()
    return BOQV2CatalogItemResponse(
        id=item.id, code=item.code, name=item.name, specification=item.specification,
        unit=item.unit, category=item.category, tags=list(item.tags or []),
        status=item.status, version=item.version,
        current_prices=[_price_response(row) for row in prices],
        observation_count=int(observation_count or 0),
        distinct_sample_count=int(distinct_count or 0),
        created_at=_timestamp(item.created_at), updated_at=_timestamp(item.updated_at),
    )


async def list_catalog_items(
    db: AsyncSession,
    *,
    query: str | None,
    category: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> BOQV2CatalogPageResponse:
    filters = []
    if query and query.strip():
        pattern = f"%{query.strip()}%"
        filters.append(
            or_(
                BOQV2CatalogItem.code.ilike(pattern),
                BOQV2CatalogItem.name.ilike(pattern),
                BOQV2CatalogItem.specification.ilike(pattern),
                BOQV2CatalogItem.unit.ilike(pattern),
                BOQV2CatalogItem.category.ilike(pattern),
            )
        )
    if category:
        filters.append(BOQV2CatalogItem.category == category)
    if status:
        filters.append(BOQV2CatalogItem.status == status)
    total = int((await db.execute(select(func.count()).select_from(BOQV2CatalogItem).where(*filters))).scalar_one())
    rows = list(
        (
            await db.execute(
                select(BOQV2CatalogItem)
                .where(*filters)
                .order_by(BOQV2CatalogItem.code)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
    )
    return BOQV2CatalogPageResponse(
        items=[await _item_response(db, row) for row in rows],
        page=page, page_size=page_size, total=total,
    )


async def load_catalog_history(db: AsyncSession, item_id: UUID) -> BOQV2CatalogHistoryResponse:
    item = (await db.execute(select(BOQV2CatalogItem).where(BOQV2CatalogItem.id == item_id))).scalar_one_or_none()
    if item is None:
        raise BOQDomainError("CATALOG_ITEM_NOT_FOUND", "Catalog item was not found")
    prices = list(
        (
            await db.execute(
                select(BOQV2CatalogPriceVersion)
                .where(BOQV2CatalogPriceVersion.catalog_item_id == item_id)
                .order_by(BOQV2CatalogPriceVersion.price_kind, BOQV2CatalogPriceVersion.version.desc())
            )
        ).scalars().all()
    )
    observations = list(
        (
            await db.execute(
                select(BOQV2PriceObservation)
                .where(BOQV2PriceObservation.catalog_item_id == item_id)
                .order_by(BOQV2PriceObservation.observed_at.desc())
                .limit(500)
            )
        ).scalars().all()
    )
    response_observations = [
        BOQV2PriceObservationResponse(
            id=row.id, observation_kind=row.observation_kind, sample_key=row.sample_key,
            project_id=row.project_id, document_id=row.document_id, revision_id=row.revision_id,
            scope_node_id=row.scope_node_id, logical_item_id=row.logical_item_id,
            component_type=row.component_type, source_event_type=row.source_event_type,
            source_event_id=row.source_event_id, observed_at=_timestamp(row.observed_at),
            quantity=_rate(row.quantity) if row.quantity is not None else None,
            unit=row.unit, specification=row.specification, tax_basis=row.tax_basis,
            unit_rate=_rate(row.unit_rate), total=f"{Decimal(str(row.total)):.2f}",
            vendor_id=row.vendor_id, lineage_root_id=row.lineage_root_id,
        )
        for row in observations
    ]
    distinct_count = len({row.sample_key for row in observations})
    return BOQV2CatalogHistoryResponse(
        item=await _item_response(db, item), prices=[_price_response(row) for row in prices],
        observations=response_observations, distinct_sample_count=distinct_count,
    )


async def _add_price_version(
    db: AsyncSession,
    *,
    item: BOQV2CatalogItem,
    price_kind: str,
    amount: Decimal,
    tax_basis: str,
    effective_date: date,
    source_observation_id: UUID | None,
    reason: str,
    actor: str,
) -> BOQV2CatalogPriceVersion:
    await db.execute(
        update(BOQV2CatalogPriceVersion)
        .where(
            BOQV2CatalogPriceVersion.catalog_item_id == item.id,
            BOQV2CatalogPriceVersion.price_kind == price_kind,
            BOQV2CatalogPriceVersion.is_current.is_(True),
        )
        .values(is_current=False)
    )
    next_version = int(
        (
            await db.execute(
                select(func.coalesce(func.max(BOQV2CatalogPriceVersion.version), 0)).where(
                    BOQV2CatalogPriceVersion.catalog_item_id == item.id,
                    BOQV2CatalogPriceVersion.price_kind == price_kind,
                )
            )
        ).scalar_one()
    ) + 1
    row = BOQV2CatalogPriceVersion(
        id=uuid4(), catalog_item_id=item.id, price_kind=price_kind,
        version=next_version, amount=amount, tax_basis=tax_basis,
        effective_date=effective_date, source_observation_id=source_observation_id,
        reason=reason.strip(), is_current=True, created_by=actor,
    )
    db.add(row)
    return row


async def promote_catalog_item(
    db: AsyncSession, *, request: BOQV2CatalogPromoteRequest, actor: str
) -> BOQV2CatalogItemResponse:
    observation = None
    node = None
    if request.observation_id:
        observation = (
            await db.execute(
                select(BOQV2PriceObservation)
                .where(BOQV2PriceObservation.id == request.observation_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if observation is None:
            raise BOQDomainError("PRICE_OBSERVATION_NOT_FOUND", "Promotion source observation was not found")
        project_id = observation.project_id
    else:
        node = (
            await db.execute(
                select(BOQV2ScopeNode)
                .where(BOQV2ScopeNode.id == request.source_node_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if node is None:
            raise BOQDomainError("SCOPE_NODE_NOT_FOUND", "Promotion source node was not found")
        project_id = node.project_id
    await acquire_project_budget_locks(db, [project_id])
    existing = (
        await db.execute(select(BOQV2CatalogItem).where(func.lower(BOQV2CatalogItem.code) == request.code.strip().lower()))
    ).scalar_one_or_none()
    if existing is not None:
        raise BOQDomainError("CATALOG_CODE_EXISTS", "Catalog code already exists; use explicit update instead")
    item = BOQV2CatalogItem(
        id=uuid4(), code=request.code.strip(), name=request.name.strip(),
        specification=(request.specification or "").strip() or None,
        unit=request.unit.strip(), category=(request.category or "").strip() or None,
        tags=sorted({tag.strip() for tag in request.tags if tag.strip()}),
        status="ACTIVE", version=1, created_by=actor, updated_by=actor,
    )
    db.add(item)
    await db.flush()
    if request.price_kind and request.reference_amount is not None:
        await _add_price_version(
            db, item=item, price_kind=request.price_kind, amount=request.reference_amount,
            tax_basis=request.tax_basis, effective_date=request.effective_date or date.today(),
            source_observation_id=observation.id if observation else None,
            reason=request.reason, actor=actor,
        )
    if observation is not None:
        observation.catalog_item_id = item.id
    if node is not None:
        node.catalog_item_id = item.id
        node.catalog_item_version = item.version
        lineage_root = node.source_logical_id or node.logical_id
        await db.execute(
            update(BOQV2PriceObservation)
            .where(
                BOQV2PriceObservation.catalog_item_id.is_(None),
                BOQV2PriceObservation.lineage_root_id == lineage_root,
            )
            .values(catalog_item_id=item.id)
        )
    db.add(
        BOQV2AuditEvent(
            id=uuid4(), event_key=f"PROMOTE_CATALOG_ITEM:{item.id}", project_id=project_id,
            actor=actor, command_type="PROMOTE_CATALOG_ITEM", entity_type="CATALOG_ITEM",
            entity_id=item.id,
            after_reference={
                "code": item.code,
                "source_observation_id": str(observation.id) if observation else None,
                "source_node_id": str(node.id) if node else None,
            }, reason=request.reason.strip(),
        )
    )
    await db.flush()
    return await _item_response(db, item)


async def update_catalog_item(
    db: AsyncSession, *, item_id: UUID, request: BOQV2CatalogItemUpdateRequest, actor: str
) -> BOQV2CatalogItemResponse:
    await _project_exists(db, request.project_id)
    await acquire_project_budget_locks(db, [request.project_id])
    item = (
        await db.execute(select(BOQV2CatalogItem).where(BOQV2CatalogItem.id == item_id).with_for_update())
    ).scalar_one_or_none()
    if item is None:
        raise BOQDomainError("CATALOG_ITEM_NOT_FOUND", "Catalog item was not found")
    if item.version != request.expected_version:
        raise BOQDomainError("STALE_CATALOG_VERSION", "Catalog item changed; reload and retry")
    before = {"version": item.version, "status": item.status, "name": item.name}
    item.name = request.name.strip()
    item.specification = (request.specification or "").strip() or None
    item.unit = request.unit.strip()
    item.category = (request.category or "").strip() or None
    item.tags = sorted({tag.strip() for tag in request.tags if tag.strip()})
    item.status = request.status
    item.version += 1
    item.updated_by = actor
    item.updated_at = datetime.now(UTC)
    db.add(
        BOQV2AuditEvent(
            id=uuid4(), event_key=f"UPDATE_CATALOG_ITEM:{item.id}:{item.version}",
            project_id=request.project_id, actor=actor, command_type="UPDATE_CATALOG_ITEM",
            entity_type="CATALOG_ITEM", entity_id=item.id, before_reference=before,
            after_reference={"version": item.version, "status": item.status, "name": item.name},
            reason=request.reason.strip(),
        )
    )
    await db.flush()
    return await _item_response(db, item)


async def update_reference_price(
    db: AsyncSession, *, item_id: UUID, request: BOQV2ReferencePriceRequest, actor: str
) -> BOQV2CatalogItemResponse:
    await _project_exists(db, request.project_id)
    await acquire_project_budget_locks(db, [request.project_id])
    item = (
        await db.execute(select(BOQV2CatalogItem).where(BOQV2CatalogItem.id == item_id).with_for_update())
    ).scalar_one_or_none()
    if item is None:
        raise BOQDomainError("CATALOG_ITEM_NOT_FOUND", "Catalog item was not found")
    if item.version != request.expected_item_version:
        raise BOQDomainError("STALE_CATALOG_VERSION", "Catalog item changed; reload and retry")
    if request.source_observation_id:
        observation = (
            await db.execute(select(BOQV2PriceObservation).where(BOQV2PriceObservation.id == request.source_observation_id))
        ).scalar_one_or_none()
        if observation is None:
            raise BOQDomainError("PRICE_OBSERVATION_NOT_FOUND", "Reference source observation was not found")
    row = await _add_price_version(
        db, item=item, price_kind=request.price_kind, amount=request.amount,
        tax_basis=request.tax_basis, effective_date=request.effective_date,
        source_observation_id=request.source_observation_id,
        reason=request.reason, actor=actor,
    )
    item.version += 1
    item.updated_by = actor
    item.updated_at = datetime.now(UTC)
    await db.flush()
    db.add(
        BOQV2AuditEvent(
            id=uuid4(), event_key=f"UPDATE_REFERENCE_PRICE:{row.id}", project_id=request.project_id,
            actor=actor, command_type="UPDATE_REFERENCE_PRICE", entity_type="CATALOG_PRICE",
            entity_id=row.id,
            after_reference={"catalog_item_id": str(item.id), "kind": row.price_kind, "version": row.version},
            reason=request.reason.strip(),
        )
    )
    return await _item_response(db, item)


async def reuse_catalog_item(
    db: AsyncSession,
    *,
    item_id: UUID,
    revision_id: UUID,
    request: BOQV2CatalogReuseRequest,
    actor: str,
    idempotency_key: str,
):
    item = (await db.execute(select(BOQV2CatalogItem).where(BOQV2CatalogItem.id == item_id))).scalar_one_or_none()
    if item is None:
        raise BOQDomainError("CATALOG_ITEM_NOT_FOUND", "Catalog item was not found")
    if item.status != "ACTIVE":
        raise BOQDomainError("CATALOG_ITEM_ARCHIVED", "Archived catalog items require reactivation before reuse")
    revision = await load_boq_revision(db, revision_id)
    if revision.status != "DRAFT":
        raise BOQDomainError("IMMUTABLE_BOQ_REVISION", "Catalog reuse is allowed only in a draft revision")
    if revision.version != request.expected_revision_version:
        raise BOQDomainError("STALE_BOQ_VERSION", "The BOQ draft changed; reload and retry")
    parent_ids = {node.logical_id for node in revision.nodes if node.node_kind != "ITEM"}
    if request.parent_logical_id and request.parent_logical_id not in parent_ids:
        raise BOQDomainError("INVALID_REUSE_PARENT", "Catalog item parent must be a structural node in the draft")
    prices = {
        row.price_kind: row
        for row in (
            await db.execute(
                select(BOQV2CatalogPriceVersion).where(
                    BOQV2CatalogPriceVersion.catalog_item_id == item.id,
                    BOQV2CatalogPriceVersion.is_current.is_(True),
                )
            )
        ).scalars().all()
    }
    nodes: list[BOQV2ScopeNodeDraft] = []
    for node in revision.nodes:
        position = node.position
        if node.parent_logical_id == request.parent_logical_id and position >= request.position:
            position += 1
        nodes.append(
            BOQV2ScopeNodeDraft(
                id=node.id, logical_id=node.logical_id, parent_logical_id=node.parent_logical_id,
                node_kind=node.node_kind, inclusion_state=node.inclusion_state, position=position,
                item_code=node.item_code, catalog_item_id=node.catalog_item_id,
                catalog_item_version=node.catalog_item_version, source_logical_id=node.source_logical_id,
                description=node.description, specification=node.specification,
                quantity=Decimal(node.quantity) if node.quantity is not None else None,
                unit=node.unit,
                sell_material_unit_rate=(Decimal(node.sell_material_unit_rate) if node.sell_material_unit_rate is not None else None),
                sell_labor_unit_rate=(Decimal(node.sell_labor_unit_rate) if node.sell_labor_unit_rate is not None else None),
                components=[
                    BOQV2CostComponentDraft(
                        id=component.id, component_type=component.component_type,
                        quantity_basis=component.quantity_basis,
                        quantity=(Decimal(component.quantity) if component.quantity_basis == "OVERRIDDEN" else None),
                        unit=component.unit, specification=component.specification,
                        cost_state=component.cost_state,
                        unit_rate=Decimal(component.unit_rate) if component.unit_rate is not None else None,
                        explicit_zero_reason=component.explicit_zero_reason,
                    )
                    for component in node.components
                ],
            )
        )
    logical_id = uuid4()
    material_sell = prices.get("MATERIAL_SELL") if request.use_reference_prices else None
    labor_sell = prices.get("LABOR_SELL") if request.use_reference_prices else None
    material_cost = prices.get("MATERIAL_COST") if request.use_reference_prices else None
    labor_cost = prices.get("LABOR_COST") if request.use_reference_prices else None
    new_components = []
    for component_type, price in (("MATERIAL", material_cost), ("LABOR", labor_cost)):
        new_components.append(
            BOQV2CostComponentDraft(
                component_type=component_type, quantity_basis="INHERITED",
                unit=item.unit, specification=item.specification,
                cost_state="PRICED" if price else "UNKNOWN",
                unit_rate=Decimal(str(price.amount)) if price else None,
                explicit_zero_reason=("Catalog reference is explicitly zero" if price and price.amount == 0 else None),
            )
        )
    nodes.append(
        BOQV2ScopeNodeDraft(
            logical_id=logical_id, parent_logical_id=request.parent_logical_id,
            node_kind="ITEM", inclusion_state=request.inclusion_state,
            position=request.position, item_code=item.code, catalog_item_id=item.id,
            catalog_item_version=item.version, source_logical_id=logical_id,
            description=item.name, specification=item.specification,
            quantity=request.quantity, unit=item.unit,
            sell_material_unit_rate=Decimal(str(material_sell.amount)) if material_sell else None,
            sell_labor_unit_rate=Decimal(str(labor_sell.amount)) if labor_sell else None,
            components=new_components,
        )
    )
    return await save_boq_draft(
        db, revision_id=revision_id,
        request=BOQV2SaveDraftRequest(expected_version=revision.version, nodes=nodes, quotation=None),
        actor=actor, idempotency_key=idempotency_key,
    )
