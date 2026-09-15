"""Verify source-aware Funds compatibility and the V2 unknown-cost gate."""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4


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

    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.boq import BOQItem, Project
    from app.models.boq_v2 import (
        BOQV2Document,
        BOQV2ProjectBaseline,
        BOQV2ProjectBudgetSource,
        BOQV2Revision,
    )
    from app.models.funds import (
        FundAllocation,
        FundAuditEvent,
        FundBucket,
        FundLedgerEntry,
    )
    from app.services.fund_service import (
        FundDomainError,
        calculate_fund_summary,
        post_allocation,
        reverse_allocation,
    )

    source_project_id = uuid4()
    target_project_id = uuid4()
    source_bucket_id = uuid4()
    target_bucket_id = uuid4()
    document_id = uuid4()
    revision_id = uuid4()
    baseline_id = uuid4()
    engine = create_async_engine(database_url, pool_pre_ping=True)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def cleanup() -> None:
        async with factory() as session, session.begin():
            allocation_ids = (
                select(FundAllocation.id)
                .where(
                    FundAllocation.source_bucket_id.in_(
                        [source_bucket_id, target_bucket_id]
                    )
                )
                .scalar_subquery()
            )
            await session.execute(
                delete(FundAuditEvent).where(
                    (FundAuditEvent.allocation_id.in_(allocation_ids))
                    | FundAuditEvent.bucket_id.in_([source_bucket_id, target_bucket_id])
                )
            )
            await session.execute(
                delete(FundLedgerEntry).where(
                    FundLedgerEntry.bucket_id.in_([source_bucket_id, target_bucket_id])
                )
            )
            await session.execute(
                delete(FundAllocation).where(
                    FundAllocation.source_bucket_id.in_(
                        [source_bucket_id, target_bucket_id]
                    )
                )
            )
            await session.execute(
                delete(BOQV2ProjectBaseline).where(
                    BOQV2ProjectBaseline.project_id == target_project_id
                )
            )
            await session.execute(
                delete(BOQV2ProjectBudgetSource).where(
                    BOQV2ProjectBudgetSource.project_id == target_project_id
                )
            )
            await session.execute(
                delete(BOQV2Revision).where(BOQV2Revision.id == revision_id)
            )
            await session.execute(
                delete(BOQV2Document).where(BOQV2Document.id == document_id)
            )
            await session.execute(
                delete(FundBucket).where(
                    FundBucket.id.in_([source_bucket_id, target_bucket_id])
                )
            )
            await session.execute(
                delete(BOQItem).where(
                    BOQItem.project_id.in_([source_project_id, target_project_id])
                )
            )
            await session.execute(
                delete(Project).where(
                    Project.id.in_([source_project_id, target_project_id])
                )
            )

    try:
        async with factory() as session, session.begin():
            session.add_all(
                [
                    Project(
                        id=source_project_id,
                        name="Legacy allocation source",
                        project_type="CONSTRUCTION",
                        status="ACTIVE",
                        contingency_budget=Decimal("0.00"),
                    ),
                    Project(
                        id=target_project_id,
                        name="Unknown V2 allocation target",
                        project_type="CONSTRUCTION",
                        status="ACTIVE",
                        contingency_budget=Decimal("0.00"),
                    ),
                ]
            )
            await session.flush()
            session.add(
                BOQItem(
                    project_id=source_project_id,
                    boq_type="CUSTOMER",
                    wbs_level=1,
                    item_no="1",
                    description="Legacy available margin",
                    grand_total=Decimal("100.00"),
                    total_material=Decimal("100.00"),
                    total_labor=Decimal("0.00"),
                    valid_to=None,
                )
            )
            session.add_all(
                [
                    FundBucket(
                        id=source_bucket_id,
                        project_id=source_project_id,
                        bucket_type="PROJECT",
                        currency="THB",
                        protected_reserve=Decimal("0.00"),
                        status="ACTIVE",
                    ),
                    FundBucket(
                        id=target_bucket_id,
                        project_id=target_project_id,
                        bucket_type="PROJECT",
                        currency="THB",
                        protected_reserve=Decimal("0.00"),
                        status="ACTIVE",
                    ),
                ]
            )
            session.add(
                BOQV2Document(
                    id=document_id,
                    project_id=target_project_id,
                    document_kind="MAIN",
                    created_by="phase1-test",
                )
            )
            await session.flush()
            session.add(
                BOQV2Revision(
                    id=revision_id,
                    document_id=document_id,
                    project_id=target_project_id,
                    revision_number=1,
                    status="ACCEPTED",
                    version=1,
                    net_sell_ex_vat=Decimal("200.00"),
                    required_cost_count=1,
                    priced_cost_count=0,
                    created_by="phase1-test",
                )
            )
            await session.flush()
            activated_at = datetime(2026, 9, 1, tzinfo=UTC)
            session.add_all(
                [
                    BOQV2ProjectBaseline(
                        id=baseline_id,
                        project_id=target_project_id,
                        version=1,
                        main_revision_id=revision_id,
                        cost_plan_id=None,
                        is_active=True,
                        net_sell_ex_vat=Decimal("200.00"),
                        activated_at=activated_at,
                        effective_from=activated_at,
                        created_by="phase1-test",
                    ),
                    BOQV2ProjectBudgetSource(
                        project_id=target_project_id,
                        source_kind="V2",
                        version=1,
                        updated_by="phase1-test",
                        updated_at=activated_at,
                    ),
                ]
            )

        async with factory() as session:
            source_summary = await calculate_fund_summary(session, source_project_id)
            await session.rollback()
            allocation = await post_allocation(
                session,
                source_project_id=source_project_id,
                target_project_id=target_project_id,
                amount=Decimal("10.00"),
                currency="THB",
                reason="Phase 1 incoming gate check",
                note=None,
                expected_source_balance_version=source_summary.version,
                idempotency_key=f"phase1-incoming-{uuid4()}",
                actor="phase1-test",
            )
            await session.rollback()
            try:
                await post_allocation(
                    session,
                    source_project_id=target_project_id,
                    target_project_id=source_project_id,
                    amount=Decimal("1.00"),
                    currency="THB",
                    reason="Must be blocked",
                    note=None,
                    expected_source_balance_version="not-reached",
                    idempotency_key=f"phase1-outward-{uuid4()}",
                    actor="phase1-test",
                )
            except FundDomainError as exc:
                assert exc.code == "BOQ_BUDGET_NOT_READY"
            else:
                raise AssertionError("Unknown V2 cost allowed a new outward allocation")
            await session.rollback()
            reversal = await reverse_allocation(
                session,
                allocation_id=allocation.id,
                reason="Phase 1 correction path check",
                idempotency_key=f"phase1-reversal-{uuid4()}",
                expected_source_balance_version=None,
                actor="phase1-test",
            )
            assert reversal.reversal_of == allocation.id
            assert reversal.amount == Decimal("10.00")
            await session.rollback()
    finally:
        await cleanup()
        await engine.dispose()

    print(
        "Funds verified: incoming to unknown V2 allowed, new outward blocked, "
        "valid reversal allowed"
    )


if __name__ == "__main__":
    asyncio.run(main())
