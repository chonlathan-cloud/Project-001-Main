"""Rehearse one-project legacy-to-V2 cutover in an isolated rollback transaction."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _safe_url() -> str:
    value = os.environ.get("PHASE5_DATABASE_URL", "").strip()
    if not value:
        raise SystemExit("PHASE5_DATABASE_URL is required; backend .env is not allowed")
    parsed = urlparse(value)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing non-loopback Phase 5 database")
    if not parsed.path.lstrip("/").endswith("_test"):
        raise SystemExit("Refusing database whose name does not end with _test")
    return value


async def main() -> None:
    database_url = _safe_url()
    os.environ["DATABASE_URL"] = database_url

    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import Settings
    from app.models.boq import BOQItem, Project
    from app.models.boq_v2 import (
        BOQV2BaselineChangeOrder,
        BOQV2CostPlan,
        BOQV2Document,
        BOQV2ProjectBaseline,
        BOQV2Revision,
        BOQV2RevisionSnapshot,
        BOQV2ScopeNode,
    )
    from app.models.finance import Installment, Transaction
    from app.services.boq_quotation_service import _activate_source
    from app.services.mcp_read_service import (
        _v2_boq_manifests,
        _v2_line_id,
        _v2_snapshot,
    )
    from app.services.project_budget_service import (
        active_budget_amount,
        load_project_budget_context,
    )

    ids = {
        "project": UUID("75000000-0000-4000-8000-000000000001"),
        "legacy_archived": UUID("75000000-0000-4000-8000-000000000002"),
        "legacy_active": UUID("75000000-0000-4000-8000-000000000003"),
        "installment": UUID("75000000-0000-4000-8000-000000000004"),
        "transaction": UUID("75000000-0000-4000-8000-000000000005"),
        "main_document": UUID("75000000-0000-4000-8000-000000000010"),
        "main_revision": UUID("75000000-0000-4000-8000-000000000011"),
        "main_snapshot": UUID("75000000-0000-4000-8000-000000000012"),
        "cost_plan": UUID("75000000-0000-4000-8000-000000000013"),
        "baseline": UUID("75000000-0000-4000-8000-000000000014"),
        "add_document": UUID("75000000-0000-4000-8000-000000000020"),
        "add_revision": UUID("75000000-0000-4000-8000-000000000021"),
        "add_snapshot": UUID("75000000-0000-4000-8000-000000000022"),
        "deduct_document": UUID("75000000-0000-4000-8000-000000000030"),
        "deduct_revision": UUID("75000000-0000-4000-8000-000000000031"),
        "deduct_snapshot": UUID("75000000-0000-4000-8000-000000000032"),
        "main_logical": UUID("75000000-0000-4000-8000-000000000040"),
    }
    activation_time = datetime(2026, 9, 18, 3, 0, tzinfo=UTC)
    before_activation = datetime(2026, 9, 17, 3, 0, tzinfo=UTC)
    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        transaction = await session.begin()
        try:
            session.add(
                Project(
                    id=ids["project"],
                    name="Phase 5 same-project cutover",
                    project_type="CONSTRUCTION",
                    status="ACTIVE",
                    contingency_budget=Decimal("10000.00"),
                )
            )
            session.add_all(
                [
                    BOQItem(
                        id=ids["legacy_archived"],
                        project_id=ids["project"],
                        boq_type="CUSTOMER",
                        wbs_level=1,
                        item_no="OLD",
                        description="Historical legacy line",
                        grand_total=Decimal("100000.00"),
                        total_material=Decimal("100000.00"),
                        total_labor=Decimal("0.00"),
                        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
                        valid_to=datetime(2026, 2, 1, tzinfo=UTC),
                    ),
                    BOQItem(
                        id=ids["legacy_active"],
                        project_id=ids["project"],
                        boq_type="CUSTOMER",
                        wbs_level=1,
                        item_no="CURRENT",
                        description="Legacy active budget",
                        grand_total=Decimal("900000.00"),
                        total_material=Decimal("900000.00"),
                        total_labor=Decimal("0.00"),
                        valid_from=datetime(2026, 2, 1, tzinfo=UTC),
                        valid_to=None,
                    ),
                ]
            )
            session.add(
                Installment(
                    id=ids["installment"],
                    boq_item_id=ids["legacy_archived"],
                    amount=Decimal("100000.00"),
                    status="PAID",
                    due_date=date(2026, 3, 1),
                )
            )
            session.add(
                Transaction(
                    id=ids["transaction"],
                    installment_id=ids["installment"],
                    base_amount=Decimal("95000.00"),
                    net_payable=Decimal("95000.00"),
                    approved_at=datetime(2026, 3, 2, tzinfo=UTC),
                )
            )
            await session.flush()

            before = await load_project_budget_context(session, ids["project"])
            assert before is not None
            assert before.snapshot.source_kind == "LEGACY"
            assert active_budget_amount(before, consumer="PROJECT_LIST") == "900000.00"

            session.add(
                BOQV2Document(
                    id=ids["main_document"],
                    project_id=ids["project"],
                    document_number="Q-TEST-MAIN",
                    document_kind="MAIN",
                    revision_counter=1,
                    created_by="phase5-owner",
                )
            )
            await session.flush()
            session.add(
                BOQV2Revision(
                    id=ids["main_revision"],
                    document_id=ids["main_document"],
                    project_id=ids["project"],
                    revision_number=1,
                    status="ACCEPTED",
                    version=1,
                    net_sell_ex_vat=Decimal("1200000.00"),
                    known_estimated_cost=Decimal("850000.00"),
                    forecast_cost=Decimal("850000.00"),
                    forecast_margin=Decimal("350000.00"),
                    required_cost_count=0,
                    priced_cost_count=0,
                    created_by="phase5-owner",
                )
            )
            await session.flush()
            session.add(
                BOQV2RevisionSnapshot(
                    id=ids["main_snapshot"],
                    project_id=ids["project"],
                    document_id=ids["main_document"],
                    revision_id=ids["main_revision"],
                    source_version=1,
                    purpose="ISSUE",
                    lifecycle_status="ISSUED",
                    calculation_version="boq-v2-calc-v1",
                    customer_payload={},
                    internal_payload={},
                    payload_sha256="0" * 64,
                    created_by="phase5-owner",
                )
            )
            session.add(
                BOQV2CostPlan(
                    id=ids["cost_plan"],
                    project_id=ids["project"],
                    scope_revision_id=ids["main_revision"],
                    version=1,
                    status="PUBLISHED",
                    is_current=True,
                    completeness_state="COMPLETE",
                    required_count=0,
                    priced_count=0,
                    original_estimated_cost=Decimal("900000.00"),
                    forecast_cost=Decimal("900000.00"),
                    published_at=activation_time,
                    created_by="phase5-owner",
                )
            )
            await session.flush()
            session.add(
                BOQV2ProjectBaseline(
                    id=ids["baseline"],
                    project_id=ids["project"],
                    version=1,
                    main_revision_id=ids["main_revision"],
                    main_snapshot_id=ids["main_snapshot"],
                    cost_plan_id=ids["cost_plan"],
                    is_active=True,
                    calculation_version="boq-v2-calc-v1",
                    net_sell_ex_vat=Decimal("1250000.00"),
                    original_estimated_cost=Decimal("900000.00"),
                    forecast_cost=Decimal("900000.00"),
                    forecast_margin=Decimal("350000.00"),
                    activated_at=activation_time,
                    effective_from=activation_time,
                    created_by="phase5-owner",
                )
            )
            await session.flush()

            co_specs = [
                ("add", "ADD", Decimal("100000.00"), 0),
                ("deduct", "DEDUCT", Decimal("50000.00"), 1),
            ]
            for key, direction, amount, position in co_specs:
                session.add(
                    BOQV2Document(
                        id=ids[f"{key}_document"],
                        project_id=ids["project"],
                        document_number=f"CO-TEST-{direction}",
                        document_kind="CHANGE_ORDER",
                        direction=direction,
                        base_baseline_id=ids["baseline"],
                        base_baseline_version=1,
                        revision_counter=1,
                        created_by="phase5-owner",
                    )
                )
                await session.flush()
                session.add(
                    BOQV2Revision(
                        id=ids[f"{key}_revision"],
                        document_id=ids[f"{key}_document"],
                        project_id=ids["project"],
                        base_baseline_id=ids["baseline"],
                        base_baseline_version=1,
                        revision_number=1,
                        status="ACCEPTED",
                        version=1,
                        net_sell_ex_vat=amount,
                        required_cost_count=0,
                        priced_cost_count=0,
                        created_by="phase5-owner",
                    )
                )
                await session.flush()
                session.add(
                    BOQV2RevisionSnapshot(
                        id=ids[f"{key}_snapshot"],
                        project_id=ids["project"],
                        document_id=ids[f"{key}_document"],
                        revision_id=ids[f"{key}_revision"],
                        source_version=1,
                        purpose="ISSUE",
                        lifecycle_status="ISSUED",
                        calculation_version="boq-v2-calc-v1",
                        customer_payload={},
                        internal_payload={},
                        payload_sha256=str(position + 1) * 64,
                        created_by="phase5-owner",
                    )
                )
                await session.flush()
                session.add(
                    BOQV2BaselineChangeOrder(
                        baseline_id=ids["baseline"],
                        revision_id=ids[f"{key}_revision"],
                        document_id=ids[f"{key}_document"],
                        snapshot_id=ids[f"{key}_snapshot"],
                        position=position,
                    )
                )
            session.add(
                BOQV2ScopeNode(
                    logical_id=ids["main_logical"],
                    revision_id=ids["main_revision"],
                    project_id=ids["project"],
                    node_kind="ITEM",
                    inclusion_state="REQUIRED",
                    position=0,
                    item_code="MAIN-1",
                    description="Accepted main scope",
                    quantity=Decimal("1.0000"),
                    unit="LS",
                    sell_material_unit_rate=Decimal("1200000.0000"),
                    sell_labor_unit_rate=Decimal("0.0000"),
                    sell_total=Decimal("1200000.00"),
                )
            )
            await session.flush()

            legacy_ids_before = set(
                (
                    await session.execute(
                        select(BOQItem.id).where(BOQItem.project_id == ids["project"])
                    )
                ).scalars()
            )
            finance_ids_before = set(
                (
                    await session.execute(
                        select(Transaction.id)
                        .join(Installment, Installment.id == Transaction.installment_id)
                        .join(BOQItem, BOQItem.id == Installment.boq_item_id)
                        .where(BOQItem.project_id == ids["project"])
                    )
                ).scalars()
            )
            assert legacy_ids_before == {ids["legacy_archived"], ids["legacy_active"]}
            assert finance_ids_before == {ids["transaction"]}

            await _activate_source(
                session,
                project_id=ids["project"],
                actor="owner@example.test",
                now=activation_time,
            )
            await session.flush()

            current = await load_project_budget_context(session, ids["project"])
            historical = await load_project_budget_context(
                session, ids["project"], as_of=before_activation
            )
            assert current is not None and historical is not None
            assert current.snapshot.source_kind == "V2"
            assert current.snapshot.status == "READY"
            assert current.snapshot.baseline_id == ids["baseline"]
            assert current.snapshot.baseline_version == 1
            assert current.snapshot.accepted_change_order_ids == [
                ids["add_revision"],
                ids["deduct_revision"],
            ]
            assert current.snapshot.cost_plan_version == 1
            assert current.snapshot.cost_completeness.state == "COMPLETE"
            assert active_budget_amount(current, consumer="PROJECT_LIST") == "1250000.00"
            assert active_budget_amount(current, consumer="FUNDS") == "350000.00"
            assert historical.snapshot.source_kind == "LEGACY"
            assert active_budget_amount(historical, consumer="PROJECT_LIST") == "900000.00"

            manifests = await _v2_boq_manifests(session, ids["project"])
            assert [manifest["version_id"] for manifest in manifests] == [
                f"boqv2_{ids['baseline'].hex}"
            ]
            project = await session.get(Project, ids["project"])
            assert project is not None
            mcp_snapshot = await _v2_snapshot(
                session,
                project,
                manifests[0],
                Settings(
                    _env_file=None,
                    APP_ENV="test",
                    JWT_SECRET_KEY="phase5-cutover-test",
                    MCP_CURSOR_SECRET="phase5-cutover-cursor",
                ),
                budget_snapshot=current.snapshot.model_dump(mode="json"),
            )
            assert mcp_snapshot["source_kind"] == "V2"
            assert mcp_snapshot["version"]["baseline_id"] == str(ids["baseline"])
            assert mcp_snapshot["lines"][0]["line_id"] == _v2_line_id(
                ids["main_document"], ids["main_logical"]
            )

            legacy_ids_after = set(
                (
                    await session.execute(
                        select(BOQItem.id).where(BOQItem.project_id == ids["project"])
                    )
                ).scalars()
            )
            finance_ids_after = set(
                (
                    await session.execute(
                        select(Transaction.id)
                        .join(Installment, Installment.id == Transaction.installment_id)
                        .join(BOQItem, BOQItem.id == Installment.boq_item_id)
                        .where(BOQItem.project_id == ids["project"])
                    )
                ).scalars()
            )
            installment_count = await session.scalar(
                select(func.count()).select_from(Installment).where(
                    Installment.id == ids["installment"]
                )
            )
            assert legacy_ids_after == legacy_ids_before
            assert finance_ids_after == finance_ids_before
            assert installment_count == 1
            assert current.snapshot.net_sell_ex_vat != before.snapshot.net_sell_ex_vat
            assert Decimal(current.snapshot.net_sell_ex_vat or "0") != Decimal(
                before.snapshot.net_sell_ex_vat or "0"
            ) + Decimal(current.snapshot.net_sell_ex_vat or "0")
        finally:
            await transaction.rollback()
    await engine.dispose()
    print(
        "Phase 5 cutover verified: one project, owner source switch, V2 replaces legacy, "
        "MAIN+ADD+DEDUCT active, finance/history IDs preserved, as-of remains legacy"
    )


if __name__ == "__main__":
    asyncio.run(main())
