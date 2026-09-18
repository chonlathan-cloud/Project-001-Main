"""Phase 4 vendor offers, selections, and versioned cost-plan publication."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boq import Project
from app.models.boq_v2 import (
    BOQV2AuditEvent,
    BOQV2BaselineChangeOrder,
    BOQV2CostComponent,
    BOQV2CostPlan,
    BOQV2CostSelection,
    BOQV2PriceObservation,
    BOQV2ProjectBaseline,
    BOQV2ProjectBudgetSource,
    BOQV2Revision,
    BOQV2RevisionSnapshot,
    BOQV2ScopeNode,
    BOQV2Vendor,
    BOQV2VendorOffer,
    BOQV2VendorOfferLine,
)
from app.schemas.boq_cost_schema import (
    BOQV2CostEstimateUpdateRequest,
    BOQV2CostComponentResponse,
    BOQV2CostPlanResponse,
    BOQV2CostPublishRequest,
    BOQV2CostPublishResponse,
    BOQV2OfferCreateRequest,
    BOQV2OfferLineResponse,
    BOQV2OfferResponse,
    BOQV2SelectionRequest,
    BOQV2SelectionResponse,
    BOQV2VendorCreateRequest,
    BOQV2VendorResponse,
)
from app.services.boq_calculation_service import extended_amount, money
from app.services.boq_document_service import _begin_command, _complete_command
from app.services.boq_domain_service import BOQDomainError, acquire_project_budget_locks
from app.services.project_budget_service import lock_project_budget_state


ZERO_MONEY = Decimal("0.00")
ZERO_RATE = Decimal("0.0000")


def _clean(value: object | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _timestamp(value: datetime | None) -> str:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _rate(value: object | None) -> str | None:
    return None if value is None else f"{Decimal(str(value)):.4f}"


def _amount(value: object | None) -> str | None:
    return None if value is None else f"{Decimal(str(value)):.2f}"


def _normalized_text(value: object | None) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _basis_fingerprint(component: BOQV2CostComponent) -> str:
    payload = {
        "quantity": _rate(component.quantity),
        "unit": _normalized_text(component.unit),
        "specification": _normalized_text(component.specification),
        "basis_version": component.basis_version,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _comparison_state(component: BOQV2CostComponent, unit: str | None, specification: str | None) -> str:
    unit_matches = _normalized_text(component.unit) == _normalized_text(unit)
    spec_matches = _normalized_text(component.specification) == _normalized_text(specification)
    if unit_matches and spec_matches:
        return "EQUIVALENT"
    if not unit_matches and not spec_matches:
        return "UNIT_AND_SPEC_MISMATCH"
    return "UNIT_MISMATCH" if not unit_matches else "SPEC_MISMATCH"


def _coverage(required: Decimal, offered: Decimal) -> str:
    if offered == required:
        return "FULL"
    return "PARTIAL" if offered < required else "EXCESS"


def _normalize_ex_vat(
    *, total: Decimal, tax_basis: str, tax_rate: Decimal | None
) -> Decimal | None:
    if tax_basis in {"EXCLUSIVE_VAT", "NO_VAT"}:
        return money(total)
    if tax_basis == "INCLUSIVE_VAT" and tax_rate is not None:
        divisor = Decimal("1") + Decimal(str(tax_rate)) / Decimal("100")
        if divisor > 0:
            return money(total / divisor)
    return None


async def _project(db: AsyncSession, project_id: UUID) -> Project:
    row = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if row is None:
        raise BOQDomainError("PROJECT_NOT_FOUND", "Project was not found")
    return row


async def _active_baseline(
    db: AsyncSession, project_id: UUID, *, for_update: bool = False
) -> BOQV2ProjectBaseline:
    statement = select(BOQV2ProjectBaseline).where(
        BOQV2ProjectBaseline.project_id == project_id,
        BOQV2ProjectBaseline.is_active.is_(True),
    )
    if for_update:
        statement = statement.with_for_update()
    baseline = (await db.execute(statement)).scalar_one_or_none()
    if baseline is None:
        raise BOQDomainError(
            "ACTIVE_BASELINE_REQUIRED",
            "Vendor cost publication requires an accepted active baseline",
        )
    return baseline


async def _current_plan(
    db: AsyncSession, project_id: UUID, *, for_update: bool = False
) -> BOQV2CostPlan | None:
    statement = select(BOQV2CostPlan).where(
        BOQV2CostPlan.project_id == project_id,
        BOQV2CostPlan.is_current.is_(True),
    )
    if for_update:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def _plan_components(db: AsyncSession, plan_id: UUID) -> list[BOQV2CostComponent]:
    return list(
        (
            await db.execute(
                select(BOQV2CostComponent)
                .where(BOQV2CostComponent.cost_plan_id == plan_id)
                .order_by(BOQV2CostComponent.scope_node_id, BOQV2CostComponent.component_type)
            )
        ).scalars().all()
    )


def _vendor_response(vendor: BOQV2Vendor) -> BOQV2VendorResponse:
    return BOQV2VendorResponse(
        id=vendor.id,
        project_id=vendor.project_id,
        display_name=vendor.display_name,
        commercial_reference=vendor.commercial_reference,
        linked_party_reference=vendor.linked_party_reference,
        tax_id=vendor.tax_id,
        contact_name=vendor.contact_name,
        contact_detail=vendor.contact_detail,
        status=vendor.status,
        created_at=_timestamp(vendor.created_at),
        updated_at=_timestamp(vendor.updated_at),
    )


async def create_vendor(
    db: AsyncSession,
    *,
    project_id: UUID,
    request: BOQV2VendorCreateRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2VendorResponse:
    await _project(db, project_id)
    await acquire_project_budget_locks(db, [project_id])
    command, prior_id = await _begin_command(
        db,
        actor=actor,
        project_id=project_id,
        command_type="CREATE_VENDOR",
        idempotency_key=idempotency_key,
        payload=request.model_dump(mode="json"),
    )
    if prior_id is not None:
        vendor = (await db.execute(select(BOQV2Vendor).where(BOQV2Vendor.id == prior_id))).scalar_one()
        return _vendor_response(vendor)
    vendor = BOQV2Vendor(
        id=uuid4(),
        project_id=project_id,
        display_name=request.display_name.strip(),
        commercial_reference=_clean(request.commercial_reference),
        linked_party_reference=_clean(request.linked_party_reference),
        tax_id=_clean(request.tax_id),
        contact_name=_clean(request.contact_name),
        contact_detail=_clean(request.contact_detail),
        created_by=actor,
    )
    db.add(vendor)
    await db.flush()
    _complete_command(command, revision_id=vendor.id, version=1)
    db.add(
        BOQV2AuditEvent(
            id=uuid4(), event_key=f"CREATE_VENDOR:{command.id}", project_id=project_id,
            actor=actor, command_type="CREATE_VENDOR", entity_type="VENDOR",
            entity_id=vendor.id, after_reference={"display_name": vendor.display_name},
        )
    )
    return _vendor_response(vendor)


async def list_vendors(db: AsyncSession, project_id: UUID) -> list[BOQV2VendorResponse]:
    await _project(db, project_id)
    rows = list(
        (
            await db.execute(
                select(BOQV2Vendor)
                .where(BOQV2Vendor.project_id == project_id)
                .order_by(BOQV2Vendor.status, BOQV2Vendor.display_name)
            )
        ).scalars().all()
    )
    return [_vendor_response(row) for row in rows]


async def _component_for_offer(
    db: AsyncSession, *, component_id: UUID, revision_id: UUID, project_id: UUID
) -> BOQV2CostComponent:
    row = (
        await db.execute(
            select(BOQV2CostComponent)
            .join(BOQV2CostPlan, BOQV2CostPlan.id == BOQV2CostComponent.cost_plan_id)
            .join(BOQV2ScopeNode, BOQV2ScopeNode.id == BOQV2CostComponent.scope_node_id)
            .where(
                BOQV2CostComponent.id == component_id,
                BOQV2CostPlan.project_id == project_id,
                BOQV2ScopeNode.revision_id == revision_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise BOQDomainError(
            "COST_COMPONENT_NOT_FOUND",
            "The cost component does not belong to this project/revision",
        )
    return row


def _line_response(line: BOQV2VendorOfferLine, component: BOQV2CostComponent) -> BOQV2OfferLineResponse:
    return BOQV2OfferLineResponse(
        id=line.id,
        component_id=line.source_component_id,
        scope_node_id=line.scope_node_id,
        component_type=line.component_type,
        basis_version=line.basis_version,
        required_quantity=_rate(component.quantity) or "0.0000",
        offered_quantity=_rate(line.offered_quantity) or "0.0000",
        required_unit=component.unit,
        offered_unit=line.unit,
        required_specification=component.specification,
        offered_specification=line.specification,
        unit_rate=_rate(line.unit_rate) or "0.0000",
        subtotal=_amount(line.subtotal) or "0.00",
        discount_amount=_amount(line.discount_amount) or "0.00",
        charges_amount=_amount(line.charges_amount) or "0.00",
        original_total=_amount(line.original_total) or "0.00",
        normalized_unit_rate_ex_vat=_rate(line.normalized_unit_rate_ex_vat),
        normalized_total_ex_vat=_amount(line.normalized_total_ex_vat),
        coverage_state=_coverage(Decimal(str(component.quantity)), Decimal(str(line.offered_quantity))),
        comparison_state=_comparison_state(component, line.unit, line.specification),
        basis_fingerprint=line.basis_fingerprint,
    )


async def _offer_response(db: AsyncSession, offer: BOQV2VendorOffer) -> BOQV2OfferResponse:
    vendor = (await db.execute(select(BOQV2Vendor).where(BOQV2Vendor.id == offer.vendor_id))).scalar_one()
    lines = list(
        (
            await db.execute(
                select(BOQV2VendorOfferLine)
                .where(BOQV2VendorOfferLine.offer_id == offer.id)
                .order_by(BOQV2VendorOfferLine.component_type, BOQV2VendorOfferLine.id)
            )
        ).scalars().all()
    )
    component_ids = [line.source_component_id for line in lines]
    components = {
        row.id: row
        for row in (
            await db.execute(select(BOQV2CostComponent).where(BOQV2CostComponent.id.in_(component_ids)))
        ).scalars().all()
    }
    return BOQV2OfferResponse(
        id=offer.id, project_id=offer.project_id, revision_id=offer.revision_id,
        vendor=_vendor_response(vendor), quotation_reference=offer.quotation_reference,
        quotation_date=offer.quotation_date, valid_until=offer.valid_until,
        expired=bool(offer.valid_until and offer.valid_until < date.today()),
        currency=offer.currency, tax_basis=offer.tax_basis, tax_rate=_rate(offer.tax_rate),
        discount_type=offer.discount_type, discount_value=_rate(offer.discount_value) or "0.0000",
        included_charges=offer.included_charges, charges_amount=_amount(offer.charges_amount) or "0.00",
        evidence_filename=offer.evidence_filename,
        evidence_content_type=offer.evidence_content_type,
        evidence_size_bytes=offer.evidence_size_bytes,
        notes=offer.notes, status=offer.status,
        lines=[_line_response(line, components[line.source_component_id]) for line in lines],
        created_at=_timestamp(offer.created_at),
    )


async def create_offer(
    db: AsyncSession,
    *,
    project_id: UUID,
    revision_id: UUID,
    request: BOQV2OfferCreateRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2OfferResponse:
    revision = (
        await db.execute(
            select(BOQV2Revision).where(
                BOQV2Revision.id == revision_id,
                BOQV2Revision.project_id == project_id,
            )
        )
    ).scalar_one_or_none()
    if revision is None:
        raise BOQDomainError("BOQ_REVISION_NOT_FOUND", "Revision does not belong to the project")
    vendor = (
        await db.execute(
            select(BOQV2Vendor).where(
                BOQV2Vendor.id == request.vendor_id,
                BOQV2Vendor.project_id == project_id,
                BOQV2Vendor.status == "ACTIVE",
            )
        )
    ).scalar_one_or_none()
    if vendor is None:
        raise BOQDomainError("VENDOR_NOT_FOUND", "Vendor does not belong to the project or is archived")
    if request.evidence_storage_key and not request.evidence_storage_key.startswith("gs://"):
        raise BOQDomainError("INVALID_EVIDENCE_REFERENCE", "Evidence storage identity must be a private gs:// key")
    await acquire_project_budget_locks(db, [project_id])
    command, prior_id = await _begin_command(
        db, actor=actor, project_id=project_id, command_type="CREATE_VENDOR_OFFER",
        idempotency_key=idempotency_key,
        payload={"revision_id": str(revision_id), **request.model_dump(mode="json")},
    )
    if prior_id is not None:
        prior = (await db.execute(select(BOQV2VendorOffer).where(BOQV2VendorOffer.id == prior_id))).scalar_one()
        return await _offer_response(db, prior)
    components: dict[UUID, BOQV2CostComponent] = {}
    for input_line in request.lines:
        component = await _component_for_offer(
            db, component_id=input_line.component_id, revision_id=revision_id, project_id=project_id
        )
        if component.component_type != input_line.component_type:
            raise BOQDomainError("COMPONENT_TYPE_MISMATCH", "Offer line component type does not match the BOQ component")
        components[component.id] = component
    offer = BOQV2VendorOffer(
        id=uuid4(), project_id=project_id, revision_id=revision_id, vendor_id=vendor.id,
        quotation_reference=_clean(request.quotation_reference), quotation_date=request.quotation_date,
        valid_until=request.valid_until, currency=request.currency, tax_basis=request.tax_basis,
        tax_rate=request.tax_rate, discount_type=request.discount_type,
        discount_value=request.discount_value, included_charges=_clean(request.included_charges),
        charges_amount=money(request.charges_amount), evidence_storage_key=request.evidence_storage_key,
        evidence_filename=_clean(request.evidence_filename), evidence_content_type=_clean(request.evidence_content_type),
        evidence_size_bytes=request.evidence_size_bytes, notes=_clean(request.notes), created_by=actor,
    )
    db.add(offer)
    await db.flush()
    now = datetime.now(UTC)
    for input_line in request.lines:
        component = components[input_line.component_id]
        subtotal = extended_amount(input_line.offered_quantity, input_line.unit_rate)
        line_total = money(subtotal - input_line.discount_amount + input_line.charges_amount)
        if line_total < 0:
            raise BOQDomainError("INVALID_OFFER_TOTAL", "Offer line discount cannot exceed subtotal plus charges")
        comparison = _comparison_state(component, input_line.unit, input_line.specification)
        normalized_total = _normalize_ex_vat(total=line_total, tax_basis=offer.tax_basis, tax_rate=offer.tax_rate)
        if comparison != "EQUIVALENT":
            normalized_total = None
        normalized_rate = (
            (normalized_total / input_line.offered_quantity).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            if normalized_total is not None else None
        )
        line = BOQV2VendorOfferLine(
            id=uuid4(), offer_id=offer.id, project_id=project_id, revision_id=revision_id,
            scope_node_id=component.scope_node_id, source_component_id=component.id,
            component_type=component.component_type, basis_version=component.basis_version,
            required_quantity=component.quantity, offered_quantity=input_line.offered_quantity,
            unit=_clean(input_line.unit), specification=_clean(input_line.specification),
            unit_rate=input_line.unit_rate, subtotal=subtotal,
            discount_amount=money(input_line.discount_amount), charges_amount=money(input_line.charges_amount),
            original_total=line_total, normalized_unit_rate_ex_vat=normalized_rate,
            normalized_total_ex_vat=normalized_total,
            coverage_state=_coverage(Decimal(str(component.quantity)), input_line.offered_quantity),
            comparison_state=comparison, basis_fingerprint=_basis_fingerprint(component),
        )
        db.add(line)
        await db.flush()
        node = (await db.execute(select(BOQV2ScopeNode).where(BOQV2ScopeNode.id == component.scope_node_id))).scalar_one()
        db.add(
            BOQV2PriceObservation(
                id=uuid4(), event_key=f"vendor-offer:{line.id}",
                sample_key=f"vendor-offer:{vendor.id}:{node.logical_id}:{component.component_type}:{offer.quotation_reference or offer.id}",
                observation_kind="VENDOR_OFFERED_COST", project_id=project_id,
                document_id=revision.document_id, revision_id=revision_id, scope_node_id=node.id,
                logical_item_id=node.logical_id, component_type=component.component_type,
                catalog_item_id=node.catalog_item_id, source_event_type="VENDOR_OFFER",
                source_event_id=offer.id, observed_at=now, quantity=input_line.offered_quantity,
                unit=line.unit, specification=line.specification, tax_basis=offer.tax_basis,
                currency=offer.currency, unit_rate=line.unit_rate, total=line.original_total,
                vendor_id=vendor.id, lineage_root_id=node.source_logical_id or node.logical_id,
            )
        )
    _complete_command(command, revision_id=offer.id, version=1)
    db.add(
        BOQV2AuditEvent(
            id=uuid4(), event_key=f"CREATE_VENDOR_OFFER:{command.id}", project_id=project_id,
            actor=actor, command_type="CREATE_VENDOR_OFFER", entity_type="VENDOR_OFFER",
            entity_id=offer.id, after_reference={"vendor_id": str(vendor.id), "line_count": len(request.lines)},
        )
    )
    await db.flush()
    return await _offer_response(db, offer)


async def list_offers(
    db: AsyncSession, *, project_id: UUID, revision_id: UUID | None = None
) -> list[BOQV2OfferResponse]:
    await _project(db, project_id)
    statement = select(BOQV2VendorOffer).where(BOQV2VendorOffer.project_id == project_id)
    if revision_id is not None:
        statement = statement.where(BOQV2VendorOffer.revision_id == revision_id)
    rows = list((await db.execute(statement.order_by(BOQV2VendorOffer.created_at.desc()))).scalars().all())
    return [await _offer_response(db, row) for row in rows]


async def _selection_response(
    db: AsyncSession, selection: BOQV2CostSelection
) -> BOQV2SelectionResponse:
    line = (await db.execute(select(BOQV2VendorOfferLine).where(BOQV2VendorOfferLine.id == selection.offer_line_id))).scalar_one()
    component = (
        await db.execute(
            select(BOQV2CostComponent)
            .join(BOQV2CostPlan, BOQV2CostPlan.id == BOQV2CostComponent.cost_plan_id)
            .where(
                BOQV2CostComponent.scope_node_id == selection.scope_node_id,
                BOQV2CostComponent.component_type == selection.component_type,
            )
            .order_by(
                BOQV2CostPlan.is_current.desc(),
                BOQV2CostPlan.version.desc(),
                BOQV2CostComponent.updated_at.desc(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    stale = component is None or _basis_fingerprint(component) != selection.basis_fingerprint
    warnings: list[str] = []
    offer = (await db.execute(select(BOQV2VendorOffer).where(BOQV2VendorOffer.id == line.offer_id))).scalar_one()
    if offer.valid_until and offer.valid_until < date.today():
        warnings.append("EXPIRED_OFFER")
    comparison = _comparison_state(component, line.unit, line.specification) if component else line.comparison_state
    if comparison != "EQUIVALENT":
        warnings.append(comparison)
    if offer.tax_basis == "UNKNOWN":
        warnings.append("UNKNOWN_TAX_BASIS")
    if stale:
        warnings.append("STALE_COMPONENT_BASIS")
    return BOQV2SelectionResponse(
        id=selection.id, project_id=selection.project_id, revision_id=selection.revision_id,
        scope_node_id=selection.scope_node_id, component_type=selection.component_type,
        offer_line_id=selection.offer_line_id,
        status="STALE" if stale and selection.is_current else selection.status,
        current=selection.is_current, stale=stale, warnings=warnings,
        warning_reason=selection.warning_reason, selected_by=selection.selected_by,
        selected_at=_timestamp(selection.selected_at), confirmed_at=(
            _timestamp(selection.confirmed_at) if selection.confirmed_at else None
        ),
    )


async def _recalculate_plan(db: AsyncSession, plan: BOQV2CostPlan) -> None:
    components = await _plan_components(db, plan.id)
    required = [component for component in components if component.cost_state != "NOT_APPLICABLE"]
    original_complete = all(component.original_total is not None for component in required)
    estimate_complete = all(component.total is not None for component in required)
    forecast_values: list[Decimal] = []
    agreed_values: list[Decimal] = []
    for component in components:
        if component.cost_state == "NOT_APPLICABLE":
            forecast_values.append(ZERO_MONEY)
        elif component.agreed_total is not None:
            agreed_values.append(money(component.agreed_total))
            forecast_values.append(money(component.agreed_total))
        elif component.total is not None:
            forecast_values.append(money(component.total))
    complete = len(forecast_values) == len(components)
    plan.required_count = len(components)
    plan.priced_count = len(forecast_values)
    plan.completeness_state = "COMPLETE" if complete else "INCOMPLETE"
    plan.original_estimated_cost = (
        money(sum((Decimal(str(item.original_total)) for item in required), ZERO_MONEY))
        if original_complete else None
    )
    plan.estimated_cost = (
        money(sum((Decimal(str(item.total)) for item in required), ZERO_MONEY))
        if estimate_complete else None
    )
    plan.agreed_cost = money(sum(agreed_values, ZERO_MONEY)) if agreed_values else None
    plan.forecast_cost = money(sum(forecast_values, ZERO_MONEY)) if complete else None


async def select_offer(
    db: AsyncSession,
    *,
    project_id: UUID,
    request: BOQV2SelectionRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2SelectionResponse:
    await acquire_project_budget_locks(db, [project_id])
    command, prior_id = await _begin_command(
        db, actor=actor, project_id=project_id, command_type="SELECT_VENDOR_OFFER",
        idempotency_key=idempotency_key, payload=request.model_dump(mode="json"),
    )
    if prior_id is not None:
        prior = (await db.execute(select(BOQV2CostSelection).where(BOQV2CostSelection.id == prior_id))).scalar_one()
        return await _selection_response(db, prior)
    plan = await _current_plan(db, project_id, for_update=True)
    if plan is None:
        raise BOQDomainError("WORKING_COST_PLAN_REQUIRED", "A working cost plan is required before selection")
    if plan.lock_version != request.expected_cost_plan_version:
        raise BOQDomainError("STALE_COST_PLAN_VERSION", "The cost plan changed; reload and retry")
    line = (
        await db.execute(
            select(BOQV2VendorOfferLine)
            .where(
                BOQV2VendorOfferLine.id == request.offer_line_id,
                BOQV2VendorOfferLine.project_id == project_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if line is None:
        raise BOQDomainError("OFFER_LINE_NOT_FOUND", "Offer line does not belong to the project")
    offer = (await db.execute(select(BOQV2VendorOffer).where(BOQV2VendorOffer.id == line.offer_id))).scalar_one()
    if offer.status != "ACTIVE":
        raise BOQDomainError("OFFER_NOT_ACTIVE", "Only an active offer can be selected")
    component = await _component_for_offer(
        db, component_id=line.source_component_id, revision_id=line.revision_id, project_id=project_id
    )
    if Decimal(str(line.offered_quantity)) != Decimal(str(component.quantity)):
        raise BOQDomainError(
            "OFFER_FULL_COVERAGE_REQUIRED",
            "Selected offer must cover exactly the full required component quantity",
        )
    current_fingerprint = _basis_fingerprint(component)
    warnings: list[str] = []
    comparison = _comparison_state(component, line.unit, line.specification)
    if comparison != "EQUIVALENT":
        warnings.append(comparison)
    if offer.valid_until and offer.valid_until < date.today():
        warnings.append("EXPIRED_OFFER")
    if offer.tax_basis == "UNKNOWN":
        warnings.append("UNKNOWN_TAX_BASIS")
    if warnings and (not request.acknowledge_warning or not _clean(request.reason)):
        raise BOQDomainError(
            "OFFER_WARNING_CONFIRMATION_REQUIRED",
            "Expired or non-equivalent offer selection requires explicit acknowledgement and reason",
        )
    previous = (
        await db.execute(
            select(BOQV2CostSelection)
            .where(
                BOQV2CostSelection.project_id == project_id,
                BOQV2CostSelection.scope_node_id == line.scope_node_id,
                BOQV2CostSelection.component_type == line.component_type,
                BOQV2CostSelection.is_current.is_(True),
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if previous is not None:
        previous.is_current = False
        previous.status = "REPLACED"
    selection = BOQV2CostSelection(
        id=uuid4(), project_id=project_id, revision_id=line.revision_id,
        scope_node_id=line.scope_node_id, component_type=line.component_type,
        offer_line_id=line.id, selected_basis_version=component.basis_version,
        basis_fingerprint=current_fingerprint, status="DRAFT", is_current=True,
        warning_reason=_clean(request.reason), warning_acknowledged=request.acknowledge_warning,
        selected_by=actor,
    )
    db.add(selection)
    await db.flush()
    candidate_component = (
        await db.execute(
            select(BOQV2CostComponent).where(
                BOQV2CostComponent.cost_plan_id == plan.id,
                BOQV2CostComponent.scope_node_id == line.scope_node_id,
                BOQV2CostComponent.component_type == line.component_type,
            )
        )
    ).scalar_one_or_none()
    if candidate_component is not None:
        candidate_component.selected_vendor_id = offer.vendor_id
        candidate_component.selected_offer_line_id = line.id
        candidate_component.selection_id = selection.id
        if line.normalized_total_ex_vat is not None and comparison == "EQUIVALENT":
            candidate_component.agreed_unit_rate = line.normalized_unit_rate_ex_vat
            candidate_component.agreed_total = line.normalized_total_ex_vat
        else:
            candidate_component.agreed_unit_rate = None
            candidate_component.agreed_total = None
    plan.lock_version += 1
    await _recalculate_plan(db, plan)
    _complete_command(command, revision_id=selection.id, version=1)
    db.add(
        BOQV2AuditEvent(
            id=uuid4(), event_key=f"SELECT_VENDOR_OFFER:{command.id}", project_id=project_id,
            actor=actor, command_type="SELECT_VENDOR_OFFER", entity_type="COST_SELECTION",
            entity_id=selection.id,
            before_reference={"selection_id": str(previous.id)} if previous else None,
            after_reference={"offer_line_id": str(line.id), "warnings": warnings},
            reason=_clean(request.reason),
        )
    )
    await db.flush()
    return await _selection_response(db, selection)


async def list_selections(db: AsyncSession, project_id: UUID) -> list[BOQV2SelectionResponse]:
    rows = list(
        (
            await db.execute(
                select(BOQV2CostSelection)
                .where(BOQV2CostSelection.project_id == project_id)
                .order_by(BOQV2CostSelection.selected_at.desc())
            )
        ).scalars().all()
    )
    return [await _selection_response(db, row) for row in rows]


async def _baseline_snapshots(
    db: AsyncSession, baseline: BOQV2ProjectBaseline
) -> list[tuple[BOQV2RevisionSnapshot, str | None]]:
    main = (
        await db.execute(select(BOQV2RevisionSnapshot).where(BOQV2RevisionSnapshot.id == baseline.main_snapshot_id))
    ).scalar_one()
    result: list[tuple[BOQV2RevisionSnapshot, str | None]] = [(main, None)]
    memberships = list(
        (
            await db.execute(
                select(BOQV2BaselineChangeOrder)
                .where(BOQV2BaselineChangeOrder.baseline_id == baseline.id)
                .order_by(BOQV2BaselineChangeOrder.position)
            )
        ).scalars().all()
    )
    for membership in memberships:
        snapshot = (
            await db.execute(select(BOQV2RevisionSnapshot).where(BOQV2RevisionSnapshot.id == membership.snapshot_id))
        ).scalar_one()
        direction = str(snapshot.internal_payload.get("document", {}).get("direction") or "") or None
        result.append((snapshot, direction))
    return result


async def ensure_working_cost_plan(
    db: AsyncSession, *, project_id: UUID, actor: str
) -> BOQV2CostPlanResponse:
    await lock_project_budget_state(db, [project_id])
    baseline = await _active_baseline(db, project_id, for_update=True)
    current = await _current_plan(db, project_id, for_update=True)
    if current is not None and current.status == "WORKING" and current.source_baseline_id == baseline.id:
        return await _cost_plan_response(db, current, baseline.net_sell_ex_vat)
    predecessor = None
    if baseline.cost_plan_id:
        predecessor = (
            await db.execute(select(BOQV2CostPlan).where(BOQV2CostPlan.id == baseline.cost_plan_id))
        ).scalar_one_or_none()
    if current is not None:
        current.is_current = False
    next_version = int(
        (await db.execute(select(func.coalesce(func.max(BOQV2CostPlan.version), 0)).where(BOQV2CostPlan.project_id == project_id))).scalar_one()
    ) + 1
    plan = BOQV2CostPlan(
        id=uuid4(), project_id=project_id, scope_revision_id=baseline.main_revision_id,
        source_baseline_id=baseline.id, predecessor_plan_id=predecessor.id if predecessor else None,
        version=next_version, lock_version=1, status="WORKING", is_current=True,
        completeness_state="INCOMPLETE", required_count=0, priced_count=0,
        calculation_version=baseline.calculation_version, created_by=actor,
    )
    db.add(plan)
    await db.flush()
    copied_keys: set[tuple[UUID, str]] = set()
    if predecessor is not None:
        for source in await _plan_components(db, predecessor.id):
            copied_keys.add((source.scope_node_id, source.component_type))
            db.add(
                BOQV2CostComponent(
                    id=uuid4(), cost_plan_id=plan.id, scope_node_id=source.scope_node_id,
                    component_type=source.component_type, quantity_basis=source.quantity_basis,
                    quantity=source.quantity, unit=source.unit, specification=source.specification,
                    basis_version=source.basis_version, source_component_id=source.source_component_id or source.id,
                    cost_state=source.cost_state, original_unit_rate=source.original_unit_rate,
                    original_total=source.original_total, unit_rate=source.unit_rate, total=source.total,
                    explicit_zero_reason=source.explicit_zero_reason,
                    agreed_unit_rate=source.agreed_unit_rate, agreed_total=source.agreed_total,
                    selected_vendor_id=source.selected_vendor_id,
                    selected_offer_line_id=source.selected_offer_line_id,
                    selection_id=source.selection_id,
                )
            )
    snapshots = await _baseline_snapshots(db, baseline)
    for snapshot, direction in snapshots:
        if direction == "DEDUCT":
            continue
        for node_payload in snapshot.internal_payload.get("scope", []):
            if node_payload.get("node_kind") != "ITEM" or node_payload.get("inclusion_state") == "EXCLUDED":
                continue
            node_id = UUID(str(node_payload["id"]))
            for component_payload in node_payload.get("components", []):
                key = (node_id, str(component_payload["component_type"]))
                if key in copied_keys:
                    continue
                copied_keys.add(key)
                state = str(component_payload["cost_state"])
                rate = component_payload.get("unit_rate")
                total = component_payload.get("total")
                db.add(
                    BOQV2CostComponent(
                        id=uuid4(), cost_plan_id=plan.id, scope_node_id=node_id,
                        component_type=component_payload["component_type"],
                        quantity_basis=component_payload["quantity_basis"],
                        quantity=Decimal(str(component_payload["quantity"])),
                        unit=component_payload.get("unit"), specification=component_payload.get("specification"),
                        basis_version=int(component_payload["basis_version"]),
                        source_component_id=UUID(str(component_payload["id"])),
                        cost_state=state,
                        original_unit_rate=Decimal(str(rate)) if rate is not None else None,
                        original_total=Decimal(str(total)) if total is not None else (ZERO_MONEY if state == "NOT_APPLICABLE" else None),
                        unit_rate=Decimal(str(rate)) if rate is not None else None,
                        total=Decimal(str(total)) if total is not None else (ZERO_MONEY if state == "NOT_APPLICABLE" else None),
                        explicit_zero_reason=component_payload.get("explicit_zero_reason"),
                    )
                )
    await db.flush()
    await _recalculate_plan(db, plan)
    db.add(
        BOQV2AuditEvent(
            id=uuid4(), event_key=f"OPEN_WORKING_COST_PLAN:{plan.id}", project_id=project_id,
            actor=actor, command_type="OPEN_WORKING_COST_PLAN", entity_type="COST_PLAN",
            entity_id=plan.id, calculation_version=plan.calculation_version,
            after_reference={"version": plan.version, "baseline_id": str(baseline.id)},
        )
    )
    await db.flush()
    return await _cost_plan_response(db, plan, baseline.net_sell_ex_vat)


async def _cost_plan_response(
    db: AsyncSession, plan: BOQV2CostPlan, net_sell_ex_vat: Decimal
) -> BOQV2CostPlanResponse:
    components = await _plan_components(db, plan.id)
    selection_ids = [component.selection_id for component in components if component.selection_id]
    selections = {
        row.id: row.status for row in (
            await db.execute(select(BOQV2CostSelection).where(BOQV2CostSelection.id.in_(selection_ids)))
        ).scalars().all()
    } if selection_ids else {}
    rows: list[BOQV2CostComponentResponse] = []
    for component in components:
        forecast = component.agreed_total if component.agreed_total is not None else component.total
        rows.append(
            BOQV2CostComponentResponse(
                id=component.id, source_component_id=component.source_component_id,
                scope_node_id=component.scope_node_id, component_type=component.component_type,
                quantity=_rate(component.quantity) or "0.0000", unit=component.unit,
                specification=component.specification, basis_version=component.basis_version,
                cost_state=component.cost_state, original_unit_rate=_rate(component.original_unit_rate),
                original_total=_amount(component.original_total), estimate_unit_rate=_rate(component.unit_rate),
                estimate_total=_amount(component.total), agreed_unit_rate=_rate(component.agreed_unit_rate),
                agreed_total=_amount(component.agreed_total), forecast_total=_amount(forecast),
                selected_vendor_id=component.selected_vendor_id,
                selected_offer_line_id=component.selected_offer_line_id,
                selection_status=selections.get(component.selection_id),
            )
        )
    return BOQV2CostPlanResponse(
        id=plan.id, project_id=plan.project_id, source_baseline_id=plan.source_baseline_id,
        version=plan.version, expected_version=plan.lock_version, status=plan.status,
        completeness_state=plan.completeness_state, required_count=plan.required_count,
        priced_count=plan.priced_count, original_estimated_cost=_amount(plan.original_estimated_cost),
        estimated_cost=_amount(plan.estimated_cost), agreed_cost=_amount(plan.agreed_cost),
        forecast_cost=_amount(plan.forecast_cost),
        forecast_margin=(
            _amount(money(Decimal(str(net_sell_ex_vat)) - Decimal(str(plan.forecast_cost))))
            if plan.forecast_cost is not None else None
        ),
        components=rows, published_at=_timestamp(plan.published_at) if plan.published_at else None,
        published_by=plan.published_by, publish_reason=plan.publish_reason,
    )


async def load_cost_plan(db: AsyncSession, project_id: UUID) -> BOQV2CostPlanResponse:
    plan = await _current_plan(db, project_id)
    baseline = (
        await db.execute(
            select(BOQV2ProjectBaseline).where(
                BOQV2ProjectBaseline.project_id == project_id,
                BOQV2ProjectBaseline.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if baseline is None:
        if plan is None:
            raise BOQDomainError("WORKING_COST_PLAN_REQUIRED", "No working cost plan is available")
        revision = (
            await db.execute(select(BOQV2Revision).where(BOQV2Revision.id == plan.scope_revision_id))
        ).scalar_one()
        return await _cost_plan_response(db, plan, revision.net_sell_ex_vat or ZERO_MONEY)
    if plan is None or (plan.status == "WORKING" and plan.source_baseline_id != baseline.id):
        if baseline.cost_plan_id is None:
            raise BOQDomainError("WORKING_COST_PLAN_REQUIRED", "Owner must open a working cost plan first")
        plan = (await db.execute(select(BOQV2CostPlan).where(BOQV2CostPlan.id == baseline.cost_plan_id))).scalar_one()
    return await _cost_plan_response(db, plan, baseline.net_sell_ex_vat)


async def update_estimates(
    db: AsyncSession,
    *,
    project_id: UUID,
    request: BOQV2CostEstimateUpdateRequest,
    actor: str,
) -> BOQV2CostPlanResponse:
    await acquire_project_budget_locks(db, [project_id])
    baseline = await _active_baseline(db, project_id, for_update=True)
    plan = await _current_plan(db, project_id, for_update=True)
    if plan is None or plan.status != "WORKING" or plan.source_baseline_id != baseline.id:
        raise BOQDomainError("WORKING_COST_PLAN_REQUIRED", "Open a working cost plan before editing estimates")
    if plan.lock_version != request.expected_version:
        raise BOQDomainError("STALE_COST_PLAN_VERSION", "The working cost plan changed; reload and retry")
    component_map = {row.id: row for row in await _plan_components(db, plan.id)}
    if len({item.component_id for item in request.components}) != len(request.components):
        raise BOQDomainError("DUPLICATE_COST_COMPONENT", "Cost component updates must be unique")
    for item in request.components:
        component = component_map.get(item.component_id)
        if component is None:
            raise BOQDomainError("COST_COMPONENT_NOT_FOUND", "Cost component does not belong to the working plan")
        component.cost_state = item.cost_state
        component.explicit_zero_reason = _clean(item.explicit_zero_reason)
        if item.cost_state == "UNKNOWN":
            component.unit_rate = None
            component.total = None
        elif item.cost_state == "NOT_APPLICABLE":
            component.unit_rate = None
            component.total = ZERO_MONEY
        else:
            component.unit_rate = item.unit_rate
            component.total = extended_amount(component.quantity, item.unit_rate or ZERO_RATE)
    plan.lock_version += 1
    await _recalculate_plan(db, plan)
    db.add(
        BOQV2AuditEvent(
            id=uuid4(), event_key=f"UPDATE_COST_ESTIMATE:{plan.id}:{plan.lock_version}",
            project_id=project_id, actor=actor, command_type="UPDATE_COST_ESTIMATE",
            entity_type="COST_PLAN", entity_id=plan.id, calculation_version=plan.calculation_version,
            after_reference={"version": plan.version, "lock_version": plan.lock_version},
        )
    )
    await db.flush()
    return await _cost_plan_response(db, plan, baseline.net_sell_ex_vat)


async def publish_cost_plan(
    db: AsyncSession,
    *,
    project_id: UUID,
    request: BOQV2CostPublishRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2CostPublishResponse:
    await lock_project_budget_state(db, [project_id])
    command, prior_id = await _begin_command(
        db, actor=actor, project_id=project_id, command_type="PUBLISH_COST_PLAN",
        idempotency_key=idempotency_key,
        payload=request.model_dump(mode="json"),
    )
    if prior_id is not None:
        prior = (await db.execute(select(BOQV2CostPlan).where(BOQV2CostPlan.id == prior_id))).scalar_one()
        published_baseline = (
            await db.execute(
                select(BOQV2ProjectBaseline).where(BOQV2ProjectBaseline.cost_plan_id == prior.id)
            )
        ).scalar_one()
        source = (
            await db.execute(select(BOQV2ProjectBudgetSource).where(BOQV2ProjectBudgetSource.project_id == project_id))
        ).scalar_one()
        return BOQV2CostPublishResponse(
            cost_plan=await _cost_plan_response(db, prior, published_baseline.net_sell_ex_vat),
            baseline_id=published_baseline.id, baseline_version=published_baseline.version,
            source_version=source.version, forecast_impact=None,
            completeness_state=prior.completeness_state,
        )
    baseline = await _active_baseline(db, project_id, for_update=True)
    if baseline.version != request.expected_baseline_version:
        raise BOQDomainError("STALE_BASELINE_VERSION", "The active baseline changed; reload and retry")
    plan = await _current_plan(db, project_id, for_update=True)
    if plan is None or plan.status != "WORKING" or plan.source_baseline_id != baseline.id:
        raise BOQDomainError("WORKING_COST_PLAN_REQUIRED", "A matching working cost plan is required")
    if plan.lock_version != request.expected_version:
        raise BOQDomainError("STALE_COST_PLAN_VERSION", "The working cost plan changed; reload and retry")
    components = await _plan_components(db, plan.id)
    selections = list(
        (
            await db.execute(
                select(BOQV2CostSelection)
                .where(
                    BOQV2CostSelection.project_id == project_id,
                    BOQV2CostSelection.is_current.is_(True),
                )
                .with_for_update()
            )
        ).scalars().all()
    )
    selection_map = {(row.scope_node_id, row.component_type): row for row in selections}
    now = datetime.now(UTC)
    for component in components:
        selection = selection_map.get((component.scope_node_id, component.component_type))
        component.agreed_unit_rate = None
        component.agreed_total = None
        component.selected_vendor_id = None
        component.selected_offer_line_id = None
        component.selection_id = None
        if selection is None:
            continue
        if selection.basis_fingerprint != _basis_fingerprint(component):
            selection.status = "STALE"
            raise BOQDomainError(
                "STALE_COST_SELECTION",
                "A selected vendor offer no longer matches the component basis; reconfirm it explicitly",
            )
        line = (await db.execute(select(BOQV2VendorOfferLine).where(BOQV2VendorOfferLine.id == selection.offer_line_id))).scalar_one()
        offer = (await db.execute(select(BOQV2VendorOffer).where(BOQV2VendorOffer.id == line.offer_id))).scalar_one()
        if Decimal(str(line.offered_quantity)) != Decimal(str(component.quantity)):
            selection.status = "STALE"
            raise BOQDomainError("OFFER_FULL_COVERAGE_REQUIRED", "Selected offer no longer covers the full quantity")
        comparison = _comparison_state(component, line.unit, line.specification)
        warnings = comparison != "EQUIVALENT" or bool(offer.valid_until and offer.valid_until < date.today())
        if warnings and (not selection.warning_acknowledged or not _clean(selection.warning_reason)):
            raise BOQDomainError("OFFER_WARNING_CONFIRMATION_REQUIRED", "Selection warnings require a recorded reason")
        if line.normalized_total_ex_vat is not None and comparison == "EQUIVALENT":
            component.agreed_unit_rate = line.normalized_unit_rate_ex_vat
            component.agreed_total = line.normalized_total_ex_vat
        component.selected_vendor_id = offer.vendor_id
        component.selected_offer_line_id = line.id
        component.selection_id = selection.id
        selection.status = "CONFIRMED"
        selection.confirmed_by = actor
        selection.confirmed_at = now
        selection.cost_plan_id = plan.id
        node = (await db.execute(select(BOQV2ScopeNode).where(BOQV2ScopeNode.id == component.scope_node_id))).scalar_one()
        db.add(
            BOQV2PriceObservation(
                id=uuid4(), event_key=f"vendor-award:{selection.id}:{plan.id}",
                sample_key=f"vendor-award:{offer.vendor_id}:{node.source_logical_id or node.logical_id}:{component.component_type}:{offer.quotation_reference or offer.id}",
                observation_kind="AGREED_VENDOR_COST", project_id=project_id,
                document_id=(await db.execute(select(BOQV2Revision.document_id).where(BOQV2Revision.id == line.revision_id))).scalar_one(),
                revision_id=line.revision_id, scope_node_id=node.id, logical_item_id=node.logical_id,
                component_type=component.component_type, catalog_item_id=node.catalog_item_id,
                source_event_type="COST_PLAN_PUBLISH", source_event_id=plan.id,
                observed_at=now, quantity=component.quantity, unit=line.unit,
                specification=line.specification, tax_basis=offer.tax_basis,
                currency=offer.currency, unit_rate=line.normalized_unit_rate_ex_vat or line.unit_rate,
                total=line.normalized_total_ex_vat or line.original_total,
                vendor_id=offer.vendor_id, lineage_root_id=node.source_logical_id or node.logical_id,
            )
        )
    await _recalculate_plan(db, plan)
    old_forecast = baseline.forecast_cost
    plan.status = "PUBLISHED"
    plan.published_at = now
    plan.published_by = actor
    plan.publish_reason = request.reason.strip()
    plan.effective_at = request.effective_at or now
    plan.lock_version += 1
    memberships = list(
        (
            await db.execute(
                select(BOQV2BaselineChangeOrder)
                .where(BOQV2BaselineChangeOrder.baseline_id == baseline.id)
                .order_by(BOQV2BaselineChangeOrder.position)
            )
        ).scalars().all()
    )
    baseline.is_active = False
    baseline.effective_to = plan.effective_at
    next_baseline = BOQV2ProjectBaseline(
        id=uuid4(), project_id=project_id, version=baseline.version + 1,
        main_revision_id=baseline.main_revision_id, main_snapshot_id=baseline.main_snapshot_id,
        cost_plan_id=plan.id, is_active=True, calculation_version=baseline.calculation_version,
        net_sell_ex_vat=baseline.net_sell_ex_vat,
        original_estimated_cost=plan.original_estimated_cost,
        agreed_cost=plan.agreed_cost, forecast_cost=plan.forecast_cost,
        forecast_margin=(money(Decimal(str(baseline.net_sell_ex_vat)) - Decimal(str(plan.forecast_cost))) if plan.forecast_cost is not None else None),
        activated_at=now, effective_from=plan.effective_at, created_by=actor,
    )
    db.add(next_baseline)
    await db.flush()
    for membership in memberships:
        db.add(
            BOQV2BaselineChangeOrder(
                id=uuid4(), baseline_id=next_baseline.id, revision_id=membership.revision_id,
                document_id=membership.document_id, snapshot_id=membership.snapshot_id,
                position=membership.position,
            )
        )
    source = (
        await db.execute(
            select(BOQV2ProjectBudgetSource)
            .where(BOQV2ProjectBudgetSource.project_id == project_id)
            .with_for_update()
        )
    ).scalar_one()
    source.source_kind = "V2"
    source.version += 1
    source.updated_by = actor
    source.updated_at = now
    _complete_command(command, revision_id=plan.id, version=plan.version)
    db.add(
        BOQV2AuditEvent(
            id=uuid4(), event_key=f"PUBLISH_COST_PLAN:{command.id}", project_id=project_id,
            actor=actor, command_type="PUBLISH_COST_PLAN", entity_type="COST_PLAN",
            entity_id=plan.id, calculation_version=plan.calculation_version,
            before_reference={"baseline_id": str(baseline.id), "forecast_cost": _amount(old_forecast)},
            after_reference={
                "baseline_id": str(next_baseline.id), "baseline_version": next_baseline.version,
                "forecast_cost": _amount(plan.forecast_cost), "completeness": plan.completeness_state,
                "source_version": source.version,
            }, reason=request.reason.strip(),
        )
    )
    for component in components:
        if component.total is None:
            continue
        node = (await db.execute(select(BOQV2ScopeNode).where(BOQV2ScopeNode.id == component.scope_node_id))).scalar_one()
        revision = (await db.execute(select(BOQV2Revision).where(BOQV2Revision.id == node.revision_id))).scalar_one()
        db.add(
            BOQV2PriceObservation(
                id=uuid4(), event_key=f"estimate-publish:{plan.id}:{component.id}",
                sample_key=f"estimate:{node.source_logical_id or node.logical_id}:{component.component_type}",
                observation_kind="ESTIMATED_COST", project_id=project_id,
                document_id=revision.document_id, revision_id=node.revision_id,
                scope_node_id=node.id, logical_item_id=node.logical_id,
                component_type=component.component_type, catalog_item_id=node.catalog_item_id,
                source_event_type="COST_PLAN_PUBLISH", source_event_id=plan.id,
                observed_at=now, quantity=component.quantity, unit=component.unit,
                specification=component.specification, tax_basis="EXCLUSIVE_VAT",
                currency="THB", unit_rate=component.unit_rate or ZERO_RATE,
                total=component.total, vendor_id=None,
                lineage_root_id=node.source_logical_id or node.logical_id,
            )
        )
    await db.flush()
    impact = None
    if old_forecast != plan.forecast_cost:
        impact = f"{_amount(old_forecast) or 'UNKNOWN'} -> {_amount(plan.forecast_cost) or 'UNKNOWN'}"
    return BOQV2CostPublishResponse(
        cost_plan=await _cost_plan_response(db, plan, next_baseline.net_sell_ex_vat),
        baseline_id=next_baseline.id, baseline_version=next_baseline.version,
        source_version=source.version, forecast_impact=impact,
        completeness_state=plan.completeness_state,
    )
