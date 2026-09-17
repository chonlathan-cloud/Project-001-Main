"""Prove archived legacy BOQ finance remains visible without entering active budget."""

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
    value = os.environ.get("PHASE1_DATABASE_URL", "").strip()
    if not value:
        raise SystemExit("PHASE1_DATABASE_URL is required; backend .env is not allowed")
    parsed = urlparse(value)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing non-loopback Phase 1 database")
    if not parsed.path.lstrip("/").endswith("_test"):
        raise SystemExit("Refusing database whose name does not end with _test")
    return value


async def main() -> None:
    database_url = _safe_url()
    os.environ["DATABASE_URL"] = database_url

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.boq import BOQItem, Project
    from app.models.boq_v2 import (
        BOQV2CostPlan,
        BOQV2Document,
        BOQV2ProjectBaseline,
        BOQV2ProjectBudgetSource,
        BOQV2Revision,
    )
    from app.models.finance import Installment, Transaction
    from app.services.chat_analytics_service import (
        _build_project_rollups,
        _load_snapshot,
    )
    from app.services.project_budget_service import load_project_budget_context

    project_id = UUID("73000000-0000-4000-8000-000000000001")
    archived_item_id = UUID("73000000-0000-4000-8000-000000000002")
    active_item_id = UUID("73000000-0000-4000-8000-000000000003")
    installment_id = UUID("73000000-0000-4000-8000-000000000004")

    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        transaction = await session.begin()
        try:
            session.add(
                Project(
                    id=project_id,
                    name="Archived finance proof",
                    project_type="CONSTRUCTION",
                    status="ACTIVE",
                    contingency_budget=Decimal("10.00"),
                )
            )
            session.add_all(
                [
                    BOQItem(
                        id=archived_item_id,
                        project_id=project_id,
                        boq_type="SUBCONTRACTOR",
                        wbs_level=1,
                        description="Archived cost row",
                        grand_total=Decimal("50.00"),
                        total_material=Decimal("50.00"),
                        total_labor=Decimal("0.00"),
                        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
                        valid_to=datetime(2026, 2, 1, tzinfo=UTC),
                    ),
                    BOQItem(
                        id=active_item_id,
                        project_id=project_id,
                        boq_type="SUBCONTRACTOR",
                        wbs_level=1,
                        description="Active budget row",
                        grand_total=Decimal("200.00"),
                        total_material=Decimal("200.00"),
                        total_labor=Decimal("0.00"),
                        valid_from=datetime(2026, 2, 1, tzinfo=UTC),
                        valid_to=None,
                    ),
                ]
            )
            session.add(
                Installment(
                    id=installment_id,
                    boq_item_id=archived_item_id,
                    amount=Decimal("50.00"),
                    status="PENDING",
                    due_date=date(2026, 9, 1),
                )
            )
            session.add(
                Transaction(
                    id=UUID("73000000-0000-4000-8000-000000000005"),
                    installment_id=installment_id,
                    base_amount=Decimal("30.00"),
                    approved_at=datetime(2026, 9, 10, tzinfo=UTC),
                )
            )
            await session.flush()

            snapshot = await _load_snapshot(session, project_id)
            rollup = _build_project_rollups(snapshot, None)[project_id]
            assert {item.id for item in snapshot.boq_items} == {active_item_id}
            assert archived_item_id in snapshot.boq_item_by_id
            assert {item.id for item in snapshot.installments} == {installment_id}
            assert len(snapshot.transactions) == 1
            assert rollup["budget_baseline"] == 200.0
            assert rollup["transaction_cost"] == 30.0
            assert rollup["pending_installment_amount"] == 50.0

            document_id = UUID("73000000-0000-4000-8000-000000000006")
            revision_id = UUID("73000000-0000-4000-8000-000000000007")
            cost_plan_id = UUID("73000000-0000-4000-8000-000000000008")
            activation_time = datetime(2026, 6, 1, tzinfo=UTC)
            session.add(
                BOQV2Document(
                    id=document_id,
                    project_id=project_id,
                    document_number=f"TEST-{document_id}",
                    document_kind="MAIN",
                    direction=None,
                    revision_counter=1,
                    created_by="phase1-test",
                )
            )
            await session.flush()
            session.add(
                BOQV2Revision(
                    id=revision_id,
                    document_id=document_id,
                    project_id=project_id,
                    revision_number=1,
                    status="ACCEPTED",
                    version=1,
                    net_sell_ex_vat=Decimal("500.00"),
                    known_estimated_cost=Decimal("300.00"),
                    forecast_cost=Decimal("300.00"),
                    forecast_margin=Decimal("200.00"),
                    required_cost_count=0,
                    priced_cost_count=0,
                    created_by="phase1-test",
                )
            )
            await session.flush()
            session.add(
                BOQV2CostPlan(
                    id=cost_plan_id,
                    project_id=project_id,
                    scope_revision_id=revision_id,
                    version=1,
                    status="PUBLISHED",
                    is_current=True,
                    completeness_state="COMPLETE",
                    required_count=0,
                    priced_count=0,
                    original_estimated_cost=Decimal("300.00"),
                    forecast_cost=Decimal("300.00"),
                    published_at=activation_time,
                    created_by="phase1-test",
                )
            )
            await session.flush()
            session.add(
                BOQV2ProjectBaseline(
                    id=UUID("73000000-0000-4000-8000-000000000009"),
                    project_id=project_id,
                    version=1,
                    main_revision_id=revision_id,
                    cost_plan_id=cost_plan_id,
                    is_active=True,
                    net_sell_ex_vat=Decimal("500.00"),
                    original_estimated_cost=Decimal("300.00"),
                    forecast_cost=Decimal("300.00"),
                    forecast_margin=Decimal("200.00"),
                    activated_at=activation_time,
                    effective_from=activation_time,
                    created_by="phase1-test",
                )
            )
            session.add(
                BOQV2ProjectBudgetSource(
                    project_id=project_id,
                    source_kind="V2",
                    version=1,
                    updated_by="phase1-test",
                    updated_at=activation_time,
                )
            )
            await session.flush()

            current_context = await load_project_budget_context(session, project_id)
            before_context = await load_project_budget_context(
                session, project_id, as_of=datetime(2026, 5, 1, tzinfo=UTC)
            )
            after_context = await load_project_budget_context(
                session, project_id, as_of=datetime(2026, 7, 1, tzinfo=UTC)
            )
            assert current_context is not None
            assert before_context is not None
            assert after_context is not None
            assert current_context.snapshot.source_kind == "V2"
            assert current_context.snapshot.status == "READY"
            assert current_context.snapshot.forecast_margin == "200.00"
            assert before_context.snapshot.source_kind == "LEGACY"
            assert after_context.snapshot.source_kind == "V2"
            assert (
                current_context.legacy_chat_budget
                == before_context.legacy_chat_budget
                == after_context.legacy_chat_budget
                == "200.00"
            )
        finally:
            await transaction.rollback()
    await engine.dispose()
    print(
        "Archived BOQ finance and as-of budget source verified: "
        "active budget isolated, history preserved"
    )


if __name__ == "__main__":
    asyncio.run(main())
