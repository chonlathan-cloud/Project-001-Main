"""Phase 2 native BOQ draft persistence and server-authoritative totals."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boq import BOQItem, Project
from app.models.boq_v2 import (
    BOQV2Acceptance,
    BOQV2AuditEvent,
    BOQV2BaselineChangeOrder,
    BOQV2ChangeOrderDeduction,
    BOQV2CommandIdempotency,
    BOQV2CostComponent,
    BOQV2CostPlan,
    BOQV2Document,
    BOQV2ProjectBaseline,
    BOQV2ProjectBudgetSource,
    BOQV2Revision,
    BOQV2RevisionSnapshot,
    BOQV2ScopeNode,
)
from app.schemas.boq_v2_schema import (
    BOQV2CompletenessResponse,
    BOQV2CostComponentDraft,
    BOQV2CostComponentResponse,
    BOQV2CreateDocumentRequest,
    BOQV2PaymentScheduleResponse,
    BOQV2QuotationDraft,
    BOQV2QuotationListItem,
    BOQV2QuotationListResponse,
    BOQV2QuotationResponse,
    BOQV2ReuseSource,
    BOQV2RevisionResponse,
    BOQV2RevisionSummary,
    BOQV2SaveDraftRequest,
    BOQV2ScopeNodeDraft,
    BOQV2ScopeNodeResponse,
    BOQV2WorkspaceResponse,
)
from app.services.boq_calculation_service import (
    CALCULATION_VERSION,
    CostComponentInput,
    SellItemInput,
    calculate_boq,
    calculate_cost_component,
    extended_amount,
    money,
    allocate_payment_percentages,
    vat_amount,
    validate_quantity_or_rate,
)
from app.services.boq_composition_service import (
    create_default_composition,
    load_composition,
    replace_composition,
)
from app.services.boq_domain_service import (
    BOQDomainError,
    ScopeIdentity,
    acquire_project_budget_locks,
    assert_expected_version,
    assert_mutable_draft,
    canonical_request_hash,
    validate_scope_hierarchy,
)
from app.services.boq_numbering_service import next_document_number


ZERO_RATE = Decimal("0.0000")
ZERO_MONEY = Decimal("0.00")
COMPONENT_TYPES = ("MATERIAL", "LABOR")


def _clean_text(value: object | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _rate_string(value: object | None) -> str | None:
    if value is None:
        return None
    return f"{Decimal(str(value)):.4f}"


def _money_string(value: object | None) -> str:
    return f"{Decimal(str(value or 0)):.2f}"


def _timestamp(value: datetime | None) -> str:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _optional_timestamp(value: datetime | None) -> str | None:
    return _timestamp(value) if value is not None else None


def _quotation_draft_from_revision(revision: BOQV2Revision) -> BOQV2QuotationDraft:
    return BOQV2QuotationDraft.model_validate(
        {
            "title": revision.quotation_title,
            "customer_name": revision.customer_name,
            "customer_address": revision.customer_address,
            "customer_tax_id": revision.customer_tax_id,
            "customer_contact": revision.customer_contact,
            "quotation_date": revision.quotation_date,
            "valid_until": revision.valid_until,
            "currency": revision.currency,
            "vat_rate": revision.vat_rate,
            "discount_type": revision.discount_type,
            "discount_value": revision.discount_value,
            "payment_schedule": revision.payment_schedule or [],
            "commercial_terms": revision.commercial_terms or [],
            "document_pages": revision.document_pages or ["BOQ"],
        }
    )


def _apply_quotation_totals(
    revision: BOQV2Revision,
    quotation: BOQV2QuotationDraft,
    *,
    subtotal: Decimal,
    forecast_cost: Decimal | None,
) -> None:
    subtotal_value = money(subtotal)
    if quotation.discount_type == "NONE":
        discount_amount = ZERO_MONEY
    elif quotation.discount_type == "FIXED":
        discount_amount = money(quotation.discount_value)
    else:
        discount_amount = money(
            subtotal_value * quotation.discount_value / Decimal("100")
        )
    if discount_amount > subtotal_value:
        raise BOQDomainError(
            "INVALID_QUOTATION_DISCOUNT",
            "Quotation discount cannot exceed the sell subtotal",
        )
    net_sell = money(subtotal_value - discount_amount)
    vat = vat_amount(net_sell, quotation.vat_rate)
    grand_total = money(net_sell + vat)

    schedule = quotation.payment_schedule
    if schedule:
        percentages = [item.percentage for item in schedule]
        if all(value is not None for value in percentages):
            allocate_payment_percentages(grand_total, percentages)
        else:
            fixed_total = money(
                sum((item.fixed_amount or ZERO_MONEY for item in schedule), ZERO_MONEY)
            )
            if fixed_total != grand_total:
                raise BOQDomainError(
                    "INVALID_PAYMENT_SCHEDULE_TOTAL",
                    "Fixed payment schedule amounts must equal the quotation grand total",
                )

    revision.quotation_title = _clean_text(quotation.title)
    revision.customer_name = _clean_text(quotation.customer_name)
    revision.customer_address = _clean_text(quotation.customer_address)
    revision.customer_tax_id = _clean_text(quotation.customer_tax_id)
    revision.customer_contact = _clean_text(quotation.customer_contact)
    revision.quotation_date = quotation.quotation_date
    revision.valid_until = quotation.valid_until
    revision.currency = quotation.currency
    revision.vat_rate = quotation.vat_rate
    revision.discount_type = quotation.discount_type
    revision.discount_value = quotation.discount_value
    revision.subtotal = subtotal_value
    revision.discount_amount = discount_amount
    revision.net_sell_ex_vat = net_sell
    revision.vat_amount = vat
    revision.grand_total = grand_total
    revision.payment_schedule = [
        item.model_dump(mode="json") for item in quotation.payment_schedule
    ]
    revision.commercial_terms = [
        str(item).strip() for item in quotation.commercial_terms
    ]
    revision.document_pages = list(quotation.document_pages)
    revision.forecast_margin = (
        money(net_sell - forecast_cost) if forecast_cost is not None else None
    )


def _payment_schedule_response(
    revision: BOQV2Revision,
) -> list[BOQV2PaymentScheduleResponse]:
    schedule = list(revision.payment_schedule or [])
    if not schedule:
        return []
    percentages = [item.get("percentage") for item in schedule]
    if all(value is not None for value in percentages):
        amounts = allocate_payment_percentages(revision.grand_total, percentages)
    else:
        amounts = tuple(money(item.get("fixed_amount") or 0) for item in schedule)
    return [
        BOQV2PaymentScheduleResponse(
            label=str(item.get("label") or ""),
            percentage=(
                _rate_string(item.get("percentage"))
                if item.get("percentage") is not None
                else None
            ),
            fixed_amount=(
                _money_string(item.get("fixed_amount"))
                if item.get("fixed_amount") is not None
                else None
            ),
            amount=_money_string(amount),
        )
        for item, amount in zip(schedule, amounts, strict=True)
    ]


async def _project_or_error(db: AsyncSession, project_id: UUID) -> Project:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        raise BOQDomainError("PROJECT_NOT_FOUND", "Project does not exist")
    if project.system_key == "OPERATIONS":
        raise BOQDomainError(
            "BOQ_NOT_AVAILABLE",
            "Company Operations does not have a project BOQ",
        )
    return project


async def _revision_context(
    db: AsyncSession,
    revision_id: UUID,
    *,
    for_update: bool = False,
) -> tuple[BOQV2Revision, BOQV2Document, Project]:
    statement = (
        select(BOQV2Revision, BOQV2Document, Project)
        .join(BOQV2Document, BOQV2Document.id == BOQV2Revision.document_id)
        .join(Project, Project.id == BOQV2Revision.project_id)
        .where(BOQV2Revision.id == revision_id)
    )
    if for_update:
        statement = statement.with_for_update()
    row = (await db.execute(statement)).one_or_none()
    if row is None:
        raise BOQDomainError("BOQ_REVISION_NOT_FOUND", "BOQ revision does not exist")
    return row


async def _current_cost_plan(
    db: AsyncSession,
    revision_id: UUID,
    *,
    for_update: bool = False,
) -> BOQV2CostPlan | None:
    statement = (
        select(BOQV2CostPlan)
        .where(BOQV2CostPlan.scope_revision_id == revision_id)
        .order_by(BOQV2CostPlan.version.desc())
        .limit(1)
    )
    if for_update:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def _next_cost_plan_version(db: AsyncSession, project_id: UUID) -> int:
    current_max = (
        await db.execute(
            select(func.max(BOQV2CostPlan.version)).where(
                BOQV2CostPlan.project_id == project_id
            )
        )
    ).scalar_one_or_none()
    return int(current_max or 0) + 1


async def _replace_current_working_plan(
    db: AsyncSession,
    project_id: UUID,
) -> None:
    await db.execute(
        update(BOQV2CostPlan)
        .where(
            BOQV2CostPlan.project_id == project_id,
            BOQV2CostPlan.is_current.is_(True),
        )
        .values(is_current=False)
    )


async def _begin_command(
    db: AsyncSession,
    *,
    actor: str,
    project_id: UUID,
    command_type: str,
    idempotency_key: str,
    payload: object,
) -> tuple[BOQV2CommandIdempotency, UUID | None]:
    request_hash = canonical_request_hash(payload)
    existing = (
        await db.execute(
            select(BOQV2CommandIdempotency)
            .where(
                BOQV2CommandIdempotency.actor == actor,
                BOQV2CommandIdempotency.project_id == project_id,
                BOQV2CommandIdempotency.command_type == command_type,
                BOQV2CommandIdempotency.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.request_hash != request_hash:
            raise BOQDomainError(
                "IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used with a different request",
            )
        if existing.status == "COMPLETED" and existing.aggregate_id is not None:
            return existing, existing.aggregate_id
        raise BOQDomainError(
            "COMMAND_IN_PROGRESS",
            "The matching BOQ command has not completed",
        )

    command = BOQV2CommandIdempotency(
        id=uuid4(),
        actor=actor,
        project_id=project_id,
        command_type=command_type,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        status="STARTED",
    )
    db.add(command)
    await db.flush()
    return command, None


def _complete_command(
    command: BOQV2CommandIdempotency,
    *,
    revision_id: UUID,
    version: int,
) -> None:
    command.aggregate_id = revision_id
    command.response_reference = {
        "revision_id": str(revision_id),
        "version": version,
    }
    command.status = "COMPLETED"
    command.completed_at = datetime.now(UTC)


def _audit(
    db: AsyncSession,
    *,
    command: BOQV2CommandIdempotency,
    actor: str,
    project_id: UUID,
    command_type: str,
    entity_type: str,
    entity_id: UUID,
    before: dict[str, object] | None,
    after: dict[str, object],
) -> None:
    db.add(
        BOQV2AuditEvent(
            id=uuid4(),
            event_key=f"{command_type}:{command.id}",
            project_id=project_id,
            actor=actor,
            command_type=command_type,
            entity_type=entity_type,
            entity_id=entity_id,
            calculation_version=CALCULATION_VERSION,
            before_reference=before,
            after_reference=after,
        )
    )


async def load_boq_revision(
    db: AsyncSession,
    revision_id: UUID,
) -> BOQV2RevisionResponse:
    revision, document, project = await _revision_context(db, revision_id)
    plan = await _current_cost_plan(db, revision_id)
    issued_snapshot = (
        await db.execute(
            select(BOQV2RevisionSnapshot)
            .where(
                BOQV2RevisionSnapshot.revision_id == revision_id,
                BOQV2RevisionSnapshot.purpose == "ISSUE",
            )
            .order_by(BOQV2RevisionSnapshot.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    acceptance = (
        await db.execute(
            select(BOQV2Acceptance).where(
                BOQV2Acceptance.revision_id == revision_id
            )
        )
    ).scalar_one_or_none()
    nodes = list(
        (
            await db.execute(
                select(BOQV2ScopeNode).where(
                    BOQV2ScopeNode.revision_id == revision_id
                )
            )
        )
        .scalars()
        .all()
    )
    components: list[BOQV2CostComponent] = []
    if plan is not None:
        components = list(
            (
                await db.execute(
                    select(BOQV2CostComponent).where(
                        BOQV2CostComponent.cost_plan_id == plan.id
                    )
                )
            )
            .scalars()
            .all()
        )

    logical_by_row = {node.id: node.logical_id for node in nodes}
    components_by_node: dict[UUID, list[BOQV2CostComponent]] = {}
    for component in components:
        components_by_node.setdefault(component.scope_node_id, []).append(component)

    children_by_parent: dict[UUID | None, list[BOQV2ScopeNode]] = {}
    for node in nodes:
        children_by_parent.setdefault(node.parent_id, []).append(node)
    for siblings in children_by_parent.values():
        siblings.sort(key=lambda item: (item.position, str(item.id)))

    ordered: list[tuple[BOQV2ScopeNode, int, str]] = []
    visited: set[UUID] = set()

    def visit(parent_id: UUID | None, depth: int, prefix: str) -> None:
        for ordinal, node in enumerate(children_by_parent.get(parent_id, []), start=1):
            if node.id in visited:
                continue
            visited.add(node.id)
            display_path = f"{prefix}.{ordinal}" if prefix else str(ordinal)
            ordered.append((node, depth, display_path))
            visit(node.id, depth + 1, display_path)

    visit(None, 0, "")
    for node in sorted(nodes, key=lambda item: (item.position, str(item.id))):
        if node.id not in visited:
            ordered.append((node, 0, str(len(ordered) + 1)))

    node_by_id = {node.id: node for node in nodes}
    inclusion_cache: dict[UUID, bool] = {}

    def is_included(node: BOQV2ScopeNode) -> bool:
        cached = inclusion_cache.get(node.id)
        if cached is not None:
            return cached
        included = node.inclusion_state != "EXCLUDED"
        if included and node.parent_id is not None:
            parent = node_by_id.get(node.parent_id)
            included = parent is not None and is_included(parent)
        inclusion_cache[node.id] = included
        return included

    response_sell_totals: dict[UUID, Decimal] = {}

    def response_sell_total(node: BOQV2ScopeNode) -> Decimal:
        cached = response_sell_totals.get(node.id)
        if cached is not None:
            return cached
        if not is_included(node):
            total = ZERO_MONEY
        elif node.node_kind == "ITEM":
            total = money(node.sell_total)
        else:
            total = money(
                sum(
                    (response_sell_total(child) for child in children_by_parent.get(node.id, [])),
                    ZERO_MONEY,
                )
            )
        response_sell_totals[node.id] = total
        return total

    for node in nodes:
        response_sell_total(node)

    included_node_ids = {
        node.id
        for node in nodes
        if node.node_kind == "ITEM" and is_included(node)
    }
    missing_component_ids = sorted(
        (
            component.id
            for component in components
            if component.scope_node_id in included_node_ids
            and component.cost_state == "UNKNOWN"
        ),
        key=str,
    )
    document_sections, visual_pages, media_assets = await load_composition(
        db,
        revision_id=revision.id,
        legacy_document_pages=list(revision.document_pages or []),
    )

    response_nodes: list[BOQV2ScopeNodeResponse] = []
    for node, depth, display_path in ordered:
        response_components = [
            BOQV2CostComponentResponse(
                id=component.id,
                component_type=component.component_type,
                quantity_basis=component.quantity_basis,
                quantity=_rate_string(component.quantity) or "0.0000",
                unit=component.unit,
                specification=component.specification,
                basis_version=component.basis_version,
                cost_state=component.cost_state,
                unit_rate=_rate_string(component.unit_rate),
                total=(
                    None if component.total is None else _money_string(component.total)
                ),
                explicit_zero_reason=component.explicit_zero_reason,
            )
            for component in sorted(
                components_by_node.get(node.id, []),
                key=lambda item: COMPONENT_TYPES.index(item.component_type),
            )
        ]
        response_nodes.append(
            BOQV2ScopeNodeResponse(
                id=node.id,
                logical_id=node.logical_id,
                parent_logical_id=logical_by_row.get(node.parent_id),
                node_kind=node.node_kind,
                inclusion_state=node.inclusion_state,
                position=node.position,
                depth=depth,
                display_path=display_path,
                item_code=node.item_code,
                catalog_item_id=node.catalog_item_id,
                catalog_item_version=node.catalog_item_version,
                source_logical_id=node.source_logical_id,
                description=node.description,
                specification=node.specification,
                quantity=_rate_string(node.quantity),
                unit=node.unit,
                sell_material_unit_rate=_rate_string(node.sell_material_unit_rate),
                sell_labor_unit_rate=_rate_string(node.sell_labor_unit_rate),
                sell_total=_money_string(response_sell_totals[node.id]),
                components=response_components,
            )
        )

    return BOQV2RevisionResponse(
        project_id=project.id,
        project_name=project.name,
        document_id=document.id,
        document_number=document.document_number,
        revision_id=revision.id,
        predecessor_revision_id=revision.predecessor_revision_id,
        document_kind=document.document_kind,
        direction=document.direction,
        alternative_group_id=document.alternative_group_id,
        base_baseline_id=revision.base_baseline_id or document.base_baseline_id,
        base_baseline_version=(
            revision.base_baseline_version or document.base_baseline_version
        ),
        status=revision.status,
        revision_number=revision.revision_number,
        version=revision.version,
        calculation_version=revision.calculation_version,
        net_sell_ex_vat=_money_string(revision.net_sell_ex_vat),
        known_estimated_cost=_money_string(revision.known_estimated_cost),
        forecast_cost=(
            None if revision.forecast_cost is None else _money_string(revision.forecast_cost)
        ),
        forecast_margin=(
            None
            if revision.forecast_margin is None
            else _money_string(revision.forecast_margin)
        ),
        completeness=BOQV2CompletenessResponse(
            state=(
                "COMPLETE"
                if revision.required_cost_count == revision.priced_cost_count
                else "INCOMPLETE"
            ),
            required_count=revision.required_cost_count,
            priced_count=revision.priced_cost_count,
            missing_component_ids=missing_component_ids,
        ),
        quotation=BOQV2QuotationResponse(
            title=revision.quotation_title,
            customer_name=revision.customer_name,
            customer_address=revision.customer_address,
            customer_tax_id=revision.customer_tax_id,
            customer_contact=revision.customer_contact,
            quotation_date=revision.quotation_date,
            valid_until=revision.valid_until,
            currency=revision.currency,
            vat_rate=_rate_string(revision.vat_rate) or "0.0000",
            discount_type=revision.discount_type,
            discount_value=_rate_string(revision.discount_value) or "0.0000",
            subtotal=_money_string(revision.subtotal),
            discount_amount=_money_string(revision.discount_amount),
            net_sell_ex_vat=_money_string(revision.net_sell_ex_vat),
            vat_amount=_money_string(revision.vat_amount),
            grand_total=_money_string(revision.grand_total),
            payment_schedule=_payment_schedule_response(revision),
            commercial_terms=list(revision.commercial_terms or []),
            document_pages=list(revision.document_pages or []),
            document_sections=document_sections,
            visual_pages=visual_pages,
            media_assets=media_assets,
        ),
        issued_at=_optional_timestamp(revision.issued_at),
        issued_by=revision.issued_by,
        issued_snapshot_id=issued_snapshot.id if issued_snapshot else None,
        accepted_at=_optional_timestamp(acceptance.recorded_at if acceptance else None),
        accepted_by=acceptance.actor if acceptance else None,
        accepted_agreed_date=acceptance.agreed_date if acceptance else None,
        acceptance_evidence_reference=(
            acceptance.evidence_reference if acceptance else None
        ),
        nodes=response_nodes,
        created_at=_timestamp(revision.created_at),
        updated_at=_timestamp(revision.updated_at),
    )


async def load_boq_workspace(
    db: AsyncSession,
    project_id: UUID,
    *,
    can_edit: bool,
) -> BOQV2WorkspaceResponse:
    project = await _project_or_error(db, project_id)
    revision_rows = (
        await db.execute(
            select(BOQV2Revision, BOQV2Document)
            .join(BOQV2Document, BOQV2Document.id == BOQV2Revision.document_id)
            .where(BOQV2Revision.project_id == project_id)
            .order_by(BOQV2Revision.updated_at.desc(), BOQV2Revision.created_at.desc())
        )
    ).all()
    legacy_row_count = int(
        (
            await db.execute(
                select(func.count(BOQItem.id)).where(
                    BOQItem.project_id == project_id,
                    BOQItem.valid_to.is_(None),
                )
            )
        ).scalar_one()
    )
    source = (
        await db.execute(
            select(BOQV2ProjectBudgetSource).where(
                BOQV2ProjectBudgetSource.project_id == project_id
            )
        )
    ).scalar_one_or_none()
    active_baseline = (
        await db.execute(
            select(BOQV2ProjectBaseline).where(
                BOQV2ProjectBaseline.project_id == project_id,
                BOQV2ProjectBaseline.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    active_change_order_ids: list[UUID] = []
    if active_baseline is not None:
        active_change_order_ids = list(
            (
                await db.execute(
                    select(BOQV2BaselineChangeOrder.revision_id)
                    .where(
                        BOQV2BaselineChangeOrder.baseline_id == active_baseline.id
                    )
                    .order_by(BOQV2BaselineChangeOrder.position)
                )
            ).scalars()
        )

    reuse_rows = (
        await db.execute(
            select(BOQV2Revision, BOQV2Document, Project)
            .join(BOQV2Document, BOQV2Document.id == BOQV2Revision.document_id)
            .join(Project, Project.id == BOQV2Revision.project_id)
            .where(
                BOQV2Document.document_kind == "MAIN",
                or_(Project.system_key.is_(None), Project.system_key != "OPERATIONS"),
            )
            .order_by(BOQV2Revision.updated_at.desc(), BOQV2Revision.created_at.desc())
            .limit(100)
        )
    ).all()

    return BOQV2WorkspaceResponse(
        project_id=project.id,
        project_name=project.name,
        rollout_enabled=True,
        can_edit=can_edit,
        active_source_kind=source.source_kind if source is not None else "LEGACY",
        legacy_available=legacy_row_count > 0,
        legacy_row_count=legacy_row_count,
        active_baseline_id=active_baseline.id if active_baseline else None,
        active_baseline_version=active_baseline.version if active_baseline else None,
        active_main_revision_id=(
            active_baseline.main_revision_id if active_baseline else None
        ),
        active_change_order_revision_ids=active_change_order_ids,
        revisions=[
            BOQV2RevisionSummary(
                revision_id=revision.id,
                document_id=document.id,
                document_number=document.document_number,
                document_kind=document.document_kind,
                direction=document.direction,
                alternative_group_id=document.alternative_group_id,
                revision_number=revision.revision_number,
                status=revision.status,
                version=revision.version,
                net_sell_ex_vat=_money_string(revision.net_sell_ex_vat),
                completeness_state=(
                    "COMPLETE"
                    if revision.required_cost_count == revision.priced_cost_count
                    else "INCOMPLETE"
                ),
                updated_at=_timestamp(revision.updated_at),
            )
            for revision, document in revision_rows
        ],
        reuse_sources=[
            BOQV2ReuseSource(
                project_id=source_project.id,
                project_name=source_project.name,
                revision_id=revision.id,
                document_id=document.id,
                document_number=document.document_number,
                revision_number=revision.revision_number,
                status=revision.status,
                net_sell_ex_vat=_money_string(revision.net_sell_ex_vat),
                updated_at=_timestamp(revision.updated_at),
            )
            for revision, document, source_project in reuse_rows
        ],
    )


async def list_quotations(
    db: AsyncSession,
    *,
    search: str | None,
    status: str | None,
    document_kind: str | None,
    date_from: object | None,
    date_to: object | None,
    limit: int,
    offset: int,
) -> BOQV2QuotationListResponse:
    latest = (
        select(
            BOQV2Revision.document_id.label("document_id"),
            func.max(BOQV2Revision.revision_number).label("revision_number"),
        )
        .group_by(BOQV2Revision.document_id)
        .subquery()
    )
    statement = (
        select(BOQV2Document, BOQV2Revision, Project)
        .join(BOQV2Revision, BOQV2Revision.document_id == BOQV2Document.id)
        .join(
            latest,
            (latest.c.document_id == BOQV2Revision.document_id)
            & (latest.c.revision_number == BOQV2Revision.revision_number),
        )
        .join(Project, Project.id == BOQV2Document.project_id)
    )
    if cleaned := str(search or "").strip():
        pattern = f"%{cleaned}%"
        statement = statement.where(
            or_(
                BOQV2Document.document_number.ilike(pattern),
                Project.name.ilike(pattern),
                BOQV2Revision.customer_name.ilike(pattern),
                BOQV2Revision.quotation_title.ilike(pattern),
            )
        )
    if status:
        statement = statement.where(BOQV2Revision.status == status)
    if document_kind:
        statement = statement.where(BOQV2Document.document_kind == document_kind)
    if date_from is not None:
        statement = statement.where(BOQV2Revision.quotation_date >= date_from)
    if date_to is not None:
        statement = statement.where(BOQV2Revision.quotation_date <= date_to)

    total = int(
        (
            await db.execute(
                select(func.count()).select_from(statement.order_by(None).subquery())
            )
        ).scalar_one()
    )
    rows = (
        await db.execute(
            statement.order_by(
                BOQV2Revision.updated_at.desc(),
                BOQV2Document.document_number.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return BOQV2QuotationListResponse(
        items=[
            BOQV2QuotationListItem(
                document_id=document.id,
                document_number=document.document_number,
                document_kind=document.document_kind,
                direction=document.direction,
                project_id=project.id,
                project_name=project.name,
                revision_id=revision.id,
                revision_number=revision.revision_number,
                status=revision.status,
                version=revision.version,
                customer_name=revision.customer_name,
                quotation_title=revision.quotation_title,
                quotation_date=revision.quotation_date,
                valid_until=revision.valid_until,
                grand_total=_money_string(revision.grand_total),
                updated_at=_timestamp(revision.updated_at),
            )
            for document, revision, project in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


async def create_boq_document(
    db: AsyncSession,
    *,
    project_id: UUID,
    request: BOQV2CreateDocumentRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2RevisionResponse:
    await acquire_project_budget_locks(db, [project_id])
    project = await _project_or_error(db, project_id)
    command, prior_revision_id = await _begin_command(
        db,
        actor=actor,
        project_id=project_id,
        command_type="CREATE_DRAFT",
        idempotency_key=idempotency_key,
        payload={"project_id": str(project_id), **request.model_dump(mode="json")},
    )
    if prior_revision_id is not None:
        return await load_boq_revision(db, prior_revision_id)

    await _replace_current_working_plan(db, project.id)
    cost_plan_version = await _next_cost_plan_version(db, project.id)
    document_number = await next_document_number(db, document_kind="MAIN")

    document = BOQV2Document(
        id=uuid4(),
        project_id=project.id,
        document_number=document_number,
        document_kind="MAIN",
        revision_counter=1,
        created_by=actor,
    )
    revision = BOQV2Revision(
        id=uuid4(),
        document_id=document.id,
        project_id=project.id,
        revision_number=1,
        status="DRAFT",
        version=1,
        calculation_version=CALCULATION_VERSION,
        currency="THB",
        vat_rate=project.vat_percent or Decimal("7.0000"),
        discount_type="NONE",
        discount_value=ZERO_RATE,
        subtotal=ZERO_MONEY,
        discount_amount=ZERO_MONEY,
        net_sell_ex_vat=ZERO_MONEY,
        vat_amount=ZERO_MONEY,
        grand_total=ZERO_MONEY,
        payment_schedule=[],
        commercial_terms=[],
        document_pages=["BOQ", "PAYMENT_TERMS", "COMMERCIAL_TERMS"],
        known_estimated_cost=ZERO_MONEY,
        forecast_cost=ZERO_MONEY,
        forecast_margin=ZERO_MONEY,
        required_cost_count=0,
        priced_cost_count=0,
        created_by=actor,
    )
    plan = BOQV2CostPlan(
        id=uuid4(),
        project_id=project.id,
        scope_revision_id=revision.id,
        version=cost_plan_version,
        status="WORKING",
        is_current=True,
        completeness_state="COMPLETE",
        required_count=0,
        priced_count=0,
        forecast_cost=ZERO_MONEY,
        calculation_version=CALCULATION_VERSION,
        created_by=actor,
    )
    db.add(document)
    await db.flush()
    db.add(revision)
    await db.flush()
    await create_default_composition(db, revision=revision)
    db.add(plan)
    _complete_command(command, revision_id=revision.id, version=revision.version)
    _audit(
        db,
        command=command,
        actor=actor,
        project_id=project.id,
        command_type="CREATE_DRAFT",
        entity_type="BOQ_REVISION",
        entity_id=revision.id,
        before=None,
        after={"status": "DRAFT", "version": 1, "node_count": 0},
    )
    await db.flush()
    return await load_boq_revision(db, revision.id)


def _default_component(component_type: str) -> BOQV2CostComponentDraft:
    return BOQV2CostComponentDraft(
        component_type=component_type,
        quantity_basis="INHERITED",
        cost_state="UNKNOWN",
    )


def _component_input_by_type(
    draft: BOQV2ScopeNodeDraft,
) -> dict[str, BOQV2CostComponentDraft]:
    return {item.component_type: item for item in draft.components}


async def save_boq_draft(
    db: AsyncSession,
    *,
    revision_id: UUID,
    request: BOQV2SaveDraftRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2RevisionResponse:
    initial_revision, _, _ = await _revision_context(db, revision_id)
    await acquire_project_budget_locks(db, [initial_revision.project_id])
    revision, document, _ = await _revision_context(db, revision_id, for_update=True)
    command, prior_revision_id = await _begin_command(
        db,
        actor=actor,
        project_id=revision.project_id,
        command_type="SAVE_DRAFT",
        idempotency_key=idempotency_key,
        payload={"revision_id": str(revision_id), **request.model_dump(mode="json")},
    )
    if prior_revision_id is not None:
        return await load_boq_revision(db, prior_revision_id)

    assert_mutable_draft(revision.status)
    assert_expected_version(current=revision.version, expected=request.expected_version)
    if document.document_kind == "CHANGE_ORDER" and document.direction == "DEDUCT":
        deductions = list(
            (
                await db.execute(
                    select(BOQV2ChangeOrderDeduction).where(
                        BOQV2ChangeOrderDeduction.revision_id == revision.id
                    )
                )
            )
            .scalars()
            .all()
        )
        deduction_by_logical = {item.target_logical_id: item for item in deductions}
        draft_items = [item for item in request.nodes if item.node_kind == "ITEM"]
        if {item.logical_id for item in draft_items} != set(deduction_by_logical):
            raise BOQDomainError(
                "IMMUTABLE_DEDUCTION_SCOPE",
                "DEDUCT scope membership is fixed; revise the change order instead",
            )
        for item in draft_items:
            deduction = deduction_by_logical[item.logical_id]
            quantity = Decimal(str(item.quantity or 0))
            rate = Decimal(str(item.sell_material_unit_rate or 0)) + Decimal(
                str(item.sell_labor_unit_rate or 0)
            )
            if quantity != Decimal(deduction.quantity) or rate != Decimal(
                deduction.unit_rate
            ):
                raise BOQDomainError(
                    "IMMUTABLE_DEDUCTION_SCOPE",
                    "DEDUCT quantity and sell rate are frozen from the accepted target",
                )
    plan = await _current_cost_plan(db, revision_id, for_update=True)
    if plan is None:
        await _replace_current_working_plan(db, revision.project_id)
        cost_plan_version = await _next_cost_plan_version(db, revision.project_id)
        plan = BOQV2CostPlan(
            id=uuid4(),
            project_id=revision.project_id,
            scope_revision_id=revision.id,
            version=cost_plan_version,
            status="WORKING",
            is_current=True,
            completeness_state="INCOMPLETE",
            required_count=0,
            priced_count=0,
            calculation_version=CALCULATION_VERSION,
            created_by=actor,
        )
        db.add(plan)
        await db.flush()

    existing_nodes = list(
        (
            await db.execute(
                select(BOQV2ScopeNode).where(
                    BOQV2ScopeNode.revision_id == revision_id
                )
            )
        )
        .scalars()
        .all()
    )
    existing_by_id = {node.id: node for node in existing_nodes}
    existing_components = list(
        (
            await db.execute(
                select(BOQV2CostComponent).where(
                    BOQV2CostComponent.cost_plan_id == plan.id
                )
            )
        )
        .scalars()
        .all()
    )
    existing_component_by_key = {
        (item.scope_node_id, item.component_type): item
        for item in existing_components
    }
    existing_component_by_id = {item.id: item for item in existing_components}

    row_id_by_logical: dict[UUID, UUID] = {}
    for draft in request.nodes:
        if draft.id is not None:
            existing = existing_by_id.get(draft.id)
            if existing is None or existing.logical_id != draft.logical_id:
                raise BOQDomainError(
                    "CROSS_REVISION_SCOPE_NODE",
                    "Scope row ID does not belong to this revision and logical ID",
                )
            row_id_by_logical[draft.logical_id] = draft.id
        else:
            row_id_by_logical[draft.logical_id] = uuid4()

    identities: list[ScopeIdentity] = []
    for draft in request.nodes:
        parent_row_id = None
        if draft.parent_logical_id is not None:
            parent_row_id = row_id_by_logical.get(draft.parent_logical_id)
            if parent_row_id is None:
                raise BOQDomainError(
                    "ORPHAN_SCOPE_NODE",
                    "Parent logical ID is not present in the saved revision",
                )
        identities.append(
            ScopeIdentity(
                row_id=row_id_by_logical[draft.logical_id],
                logical_id=draft.logical_id,
                project_id=revision.project_id,
                revision_id=revision.id,
                parent_row_id=parent_row_id,
                node_kind=draft.node_kind,
                position=draft.position,
            )
        )
    validate_scope_hierarchy(identities)

    for draft in request.nodes:
        if draft.id is None:
            continue
        existing = existing_by_id[draft.id]
        if (
            existing.node_kind == "ITEM"
            and draft.node_kind != "ITEM"
            and not draft.confirm_financial_discard
        ):
            raise BOQDomainError(
                "FINANCIAL_DISCARD_CONFIRMATION_REQUIRED",
                "Changing an item to a structural node requires explicit confirmation",
            )

    for offset, node in enumerate(existing_nodes):
        node.parent_id = None
        node.position = 1_000_000 + offset
    if existing_nodes:
        await db.flush()

    saved_by_logical: dict[UUID, BOQV2ScopeNode] = {}
    desired_row_ids = set(row_id_by_logical.values())
    for draft in request.nodes:
        row_id = row_id_by_logical[draft.logical_id]
        node = existing_by_id.get(row_id)
        if node is None:
            node = BOQV2ScopeNode(
                id=row_id,
                logical_id=draft.logical_id,
                revision_id=revision.id,
                project_id=revision.project_id,
            )
            db.add(node)
        node.parent_id = (
            row_id_by_logical.get(draft.parent_logical_id)
            if draft.parent_logical_id is not None
            else None
        )
        node.node_kind = draft.node_kind
        node.inclusion_state = draft.inclusion_state
        node.position = draft.position
        node.item_code = _clean_text(draft.item_code)
        node.catalog_item_id = draft.catalog_item_id
        node.catalog_item_version = draft.catalog_item_version
        node.source_logical_id = draft.source_logical_id
        node.description = _clean_text(draft.description)
        node.specification = _clean_text(draft.specification)
        if draft.node_kind == "ITEM":
            node.quantity = draft.quantity
            node.unit = _clean_text(draft.unit)
            node.sell_material_unit_rate = draft.sell_material_unit_rate
            node.sell_labor_unit_rate = draft.sell_labor_unit_rate
        else:
            node.quantity = None
            node.unit = None
            node.sell_material_unit_rate = None
            node.sell_labor_unit_rate = None
            node.sell_total = ZERO_MONEY
        node.updated_at = func.now()
        saved_by_logical[draft.logical_id] = node

    deleted_node_ids = set(existing_by_id) - desired_row_ids
    if deleted_node_ids:
        await db.execute(
            delete(BOQV2CostComponent).where(
                BOQV2CostComponent.scope_node_id.in_(deleted_node_ids)
            )
        )
        await db.execute(
            delete(BOQV2ScopeNode).where(BOQV2ScopeNode.id.in_(deleted_node_ids))
        )
    await db.flush()

    draft_by_logical = {draft.logical_id: draft for draft in request.nodes}

    def included_in_scope(draft: BOQV2ScopeNodeDraft) -> bool:
        current: BOQV2ScopeNodeDraft | None = draft
        while current is not None:
            if current.inclusion_state == "EXCLUDED":
                return False
            current = (
                draft_by_logical.get(current.parent_logical_id)
                if current.parent_logical_id is not None
                else None
            )
        return True

    sell_inputs: list[SellItemInput] = []
    cost_inputs: list[CostComponentInput] = []
    desired_component_ids: set[UUID] = set()
    for draft in request.nodes:
        node = saved_by_logical[draft.logical_id]
        if draft.node_kind != "ITEM":
            structural_component_ids = {
                item.id
                for item in existing_components
                if item.scope_node_id == node.id
            }
            if structural_component_ids:
                await db.execute(
                    delete(BOQV2CostComponent).where(
                        BOQV2CostComponent.id.in_(structural_component_ids)
                    )
                )
            continue

        quantity = validate_quantity_or_rate(
            draft.quantity if draft.quantity is not None else ZERO_RATE,
            label="scope quantity",
        )
        material_rate = validate_quantity_or_rate(
            draft.sell_material_unit_rate
            if draft.sell_material_unit_rate is not None
            else ZERO_RATE,
            label="sell material unit rate",
        )
        labor_rate = validate_quantity_or_rate(
            draft.sell_labor_unit_rate
            if draft.sell_labor_unit_rate is not None
            else ZERO_RATE,
            label="sell labor unit rate",
        )
        included = included_in_scope(draft)
        node.sell_total = (
            extended_amount(quantity, material_rate)
            + extended_amount(quantity, labor_rate)
            if included
            else ZERO_MONEY
        )
        sell_inputs.append(
            SellItemInput(
                item_id=node.id,
                quantity=quantity,
                material_unit_rate=material_rate,
                labor_unit_rate=labor_rate,
                included=included,
            )
        )

        component_inputs = _component_input_by_type(draft)
        for component_type in COMPONENT_TYPES:
            current = existing_component_by_key.get((node.id, component_type))
            provided = component_inputs.get(component_type)
            component_draft = provided or (
                BOQV2CostComponentDraft(
                    id=current.id,
                    component_type=current.component_type,
                    quantity_basis=current.quantity_basis,
                    quantity=(current.quantity if current.quantity_basis == "OVERRIDDEN" else None),
                    unit=current.unit,
                    specification=current.specification,
                    cost_state=current.cost_state,
                    unit_rate=current.unit_rate,
                    explicit_zero_reason=current.explicit_zero_reason,
                )
                if current is not None
                else _default_component(component_type)
            )
            if provided is not None and provided.id is not None:
                identified = existing_component_by_id.get(provided.id)
                if (
                    identified is None
                    or identified.scope_node_id != node.id
                    or identified.component_type != component_type
                ):
                    raise BOQDomainError(
                        "CROSS_REVISION_COST_COMPONENT",
                        "Cost component ID does not belong to this revision item",
                    )

            component = current
            if component is None:
                component = BOQV2CostComponent(
                    id=uuid4(),
                    cost_plan_id=plan.id,
                    scope_node_id=node.id,
                    component_type=component_type,
                )
                db.add(component)
            desired_component_ids.add(component.id)
            previous_basis = (
                component.quantity,
                component.unit,
                component.specification,
                component.quantity_basis,
            ) if current is not None else None
            component.quantity_basis = component_draft.quantity_basis
            component.quantity = (
                quantity
                if component_draft.quantity_basis == "INHERITED"
                else validate_quantity_or_rate(
                    component_draft.quantity,
                    label="overridden component quantity",
                )
            )
            component.unit = (
                _clean_text(component_draft.unit)
                if component_draft.quantity_basis == "OVERRIDDEN"
                else node.unit
            )
            component.specification = (
                _clean_text(component_draft.specification)
                if component_draft.quantity_basis == "OVERRIDDEN"
                else node.specification
            )
            next_basis = (
                component.quantity,
                component.unit,
                component.specification,
                component.quantity_basis,
            )
            if previous_basis is not None and previous_basis != next_basis:
                component.basis_version += 1
            component.cost_state = component_draft.cost_state
            component.unit_rate = component_draft.unit_rate
            component.explicit_zero_reason = _clean_text(
                component_draft.explicit_zero_reason
            )
            component_result = calculate_cost_component(
                CostComponentInput(
                    component_id=component.id,
                    component_type=component_type,
                    state=component.cost_state,
                    quantity=component.quantity,
                    unit_rate=component.unit_rate,
                    explicit_zero_reason=component.explicit_zero_reason,
                )
            )
            component.total = component_result.total
            component.updated_at = func.now()
            if included:
                cost_inputs.append(
                    CostComponentInput(
                        component_id=component.id,
                        component_type=component_type,
                        state=component.cost_state,
                        quantity=component.quantity,
                        unit_rate=component.unit_rate,
                        explicit_zero_reason=component.explicit_zero_reason,
                    )
                )

    obsolete_component_ids = {
        item.id for item in existing_components
    } - desired_component_ids
    if obsolete_component_ids:
        await db.execute(
            delete(BOQV2CostComponent).where(
                BOQV2CostComponent.id.in_(obsolete_component_ids)
            )
        )

    result = calculate_boq(sell_inputs, cost_inputs)
    before = {
        "version": revision.version,
        "net_sell_ex_vat": _money_string(revision.net_sell_ex_vat),
        "required_cost_count": revision.required_cost_count,
        "priced_cost_count": revision.priced_cost_count,
    }
    revision.version += 1
    revision.calculation_version = result.calculation_version
    quotation = request.quotation or _quotation_draft_from_revision(revision)
    _apply_quotation_totals(
        revision,
        quotation,
        subtotal=result.net_sell_ex_vat,
        forecast_cost=result.forecast_cost,
    )
    if request.quotation is not None:
        await replace_composition(
            db,
            revision=revision,
            quotation=request.quotation,
            valid_scope_logical_ids=set(saved_by_logical),
        )
    revision.known_estimated_cost = result.known_estimated_cost
    revision.forecast_cost = result.forecast_cost
    revision.required_cost_count = result.required_count
    revision.priced_cost_count = result.priced_count
    revision.updated_at = func.now()
    plan.completeness_state = result.completeness_state
    plan.required_count = result.required_count
    plan.priced_count = result.priced_count
    plan.forecast_cost = result.forecast_cost
    plan.calculation_version = result.calculation_version

    after = {
        "version": revision.version,
        "node_count": len(request.nodes),
        "net_sell_ex_vat": _money_string(revision.net_sell_ex_vat),
        "required_cost_count": result.required_count,
        "priced_cost_count": result.priced_count,
    }
    _complete_command(command, revision_id=revision.id, version=revision.version)
    _audit(
        db,
        command=command,
        actor=actor,
        project_id=revision.project_id,
        command_type="SAVE_DRAFT",
        entity_type="BOQ_REVISION",
        entity_id=revision.id,
        before=before,
        after=after,
    )
    await db.flush()
    return await load_boq_revision(db, revision.id)


async def copy_boq_revision(
    db: AsyncSession,
    *,
    target_project_id: UUID,
    source_revision_id: UUID,
    actor: str,
    idempotency_key: str,
) -> BOQV2RevisionResponse:
    source_revision, source_document, _ = await _revision_context(
        db, source_revision_id
    )
    if source_document.document_kind != "MAIN":
        raise BOQDomainError(
            "PHASE_2_MAIN_ONLY",
            "Phase 2 can copy only a MAIN BOQ revision",
        )
    await acquire_project_budget_locks(
        db, [source_revision.project_id, target_project_id]
    )
    target_project = await _project_or_error(db, target_project_id)
    command, prior_revision_id = await _begin_command(
        db,
        actor=actor,
        project_id=target_project_id,
        command_type="COPY_DRAFT",
        idempotency_key=idempotency_key,
        payload={
            "target_project_id": str(target_project_id),
            "source_revision_id": str(source_revision_id),
        },
    )
    if prior_revision_id is not None:
        return await load_boq_revision(db, prior_revision_id)

    await _replace_current_working_plan(db, target_project.id)
    cost_plan_version = await _next_cost_plan_version(db, target_project.id)
    document_number = await next_document_number(db, document_kind="MAIN")

    source_nodes = list(
        (
            await db.execute(
                select(BOQV2ScopeNode).where(
                    BOQV2ScopeNode.revision_id == source_revision_id
                )
            )
        )
        .scalars()
        .all()
    )
    source_plan = await _current_cost_plan(db, source_revision_id)
    source_components: list[BOQV2CostComponent] = []
    if source_plan is not None:
        source_components = list(
            (
                await db.execute(
                    select(BOQV2CostComponent).where(
                        BOQV2CostComponent.cost_plan_id == source_plan.id
                    )
                )
            )
            .scalars()
            .all()
        )

    document = BOQV2Document(
        id=uuid4(),
        project_id=target_project.id,
        document_number=document_number,
        document_kind="MAIN",
        revision_counter=1,
        created_by=actor,
    )
    revision = BOQV2Revision(
        id=uuid4(),
        document_id=document.id,
        project_id=target_project.id,
        predecessor_revision_id=source_revision.id,
        revision_number=1,
        status="DRAFT",
        version=1,
        calculation_version=source_revision.calculation_version,
        quotation_title=source_revision.quotation_title,
        customer_name=source_revision.customer_name,
        customer_address=source_revision.customer_address,
        customer_tax_id=source_revision.customer_tax_id,
        customer_contact=source_revision.customer_contact,
        quotation_date=source_revision.quotation_date,
        valid_until=source_revision.valid_until,
        currency=source_revision.currency,
        vat_rate=source_revision.vat_rate,
        discount_type=source_revision.discount_type,
        discount_value=source_revision.discount_value,
        subtotal=source_revision.subtotal,
        discount_amount=source_revision.discount_amount,
        net_sell_ex_vat=source_revision.net_sell_ex_vat,
        vat_amount=source_revision.vat_amount,
        grand_total=source_revision.grand_total,
        payment_schedule=list(source_revision.payment_schedule or []),
        commercial_terms=list(source_revision.commercial_terms or []),
        document_pages=list(source_revision.document_pages or []),
        known_estimated_cost=source_revision.known_estimated_cost,
        forecast_cost=source_revision.forecast_cost,
        forecast_margin=source_revision.forecast_margin,
        required_cost_count=source_revision.required_cost_count,
        priced_cost_count=source_revision.priced_cost_count,
        created_by=actor,
    )
    plan = BOQV2CostPlan(
        id=uuid4(),
        project_id=target_project.id,
        scope_revision_id=revision.id,
        version=cost_plan_version,
        status="WORKING",
        is_current=True,
        completeness_state=(
            source_plan.completeness_state if source_plan else "COMPLETE"
        ),
        required_count=source_revision.required_cost_count,
        priced_count=source_revision.priced_cost_count,
        original_estimated_cost=None,
        agreed_cost=None,
        forecast_cost=source_revision.forecast_cost,
        calculation_version=source_revision.calculation_version,
        created_by=actor,
    )
    db.add(document)
    await db.flush()
    db.add(revision)
    await db.flush()
    await create_default_composition(db, revision=revision)
    db.add(plan)
    await db.flush()

    row_id_map = {node.id: uuid4() for node in source_nodes}
    for node in source_nodes:
        db.add(
            BOQV2ScopeNode(
                id=row_id_map[node.id],
                logical_id=node.logical_id,
                revision_id=revision.id,
                project_id=target_project.id,
                parent_id=row_id_map.get(node.parent_id),
                node_kind=node.node_kind,
                inclusion_state=node.inclusion_state,
                position=node.position,
                item_code=node.item_code,
                catalog_item_id=node.catalog_item_id,
                catalog_item_version=node.catalog_item_version,
                source_logical_id=node.source_logical_id or node.logical_id,
                description=node.description,
                specification=node.specification,
                quantity=node.quantity,
                unit=node.unit,
                sell_material_unit_rate=node.sell_material_unit_rate,
                sell_labor_unit_rate=node.sell_labor_unit_rate,
                sell_total=node.sell_total,
            )
        )
    await db.flush()
    for component in source_components:
        target_node_id = row_id_map.get(component.scope_node_id)
        if target_node_id is None:
            continue
        db.add(
            BOQV2CostComponent(
                id=uuid4(),
                cost_plan_id=plan.id,
                scope_node_id=target_node_id,
                component_type=component.component_type,
                quantity_basis=component.quantity_basis,
                quantity=component.quantity,
                unit=component.unit,
                specification=component.specification,
                basis_version=component.basis_version,
                cost_state=component.cost_state,
                unit_rate=component.unit_rate,
                total=component.total,
                explicit_zero_reason=component.explicit_zero_reason,
            )
        )

    _complete_command(command, revision_id=revision.id, version=revision.version)
    _audit(
        db,
        command=command,
        actor=actor,
        project_id=target_project.id,
        command_type="COPY_DRAFT",
        entity_type="BOQ_REVISION",
        entity_id=revision.id,
        before={"source_revision_id": str(source_revision.id)},
        after={
            "status": "DRAFT",
            "version": 1,
            "node_count": len(source_nodes),
        },
    )
    await db.flush()
    return await load_boq_revision(db, revision.id)
