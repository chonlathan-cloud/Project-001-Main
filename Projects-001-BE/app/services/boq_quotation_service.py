"""Phase 3 quotation lifecycle, immutable snapshots, and accepted baselines."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boq import Project
from app.models.boq_v2 import (
    BOQV2Acceptance,
    BOQV2AuditEvent,
    BOQV2BaselineChangeOrder,
    BOQV2ChangeOrderDeduction,
    BOQV2CostComponent,
    BOQV2CostPlan,
    BOQV2Document,
    BOQV2ProjectBaseline,
    BOQV2ProjectBudgetSource,
    BOQV2Revision,
    BOQV2RevisionSnapshot,
    BOQV2ScopeNode,
)
from app.schemas.boq_quotation_schema import (
    BOQV2AcceptanceResponse,
    BOQV2ActiveBaselineResponse,
    BOQV2CreateAlternativeRequest,
    BOQV2CreateChangeOrderRequest,
    BOQV2ExpectedVersionRequest,
    BOQV2QuotationPreviewResponse,
    BOQV2RecordAcceptanceRequest,
    BOQV2ReplacementDecision,
    BOQV2SnapshotSummary,
    BOQV2TransitionRequest,
)
from app.schemas.boq_v2_schema import BOQV2RevisionResponse
from app.services.boq_calculation_service import (
    CALCULATION_VERSION,
    money,
    signed_change_order_amount,
)
from app.services.boq_document_service import (
    _audit,
    _begin_command,
    _complete_command,
    _current_cost_plan,
    _next_cost_plan_version,
    _project_or_error,
    _replace_current_working_plan,
    _revision_context,
    load_boq_revision,
)
from app.services.boq_domain_service import (
    BOQDomainError,
    acquire_project_budget_locks,
    assert_expected_version,
    assert_mutable_draft,
)
from app.services.boq_numbering_service import (
    next_document_number,
    next_revision_number,
)


ZERO_MONEY = Decimal("0.00")
ZERO_RATE = Decimal("0.0000")


def _timestamp(value: datetime | None) -> str:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _canonical_hash(payload: object) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _clean_text(value: object | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


async def _active_baseline(
    db: AsyncSession,
    project_id: UUID,
    *,
    for_update: bool = False,
) -> BOQV2ProjectBaseline | None:
    statement = select(BOQV2ProjectBaseline).where(
        BOQV2ProjectBaseline.project_id == project_id,
        BOQV2ProjectBaseline.is_active.is_(True),
    )
    if for_update:
        statement = statement.with_for_update()
    return (await db.execute(statement)).scalar_one_or_none()


async def _baseline_memberships(
    db: AsyncSession,
    baseline_id: UUID,
) -> list[BOQV2BaselineChangeOrder]:
    return list(
        (
            await db.execute(
                select(BOQV2BaselineChangeOrder)
                .where(BOQV2BaselineChangeOrder.baseline_id == baseline_id)
                .order_by(BOQV2BaselineChangeOrder.position)
            )
        )
        .scalars()
        .all()
    )


async def _issue_snapshot(
    db: AsyncSession,
    revision_id: UUID,
) -> BOQV2RevisionSnapshot | None:
    return (
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


def _snapshot_summary(
    snapshot: BOQV2RevisionSnapshot,
    *,
    document_number: str,
    revision_number: int,
) -> BOQV2SnapshotSummary:
    return BOQV2SnapshotSummary(
        snapshot_id=snapshot.id,
        project_id=snapshot.project_id,
        document_id=snapshot.document_id,
        document_number=document_number,
        revision_id=snapshot.revision_id,
        revision_number=revision_number,
        source_version=snapshot.source_version,
        purpose=snapshot.purpose,
        lifecycle_status=snapshot.lifecycle_status,
        calculation_version=snapshot.calculation_version,
        payload_sha256=snapshot.payload_sha256,
        created_at=_timestamp(snapshot.created_at),
    )


def _customer_scope_node(node: object) -> dict[str, object]:
    return {
        "id": str(node.id),
        "logical_id": str(node.logical_id),
        "parent_logical_id": (
            str(node.parent_logical_id) if node.parent_logical_id else None
        ),
        "node_kind": node.node_kind,
        "inclusion_state": node.inclusion_state,
        "position": node.position,
        "depth": node.depth,
        "display_path": node.display_path,
        "item_code": node.item_code,
        "description": node.description,
        "specification": node.specification,
        "quantity": node.quantity,
        "unit": node.unit,
        "sell_material_unit_rate": node.sell_material_unit_rate,
        "sell_labor_unit_rate": node.sell_labor_unit_rate,
        "sell_total": node.sell_total,
    }


def _internal_scope_node(node: object) -> dict[str, object]:
    payload = _customer_scope_node(node)
    payload["components"] = [
        {
            "id": str(component.id),
            "component_type": component.component_type,
            "quantity_basis": component.quantity_basis,
            "quantity": component.quantity,
            "unit": component.unit,
            "specification": component.specification,
            "basis_version": component.basis_version,
            "cost_state": component.cost_state,
            "unit_rate": component.unit_rate,
            "total": component.total,
            "explicit_zero_reason": component.explicit_zero_reason,
        }
        for component in node.components
    ]
    return payload


async def _build_snapshot_payloads(
    db: AsyncSession,
    *,
    revision_id: UUID,
    lifecycle_status: str,
) -> tuple[dict[str, object], dict[str, object], BOQV2RevisionResponse]:
    response = await load_boq_revision(db, revision_id)
    cost_plan = await _current_cost_plan(db, revision_id)
    quotation = response.quotation.model_dump(mode="json")
    common = {
        "schema_version": "boq-v2-document-snapshot-v1",
        "project": {
            "id": str(response.project_id),
            "name": response.project_name,
        },
        "document": {
            "id": str(response.document_id),
            "number": response.document_number,
            "kind": response.document_kind,
            "direction": response.direction,
            "alternative_group_id": (
                str(response.alternative_group_id)
                if response.alternative_group_id
                else None
            ),
            "base_baseline_id": (
                str(response.base_baseline_id) if response.base_baseline_id else None
            ),
            "base_baseline_version": response.base_baseline_version,
        },
        "revision": {
            "id": str(response.revision_id),
            "number": response.revision_number,
            "status": lifecycle_status,
            "source_version": response.version,
            "predecessor_revision_id": (
                str(response.predecessor_revision_id)
                if response.predecessor_revision_id
                else None
            ),
        },
        "calculation": {
            "version": response.calculation_version,
            "policy": {
                "money_rounding": "ROUND_HALF_UP_2",
                "rate_scale": 4,
                "currency": "THB",
                "change_order_sign": response.direction,
            },
            "subtotal": quotation["subtotal"],
            "discount_type": quotation["discount_type"],
            "discount_value": quotation["discount_value"],
            "discount_amount": quotation["discount_amount"],
            "net_sell_ex_vat": quotation["net_sell_ex_vat"],
            "vat_rate": quotation["vat_rate"],
            "vat_amount": quotation["vat_amount"],
            "grand_total": quotation["grand_total"],
        },
        "quotation": {
            key: quotation[key]
            for key in (
                "title",
                "customer_name",
                "customer_address",
                "customer_tax_id",
                "customer_contact",
                "quotation_date",
                "valid_until",
                "currency",
                "payment_schedule",
                "commercial_terms",
                "document_pages",
            )
        },
    }
    customer_payload = {
        **common,
        "scope": [_customer_scope_node(node) for node in response.nodes],
    }
    internal_payload = {
        **common,
        "scope": [_internal_scope_node(node) for node in response.nodes],
        "cost": {
            "plan_id": str(cost_plan.id) if cost_plan else None,
            "plan_version": cost_plan.version if cost_plan else None,
            "known_estimated_cost": response.known_estimated_cost,
            "forecast_cost": response.forecast_cost,
            "forecast_margin": response.forecast_margin,
            "completeness": response.completeness.model_dump(mode="json"),
        },
    }
    return customer_payload, internal_payload, response


async def _create_snapshot(
    db: AsyncSession,
    *,
    revision: BOQV2Revision,
    document: BOQV2Document,
    purpose: str,
    lifecycle_status: str,
    actor: str,
) -> BOQV2RevisionSnapshot:
    existing = (
        await db.execute(
            select(BOQV2RevisionSnapshot).where(
                BOQV2RevisionSnapshot.revision_id == revision.id,
                BOQV2RevisionSnapshot.source_version == revision.version,
                BOQV2RevisionSnapshot.purpose == purpose,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    customer_payload, internal_payload, _ = await _build_snapshot_payloads(
        db,
        revision_id=revision.id,
        lifecycle_status=lifecycle_status,
    )
    payload_hash = _canonical_hash(
        {"customer": customer_payload, "internal": internal_payload}
    )
    snapshot = BOQV2RevisionSnapshot(
        id=uuid4(),
        project_id=revision.project_id,
        document_id=document.id,
        revision_id=revision.id,
        source_version=revision.version,
        purpose=purpose,
        lifecycle_status=lifecycle_status,
        calculation_version=revision.calculation_version,
        customer_payload=customer_payload,
        internal_payload=internal_payload,
        payload_sha256=payload_hash,
        created_by=actor,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


def _validate_issue(response: BOQV2RevisionResponse) -> None:
    quotation = response.quotation
    missing_header: list[str] = []
    if not _clean_text(quotation.title):
        missing_header.append("title")
    if not _clean_text(quotation.customer_name):
        missing_header.append("customer_name")
    if quotation.quotation_date is None:
        missing_header.append("quotation_date")
    if quotation.valid_until is None:
        missing_header.append("valid_until")
    if missing_header:
        raise BOQDomainError(
            "QUOTATION_HEADER_INCOMPLETE",
            f"Quotation header is missing: {', '.join(missing_header)}",
        )
    included_items = [
        node
        for node in response.nodes
        if node.node_kind == "ITEM" and node.inclusion_state != "EXCLUDED"
    ]
    if not included_items:
        raise BOQDomainError(
            "QUOTATION_SCOPE_EMPTY", "Quotation requires at least one included item"
        )
    for node in included_items:
        missing = []
        if not _clean_text(node.description):
            missing.append("description")
        if not _clean_text(node.unit):
            missing.append("unit")
        if node.quantity is None or Decimal(node.quantity) <= 0:
            missing.append("quantity")
        if node.sell_material_unit_rate is None or node.sell_labor_unit_rate is None:
            missing.append("sell rates")
        if missing:
            raise BOQDomainError(
                "QUOTATION_SCOPE_INCOMPLETE",
                f"Scope item {node.logical_id} is missing: {', '.join(missing)}",
            )
    if not quotation.commercial_terms:
        raise BOQDomainError(
            "QUOTATION_TERMS_REQUIRED",
            "Quotation requires at least one commercial term before issue",
        )
    if not quotation.payment_schedule:
        raise BOQDomainError(
            "QUOTATION_PAYMENT_SCHEDULE_REQUIRED",
            "Quotation requires a payment schedule before issue",
        )


async def create_preview_snapshot(
    db: AsyncSession,
    *,
    revision_id: UUID,
    request: BOQV2ExpectedVersionRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2QuotationPreviewResponse:
    revision, document, _ = await _revision_context(db, revision_id)
    await acquire_project_budget_locks(db, [revision.project_id])
    revision, document, _ = await _revision_context(db, revision_id, for_update=True)
    assert_expected_version(current=revision.version, expected=request.expected_version)
    if revision.status not in {"DRAFT", "ISSUED", "ACCEPTED"}:
        raise BOQDomainError(
            "QUOTATION_PREVIEW_UNAVAILABLE",
            "Only draft, issued, or accepted revisions can be previewed",
        )
    command, prior_snapshot_id = await _begin_command(
        db,
        actor=actor,
        project_id=revision.project_id,
        command_type="CREATE_PREVIEW_SNAPSHOT",
        idempotency_key=idempotency_key,
        payload={
            "revision_id": str(revision_id),
            "expected_version": request.expected_version,
        },
    )
    if prior_snapshot_id is not None:
        snapshot = (
            await db.execute(
                select(BOQV2RevisionSnapshot).where(
                    BOQV2RevisionSnapshot.id == prior_snapshot_id
                )
            )
        ).scalar_one()
    elif revision.status in {"ISSUED", "ACCEPTED"}:
        snapshot = await _issue_snapshot(db, revision.id)
        if snapshot is None:
            raise BOQDomainError(
                "ISSUED_SNAPSHOT_MISSING",
                "Issued quotation snapshot is missing",
            )
        _complete_command(command, revision_id=snapshot.id, version=revision.version)
    else:
        snapshot = await _create_snapshot(
            db,
            revision=revision,
            document=document,
            purpose="PREVIEW",
            lifecycle_status="DRAFT",
            actor=actor,
        )
        _complete_command(command, revision_id=snapshot.id, version=revision.version)
    await db.flush()
    return BOQV2QuotationPreviewResponse(
        snapshot=_snapshot_summary(
            snapshot,
            document_number=document.document_number,
            revision_number=revision.revision_number,
        ),
        document=dict(snapshot.customer_payload),
    )


async def load_quotation_preview(
    db: AsyncSession,
    *,
    revision_id: UUID,
    snapshot_id: UUID,
) -> BOQV2QuotationPreviewResponse:
    revision, document, _ = await _revision_context(db, revision_id)
    snapshot = (
        await db.execute(
            select(BOQV2RevisionSnapshot).where(
                BOQV2RevisionSnapshot.id == snapshot_id,
                BOQV2RevisionSnapshot.revision_id == revision_id,
                BOQV2RevisionSnapshot.project_id == revision.project_id,
            )
        )
    ).scalar_one_or_none()
    if snapshot is None:
        raise BOQDomainError(
            "QUOTATION_SNAPSHOT_NOT_FOUND",
            "Quotation snapshot does not belong to this revision",
        )
    return BOQV2QuotationPreviewResponse(
        snapshot=_snapshot_summary(
            snapshot,
            document_number=document.document_number,
            revision_number=revision.revision_number,
        ),
        document=dict(snapshot.customer_payload),
    )


async def issue_quotation(
    db: AsyncSession,
    *,
    revision_id: UUID,
    request: BOQV2ExpectedVersionRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2RevisionResponse:
    revision, document, _ = await _revision_context(db, revision_id)
    await acquire_project_budget_locks(db, [revision.project_id])
    revision, document, _ = await _revision_context(db, revision_id, for_update=True)
    assert_mutable_draft(revision.status)
    assert_expected_version(current=revision.version, expected=request.expected_version)
    command, prior_revision_id = await _begin_command(
        db,
        actor=actor,
        project_id=revision.project_id,
        command_type="ISSUE_QUOTATION",
        idempotency_key=idempotency_key,
        payload={
            "revision_id": str(revision_id),
            "expected_version": request.expected_version,
        },
    )
    if prior_revision_id is not None:
        return await load_boq_revision(db, prior_revision_id)
    current = await load_boq_revision(db, revision.id)
    _validate_issue(current)
    now = datetime.now(UTC)
    before = {"status": revision.status, "version": revision.version}
    revision.status = "ISSUED"
    revision.version += 1
    revision.issued_by = actor
    revision.issued_at = now
    revision.updated_at = now
    await db.flush()
    snapshot = await _create_snapshot(
        db,
        revision=revision,
        document=document,
        purpose="ISSUE",
        lifecycle_status="ISSUED",
        actor=actor,
    )
    _complete_command(command, revision_id=revision.id, version=revision.version)
    _audit(
        db,
        command=command,
        actor=actor,
        project_id=revision.project_id,
        command_type="ISSUE_QUOTATION",
        entity_type="BOQ_REVISION",
        entity_id=revision.id,
        before=before,
        after={
            "status": "ISSUED",
            "version": revision.version,
            "snapshot_id": str(snapshot.id),
            "payload_sha256": snapshot.payload_sha256,
        },
    )
    await db.flush()
    return await load_boq_revision(db, revision.id)


async def _clone_revision(
    db: AsyncSession,
    *,
    source_revision: BOQV2Revision,
    target_document: BOQV2Document,
    target_project: Project,
    revision_number: int,
    actor: str,
    base_baseline: BOQV2ProjectBaseline | None = None,
) -> BOQV2Revision:
    source_nodes = list(
        (
            await db.execute(
                select(BOQV2ScopeNode).where(
                    BOQV2ScopeNode.revision_id == source_revision.id
                )
            )
        )
        .scalars()
        .all()
    )
    source_plan = await _current_cost_plan(db, source_revision.id)
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

    await _replace_current_working_plan(db, target_project.id)
    cost_plan_version = await _next_cost_plan_version(db, target_project.id)
    revision = BOQV2Revision(
        id=uuid4(),
        document_id=target_document.id,
        project_id=target_project.id,
        predecessor_revision_id=source_revision.id,
        base_baseline_id=base_baseline.id if base_baseline else None,
        base_baseline_version=base_baseline.version if base_baseline else None,
        revision_number=revision_number,
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
    db.add(revision)
    await db.flush()
    plan = BOQV2CostPlan(
        id=uuid4(),
        project_id=target_project.id,
        scope_revision_id=revision.id,
        version=cost_plan_version,
        status="WORKING",
        is_current=True,
        completeness_state=(
            source_plan.completeness_state if source_plan else "INCOMPLETE"
        ),
        required_count=source_revision.required_cost_count,
        priced_count=source_revision.priced_cost_count,
        original_estimated_cost=None,
        agreed_cost=None,
        forecast_cost=source_revision.forecast_cost,
        calculation_version=source_revision.calculation_version,
        created_by=actor,
    )
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
    return revision


async def revise_quotation(
    db: AsyncSession,
    *,
    revision_id: UUID,
    request: BOQV2ExpectedVersionRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2RevisionResponse:
    source, document, project = await _revision_context(db, revision_id)
    await acquire_project_budget_locks(db, [source.project_id])
    source, document, project = await _revision_context(
        db, revision_id, for_update=True
    )
    assert_expected_version(current=source.version, expected=request.expected_version)
    if source.status not in {"ISSUED", "ACCEPTED", "REJECTED", "WITHDRAWN"}:
        raise BOQDomainError(
            "INVALID_REVISION_SOURCE",
            "A revision can be created only from issued or closed quotation history",
        )
    command, prior_revision_id = await _begin_command(
        db,
        actor=actor,
        project_id=source.project_id,
        command_type="REVISE_QUOTATION",
        idempotency_key=idempotency_key,
        payload={
            "source_revision_id": str(source.id),
            "expected_version": request.expected_version,
        },
    )
    if prior_revision_id is not None:
        return await load_boq_revision(db, prior_revision_id)
    active = (
        await _active_baseline(db, source.project_id, for_update=True)
        if document.document_kind == "CHANGE_ORDER"
        else None
    )
    next_number = await next_revision_number(db, document_id=document.id)
    revision = await _clone_revision(
        db,
        source_revision=source,
        target_document=document,
        target_project=project,
        revision_number=next_number,
        actor=actor,
        base_baseline=active,
    )
    if document.document_kind == "CHANGE_ORDER" and document.direction == "DEDUCT":
        source_deductions = list(
            (
                await db.execute(
                    select(BOQV2ChangeOrderDeduction).where(
                        BOQV2ChangeOrderDeduction.revision_id == source.id
                    )
                )
            )
            .scalars()
            .all()
        )
        if active is None:
            raise BOQDomainError(
                "ACTIVE_BASELINE_REQUIRED",
                "A change-order revision requires an active baseline",
            )
        for item in source_deductions:
            db.add(
                BOQV2ChangeOrderDeduction(
                    id=uuid4(),
                    project_id=item.project_id,
                    document_id=document.id,
                    revision_id=revision.id,
                    base_baseline_id=active.id,
                    base_baseline_version=active.version,
                    target_revision_id=item.target_revision_id,
                    target_logical_id=item.target_logical_id,
                    quantity=item.quantity,
                    unit_rate=item.unit_rate,
                    amount=item.amount,
                )
            )
    _complete_command(command, revision_id=revision.id, version=revision.version)
    _audit(
        db,
        command=command,
        actor=actor,
        project_id=revision.project_id,
        command_type="REVISE_QUOTATION",
        entity_type="BOQ_REVISION",
        entity_id=revision.id,
        before={"source_revision_id": str(source.id), "status": source.status},
        after={"status": "DRAFT", "revision_number": revision.revision_number},
    )
    await db.flush()
    return await load_boq_revision(db, revision.id)


async def create_alternative(
    db: AsyncSession,
    *,
    revision_id: UUID,
    request: BOQV2CreateAlternativeRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2RevisionResponse:
    source, source_document, project = await _revision_context(db, revision_id)
    await acquire_project_budget_locks(db, [source.project_id])
    source, source_document, project = await _revision_context(
        db, revision_id, for_update=True
    )
    assert_expected_version(current=source.version, expected=request.expected_version)
    command, prior_revision_id = await _begin_command(
        db,
        actor=actor,
        project_id=source.project_id,
        command_type="CREATE_ALTERNATIVE",
        idempotency_key=idempotency_key,
        payload={
            "source_revision_id": str(source.id),
            **request.model_dump(mode="json"),
        },
    )
    if prior_revision_id is not None:
        return await load_boq_revision(db, prior_revision_id)
    group_id = (
        request.alternative_group_id
        or source_document.alternative_group_id
        or source_document.id
    )
    document = BOQV2Document(
        id=uuid4(),
        project_id=source.project_id,
        document_number=await next_document_number(db, document_kind="ALTERNATIVE"),
        document_kind="ALTERNATIVE",
        alternative_group_id=group_id,
        revision_counter=1,
        created_by=actor,
    )
    db.add(document)
    await db.flush()
    revision = await _clone_revision(
        db,
        source_revision=source,
        target_document=document,
        target_project=project,
        revision_number=1,
        actor=actor,
    )
    _complete_command(command, revision_id=revision.id, version=revision.version)
    _audit(
        db,
        command=command,
        actor=actor,
        project_id=revision.project_id,
        command_type="CREATE_ALTERNATIVE",
        entity_type="BOQ_DOCUMENT",
        entity_id=document.id,
        before={"source_revision_id": str(source.id)},
        after={
            "revision_id": str(revision.id),
            "alternative_group_id": str(group_id),
        },
    )
    await db.flush()
    return await load_boq_revision(db, revision.id)


async def _member_snapshot_map(
    db: AsyncSession,
    baseline: BOQV2ProjectBaseline,
) -> dict[UUID, BOQV2RevisionSnapshot]:
    result: dict[UUID, BOQV2RevisionSnapshot] = {}
    if baseline.main_snapshot_id is None:
        raise BOQDomainError(
            "BASELINE_SNAPSHOT_MISSING", "Active baseline has no main snapshot"
        )
    main_snapshot = (
        await db.execute(
            select(BOQV2RevisionSnapshot).where(
                BOQV2RevisionSnapshot.id == baseline.main_snapshot_id
            )
        )
    ).scalar_one()
    result[baseline.main_revision_id] = main_snapshot
    for membership in await _baseline_memberships(db, baseline.id):
        snapshot = (
            await db.execute(
                select(BOQV2RevisionSnapshot).where(
                    BOQV2RevisionSnapshot.id == membership.snapshot_id
                )
            )
        ).scalar_one()
        result[membership.revision_id] = snapshot
    return result


def _snapshot_item(
    snapshot: BOQV2RevisionSnapshot,
    logical_id: UUID,
) -> dict[str, object] | None:
    for node in snapshot.customer_payload.get("scope", []):
        if (
            node.get("node_kind") == "ITEM"
            and node.get("inclusion_state") != "EXCLUDED"
            and str(node.get("logical_id")) == str(logical_id)
        ):
            return dict(node)
    return None


async def create_change_order(
    db: AsyncSession,
    *,
    project_id: UUID,
    request: BOQV2CreateChangeOrderRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2RevisionResponse:
    await acquire_project_budget_locks(db, [project_id])
    project = await _project_or_error(db, project_id)
    baseline = await _active_baseline(db, project_id, for_update=True)
    if baseline is None:
        raise BOQDomainError(
            "ACTIVE_BASELINE_REQUIRED", "A change order requires an accepted baseline"
        )
    if baseline.id != request.baseline_id or baseline.version != request.baseline_version:
        raise BOQDomainError(
            "STALE_BASELINE_VERSION",
            "The active baseline changed; reload before creating a change order",
        )
    command, prior_revision_id = await _begin_command(
        db,
        actor=actor,
        project_id=project_id,
        command_type="CREATE_CHANGE_ORDER",
        idempotency_key=idempotency_key,
        payload={"project_id": str(project_id), **request.model_dump(mode="json")},
    )
    if prior_revision_id is not None:
        return await load_boq_revision(db, prior_revision_id)

    document = BOQV2Document(
        id=uuid4(),
        project_id=project_id,
        document_number=await next_document_number(
            db, document_kind="CHANGE_ORDER"
        ),
        document_kind="CHANGE_ORDER",
        direction=request.direction,
        base_baseline_id=baseline.id,
        base_baseline_version=baseline.version,
        revision_counter=1,
        created_by=actor,
    )
    revision = BOQV2Revision(
        id=uuid4(),
        document_id=document.id,
        project_id=project_id,
        base_baseline_id=baseline.id,
        base_baseline_version=baseline.version,
        revision_number=1,
        status="DRAFT",
        version=1,
        calculation_version=CALCULATION_VERSION,
        quotation_title=f"Change order {request.direction}",
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
    db.add(document)
    await db.flush()
    db.add(revision)
    await db.flush()
    await _replace_current_working_plan(db, project_id)
    plan = BOQV2CostPlan(
        id=uuid4(),
        project_id=project_id,
        scope_revision_id=revision.id,
        version=await _next_cost_plan_version(db, project_id),
        status="WORKING",
        is_current=True,
        completeness_state="COMPLETE",
        required_count=0,
        priced_count=0,
        forecast_cost=ZERO_MONEY,
        calculation_version=CALCULATION_VERSION,
        created_by=actor,
    )
    db.add(plan)
    await db.flush()

    if request.direction == "DEDUCT":
        snapshots = await _member_snapshot_map(db, baseline)
        member_ids = set(snapshots)
        accepted_deductions = list(
            (
                await db.execute(
                    select(BOQV2ChangeOrderDeduction).where(
                        BOQV2ChangeOrderDeduction.revision_id.in_(member_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        consumed: dict[tuple[UUID, UUID], Decimal] = {}
        for item in accepted_deductions:
            key = (item.target_revision_id, item.target_logical_id)
            consumed[key] = consumed.get(key, ZERO_RATE) + Decimal(item.quantity)
        subtotal = ZERO_MONEY
        for position, deduction in enumerate(request.deductions):
            snapshot = snapshots.get(deduction.target_revision_id)
            if snapshot is None:
                raise BOQDomainError(
                    "CHANGE_ORDER_TARGET_NOT_ACTIVE",
                    "Deduction target is not part of the active baseline",
                )
            source_document = snapshot.customer_payload.get("document", {})
            if source_document.get("direction") == "DEDUCT":
                raise BOQDomainError(
                    "INVALID_DEDUCTION_TARGET",
                    "A deduction cannot target another deduction",
                )
            source_item = _snapshot_item(snapshot, deduction.target_logical_id)
            if source_item is None:
                raise BOQDomainError(
                    "CHANGE_ORDER_TARGET_NOT_FOUND",
                    "Deduction target does not exist in its frozen baseline snapshot",
                )
            available = Decimal(str(source_item.get("quantity") or 0)) - consumed.get(
                (deduction.target_revision_id, deduction.target_logical_id),
                ZERO_RATE,
            )
            if deduction.quantity > available:
                raise BOQDomainError(
                    "DEDUCTION_EXCEEDS_REMAINING_SCOPE",
                    "Deduction quantity exceeds remaining accepted scope",
                )
            material_rate = Decimal(
                str(source_item.get("sell_material_unit_rate") or 0)
            )
            labor_rate = Decimal(str(source_item.get("sell_labor_unit_rate") or 0))
            unit_rate = material_rate + labor_rate
            amount = money(deduction.quantity * unit_rate)
            row_id = uuid4()
            db.add(
                BOQV2ScopeNode(
                    id=row_id,
                    logical_id=deduction.target_logical_id,
                    revision_id=revision.id,
                    project_id=project_id,
                    parent_id=None,
                    node_kind="ITEM",
                    inclusion_state="REQUIRED",
                    position=position,
                    item_code=source_item.get("item_code"),
                    description=source_item.get("description"),
                    specification=source_item.get("specification"),
                    quantity=deduction.quantity,
                    unit=source_item.get("unit"),
                    sell_material_unit_rate=material_rate,
                    sell_labor_unit_rate=labor_rate,
                    sell_total=amount,
                )
            )
            db.add(
                BOQV2ChangeOrderDeduction(
                    id=uuid4(),
                    project_id=project_id,
                    document_id=document.id,
                    revision_id=revision.id,
                    base_baseline_id=baseline.id,
                    base_baseline_version=baseline.version,
                    target_revision_id=deduction.target_revision_id,
                    target_logical_id=deduction.target_logical_id,
                    quantity=deduction.quantity,
                    unit_rate=unit_rate,
                    amount=amount,
                )
            )
            subtotal += amount
        revision.subtotal = money(subtotal)
        revision.net_sell_ex_vat = money(subtotal)
        revision.vat_amount = money(
            revision.net_sell_ex_vat * Decimal(revision.vat_rate) / Decimal("100")
        )
        revision.grand_total = money(
            revision.net_sell_ex_vat + revision.vat_amount
        )
    _complete_command(command, revision_id=revision.id, version=revision.version)
    _audit(
        db,
        command=command,
        actor=actor,
        project_id=project_id,
        command_type="CREATE_CHANGE_ORDER",
        entity_type="BOQ_DOCUMENT",
        entity_id=document.id,
        before={
            "baseline_id": str(baseline.id),
            "baseline_version": baseline.version,
        },
        after={
            "revision_id": str(revision.id),
            "direction": request.direction,
            "deduction_count": len(request.deductions),
        },
    )
    await db.flush()
    return await load_boq_revision(db, revision.id)


async def _validate_replacement(
    db: AsyncSession,
    *,
    active: BOQV2ProjectBaseline,
    decision: BOQV2ReplacementDecision | None,
) -> tuple[list[BOQV2BaselineChangeOrder], list[BOQV2BaselineChangeOrder]]:
    if decision is None:
        raise BOQDomainError(
            "BASELINE_REPLACEMENT_CONFIRMATION_REQUIRED",
            "Replacing an accepted MAIN requires explicit retain/absorb decisions",
        )
    if decision.baseline_id != active.id or decision.baseline_version != active.version:
        raise BOQDomainError(
            "STALE_BASELINE_VERSION",
            "The active baseline changed; reload replacement impact",
        )
    memberships = await _baseline_memberships(db, active.id)
    by_revision = {item.revision_id: item for item in memberships}
    retain_ids = set(decision.retain_change_order_revision_ids)
    absorb_ids = set(decision.absorb_change_order_revision_ids)
    if retain_ids.union(absorb_ids) != set(by_revision):
        raise BOQDomainError(
            "CHANGE_ORDER_REPLACEMENT_MAPPING_INCOMPLETE",
            "Every active change order must be explicitly retained or absorbed",
        )
    return (
        [by_revision[item] for item in decision.retain_change_order_revision_ids],
        [by_revision[item] for item in decision.absorb_change_order_revision_ids],
    )


async def _validate_deductions_for_acceptance(
    db: AsyncSession,
    *,
    revision: BOQV2Revision,
    document: BOQV2Document,
    active: BOQV2ProjectBaseline,
) -> None:
    if document.direction != "DEDUCT":
        return
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
    if not deductions:
        raise BOQDomainError(
            "DEDUCTION_TARGET_REQUIRED", "DEDUCT change order has no target lines"
        )
    snapshots = await _member_snapshot_map(db, active)
    memberships = await _baseline_memberships(db, active.id)
    existing_same_document = {
        item.revision_id
        for item in memberships
        if item.document_id == document.id
    }
    accepted_ids = set(snapshots) - existing_same_document
    accepted = list(
        (
            await db.execute(
                select(BOQV2ChangeOrderDeduction).where(
                    BOQV2ChangeOrderDeduction.revision_id.in_(accepted_ids)
                )
            )
        )
        .scalars()
        .all()
    )
    consumed: dict[tuple[UUID, UUID], Decimal] = {}
    for item in accepted:
        key = (item.target_revision_id, item.target_logical_id)
        consumed[key] = consumed.get(key, ZERO_RATE) + Decimal(item.quantity)
    for item in deductions:
        snapshot = snapshots.get(item.target_revision_id)
        source = _snapshot_item(snapshot, item.target_logical_id) if snapshot else None
        if source is None:
            raise BOQDomainError(
                "CHANGE_ORDER_TARGET_NOT_ACTIVE",
                "Deduction target is no longer in the active baseline",
            )
        remaining = Decimal(str(source.get("quantity") or 0)) - consumed.get(
            (item.target_revision_id, item.target_logical_id), ZERO_RATE
        )
        if Decimal(item.quantity) > remaining:
            raise BOQDomainError(
                "DEDUCTION_EXCEEDS_REMAINING_SCOPE",
                "Deduction exceeds remaining scope after accepted change orders",
            )


async def _next_baseline(
    db: AsyncSession,
    *,
    project_id: UUID,
    previous: BOQV2ProjectBaseline | None,
    main_revision: BOQV2Revision,
    main_snapshot: BOQV2RevisionSnapshot,
    memberships: list[BOQV2BaselineChangeOrder],
    actor: str,
    now: datetime,
) -> BOQV2ProjectBaseline:
    main_value = money(main_revision.net_sell_ex_vat or 0)
    net_value = main_value
    membership_rows: list[
        tuple[BOQV2BaselineChangeOrder, BOQV2Revision, BOQV2Document]
    ] = []
    for membership in memberships:
        row = (
            await db.execute(
                select(BOQV2Revision, BOQV2Document)
                .join(
                    BOQV2Document,
                    BOQV2Document.id == BOQV2Revision.document_id,
                )
                .where(BOQV2Revision.id == membership.revision_id)
            )
        ).one()
        revision, document = row
        net_value += signed_change_order_amount(
            document.direction, revision.net_sell_ex_vat or 0
        )
        membership_rows.append((membership, revision, document))
    if net_value < ZERO_MONEY:
        raise BOQDomainError(
            "BASELINE_NET_NEGATIVE", "Accepted changes cannot make the baseline negative"
        )
    if previous is not None:
        previous.is_active = False
        previous.effective_to = now
    next_version = previous.version + 1 if previous else 1
    baseline = BOQV2ProjectBaseline(
        id=uuid4(),
        project_id=project_id,
        version=next_version,
        main_revision_id=main_revision.id,
        main_snapshot_id=main_snapshot.id,
        cost_plan_id=None,
        is_active=True,
        calculation_version=main_revision.calculation_version,
        net_sell_ex_vat=money(net_value),
        original_estimated_cost=(
            main_revision.forecast_cost
            if main_revision.required_cost_count == main_revision.priced_cost_count
            else None
        ),
        agreed_cost=None,
        forecast_cost=None,
        forecast_margin=None,
        activated_at=now,
        effective_from=now,
        effective_to=None,
        created_by=actor,
    )
    db.add(baseline)
    await db.flush()
    for position, (membership, _revision, document) in enumerate(membership_rows):
        db.add(
            BOQV2BaselineChangeOrder(
                id=uuid4(),
                baseline_id=baseline.id,
                revision_id=membership.revision_id,
                document_id=document.id,
                snapshot_id=membership.snapshot_id,
                position=position,
            )
        )
    return baseline


async def _activate_source(
    db: AsyncSession,
    *,
    project_id: UUID,
    actor: str,
    now: datetime,
) -> None:
    statement = (
        insert(BOQV2ProjectBudgetSource)
        .values(
            project_id=project_id,
            source_kind="V2",
            version=1,
            updated_by=actor,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=[BOQV2ProjectBudgetSource.project_id],
            set_={
                "source_kind": "V2",
                "version": BOQV2ProjectBudgetSource.version + 1,
                "updated_by": actor,
                "updated_at": now,
            },
        )
    )
    await db.execute(statement)


async def _acceptance_response(
    db: AsyncSession,
    acceptance: BOQV2Acceptance,
    baseline: BOQV2ProjectBaseline,
) -> BOQV2AcceptanceResponse:
    co_ids = list(
        (
            await db.execute(
                select(BOQV2BaselineChangeOrder.revision_id)
                .where(BOQV2BaselineChangeOrder.baseline_id == baseline.id)
                .order_by(BOQV2BaselineChangeOrder.position)
            )
        ).scalars()
    )
    return BOQV2AcceptanceResponse(
        acceptance_id=acceptance.id,
        revision_id=acceptance.revision_id,
        snapshot_id=acceptance.snapshot_id,
        agreed_date=acceptance.agreed_date,
        actor=acceptance.actor,
        evidence_reference=acceptance.evidence_reference,
        note=acceptance.note,
        recorded_at=_timestamp(acceptance.recorded_at),
        baseline=BOQV2ActiveBaselineResponse(
            baseline_id=baseline.id,
            baseline_version=baseline.version,
            project_id=baseline.project_id,
            main_revision_id=baseline.main_revision_id,
            main_snapshot_id=baseline.main_snapshot_id,
            accepted_change_order_revision_ids=co_ids,
            net_sell_ex_vat=f"{Decimal(baseline.net_sell_ex_vat):.2f}",
            calculation_version=baseline.calculation_version,
            activated_at=_timestamp(baseline.activated_at),
        ),
    )


async def record_acceptance(
    db: AsyncSession,
    *,
    revision_id: UUID,
    request: BOQV2RecordAcceptanceRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2AcceptanceResponse:
    revision, document, _ = await _revision_context(db, revision_id)
    await acquire_project_budget_locks(db, [revision.project_id])
    revision, document, _ = await _revision_context(db, revision_id, for_update=True)
    active = await _active_baseline(db, revision.project_id, for_update=True)
    assert_expected_version(current=revision.version, expected=request.expected_version)
    command, prior_revision_id = await _begin_command(
        db,
        actor=actor,
        project_id=revision.project_id,
        command_type="RECORD_ACCEPTANCE",
        idempotency_key=idempotency_key,
        payload={"revision_id": str(revision_id), **request.model_dump(mode="json")},
    )
    if prior_revision_id is not None:
        prior_acceptance = (
            await db.execute(
                select(BOQV2Acceptance).where(
                    BOQV2Acceptance.revision_id == prior_revision_id
                )
            )
        ).scalar_one()
        current_baseline = await _active_baseline(db, revision.project_id)
        if current_baseline is None:
            raise BOQDomainError(
                "ACTIVE_BASELINE_MISSING", "Accepted quotation has no active baseline"
            )
        return await _acceptance_response(db, prior_acceptance, current_baseline)
    if revision.status != "ISSUED":
        raise BOQDomainError(
            "INVALID_ACCEPTANCE_STATE", "Only an ISSUED revision can be accepted"
        )
    snapshot = await _issue_snapshot(db, revision.id)
    if snapshot is None:
        raise BOQDomainError(
            "ISSUED_SNAPSHOT_MISSING", "Issued quotation snapshot is missing"
        )
    now = datetime.now(UTC)
    retained: list[BOQV2BaselineChangeOrder] = []
    absorbed: list[BOQV2BaselineChangeOrder] = []

    if document.document_kind in {"MAIN", "ALTERNATIVE"}:
        if active is not None and active.main_revision_id != revision.id:
            retained, absorbed = await _validate_replacement(
                db,
                active=active,
                decision=request.replacement,
            )
        baseline = await _next_baseline(
            db,
            project_id=revision.project_id,
            previous=active,
            main_revision=revision,
            main_snapshot=snapshot,
            memberships=retained,
            actor=actor,
            now=now,
        )
        if active is not None and active.main_revision_id != revision.id:
            await db.execute(
                update(BOQV2Revision)
                .where(
                    BOQV2Revision.id == active.main_revision_id,
                    BOQV2Revision.status == "ACCEPTED",
                )
                .values(status="SUPERSEDED", updated_at=now)
            )
    else:
        if active is None:
            raise BOQDomainError(
                "ACTIVE_BASELINE_REQUIRED",
                "A change order cannot be accepted without an active MAIN baseline",
            )
        if (
            revision.base_baseline_id != active.id
            or revision.base_baseline_version != active.version
        ):
            raise BOQDomainError(
                "STALE_BASELINE_VERSION",
                "The active baseline changed; revise the change order explicitly",
            )
        await _validate_deductions_for_acceptance(
            db,
            revision=revision,
            document=document,
            active=active,
        )
        memberships = await _baseline_memberships(db, active.id)
        replaced = [item for item in memberships if item.document_id == document.id]
        kept = [item for item in memberships if item.document_id != document.id]
        synthetic = BOQV2BaselineChangeOrder(
            id=uuid4(),
            baseline_id=active.id,
            revision_id=revision.id,
            document_id=document.id,
            snapshot_id=snapshot.id,
            position=len(kept),
        )
        kept.append(synthetic)
        main_revision = (
            await db.execute(
                select(BOQV2Revision).where(
                    BOQV2Revision.id == active.main_revision_id
                )
            )
        ).scalar_one()
        main_snapshot = (
            await db.execute(
                select(BOQV2RevisionSnapshot).where(
                    BOQV2RevisionSnapshot.id == active.main_snapshot_id
                )
            )
        ).scalar_one()
        baseline = await _next_baseline(
            db,
            project_id=revision.project_id,
            previous=active,
            main_revision=main_revision,
            main_snapshot=main_snapshot,
            memberships=kept,
            actor=actor,
            now=now,
        )
        for item in replaced:
            await db.execute(
                update(BOQV2Revision)
                .where(
                    BOQV2Revision.id == item.revision_id,
                    BOQV2Revision.status == "ACCEPTED",
                )
                .values(status="SUPERSEDED", updated_at=now)
            )

    acceptance = BOQV2Acceptance(
        id=uuid4(),
        project_id=revision.project_id,
        document_id=document.id,
        revision_id=revision.id,
        snapshot_id=snapshot.id,
        agreed_date=request.agreed_date,
        actor=actor,
        evidence_reference=_clean_text(request.evidence_reference),
        note=_clean_text(request.note),
        recorded_at=now,
    )
    db.add(acceptance)
    revision.status = "ACCEPTED"
    revision.version += 1
    revision.updated_at = now
    await _activate_source(
        db,
        project_id=revision.project_id,
        actor=actor,
        now=now,
    )
    _complete_command(command, revision_id=revision.id, version=revision.version)
    _audit(
        db,
        command=command,
        actor=actor,
        project_id=revision.project_id,
        command_type="RECORD_ACCEPTANCE",
        entity_type="BOQ_REVISION",
        entity_id=revision.id,
        before={
            "status": "ISSUED",
            "active_baseline_id": str(active.id) if active else None,
            "active_baseline_version": active.version if active else None,
        },
        after={
            "status": "ACCEPTED",
            "baseline_id": str(baseline.id),
            "baseline_version": baseline.version,
            "snapshot_id": str(snapshot.id),
            "retained_change_order_ids": [str(item.revision_id) for item in retained],
            "absorbed_change_order_ids": [str(item.revision_id) for item in absorbed],
        },
    )
    await db.flush()
    return await _acceptance_response(db, acceptance, baseline)


async def transition_quotation(
    db: AsyncSession,
    *,
    revision_id: UUID,
    action: str,
    request: BOQV2TransitionRequest,
    actor: str,
    idempotency_key: str,
) -> BOQV2RevisionResponse:
    revision, _document, _project = await _revision_context(db, revision_id)
    await acquire_project_budget_locks(db, [revision.project_id])
    revision, _document, _project = await _revision_context(
        db, revision_id, for_update=True
    )
    assert_expected_version(current=revision.version, expected=request.expected_version)
    target = action.upper()
    allowed = {
        "WITHDRAW": ({"DRAFT", "ISSUED"}, "WITHDRAWN"),
        "REJECT": ({"ISSUED"}, "REJECTED"),
    }
    if target not in allowed:
        raise BOQDomainError("INVALID_TRANSITION", "Unsupported quotation transition")
    source_states, next_state = allowed[target]
    if revision.status not in source_states:
        raise BOQDomainError(
            "INVALID_TRANSITION",
            f"Cannot {action.lower()} a {revision.status} revision",
        )
    command_type = f"{target}_QUOTATION"
    command, prior_revision_id = await _begin_command(
        db,
        actor=actor,
        project_id=revision.project_id,
        command_type=command_type,
        idempotency_key=idempotency_key,
        payload={"revision_id": str(revision.id), **request.model_dump(mode="json")},
    )
    if prior_revision_id is not None:
        return await load_boq_revision(db, prior_revision_id)
    before = {"status": revision.status, "version": revision.version}
    revision.status = next_state
    revision.version += 1
    revision.updated_at = datetime.now(UTC)
    _complete_command(command, revision_id=revision.id, version=revision.version)
    _audit(
        db,
        command=command,
        actor=actor,
        project_id=revision.project_id,
        command_type=command_type,
        entity_type="BOQ_REVISION",
        entity_id=revision.id,
        before=before,
        after={"status": next_state, "version": revision.version},
    )
    if request.reason:
        await db.flush()
        audit = (
            await db.execute(
                select(BOQV2AuditEvent).where(
                    BOQV2AuditEvent.event_key == f"{command_type}:{command.id}"
                )
            )
        ).scalar_one()
        audit.reason = _clean_text(request.reason)
    await db.flush()
    return await load_boq_revision(db, revision.id)
