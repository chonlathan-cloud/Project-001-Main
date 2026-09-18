"""Canonical project-budget snapshots and exact Phase 1 legacy adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Literal, Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.boq import BOQItem, Project
from app.models.boq_v2 import (
    BOQV2BaselineChangeOrder,
    BOQV2CostComponent,
    BOQV2CostPlan,
    BOQV2ProjectBaseline,
    BOQV2ProjectBudgetSource,
)
from app.schemas.project_budget_schema import (
    CostCompleteness,
    ProjectBudgetReadContext,
    ProjectBudgetSnapshot,
)
from app.services.boq_calculation_service import CALCULATION_VERSION
from app.services.boq_domain_service import acquire_project_budget_locks
from app.services.boq_margin_service import projected_boq_totals


ZERO = Decimal("0.00")
MONEY_QUANTUM = Decimal("0.01")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


def _money(value: object) -> Decimal:
    return _decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _money_string(value: object | None) -> str | None:
    if value is None:
        return None
    return str(_money(value))


@dataclass(frozen=True)
class LegacyBudgetFacts:
    project_id: UUID
    contingency_budget: Decimal
    item_count: int
    root_row_count: int
    root_all_total: Decimal
    root_customer_total: Decimal
    dashboard_root_customer_total: Decimal
    dashboard_root_subcontractor_total: Decimal
    projected_customer_total: Decimal
    projected_subcontractor_total: Decimal
    leaf_customer_total: Decimal
    leaf_subcontractor_total: Decimal

    @property
    def project_list_budget(self) -> Decimal:
        return self.root_all_total if self.root_row_count else self.contingency_budget

    @property
    def dashboard_budget(self) -> Decimal:
        return (
            self.dashboard_root_customer_total
            or self.dashboard_root_subcontractor_total
            or self.contingency_budget
        )

    @property
    def fund_forecast_base(self) -> Decimal:
        return _money(
            self.projected_customer_total - self.projected_subcontractor_total
        )

    @property
    def chat_budget(self) -> Decimal:
        return (
            self.leaf_subcontractor_total
            or self.leaf_customer_total
            or self.contingency_budget
        )

    @property
    def mcp_customer_budget(self) -> Decimal:
        return self.root_customer_total


def legacy_budget_facts_from_items(
    *,
    project_id: UUID,
    contingency_budget: object,
    items: Iterable[BOQItem],
) -> LegacyBudgetFacts:
    current_items = list(items)
    roots = [item for item in current_items if item.parent_id is None]
    parent_ids = {
        item.parent_id for item in current_items if item.parent_id is not None
    }
    leaves = [item for item in current_items if item.id not in parent_ids]

    def boq_type(item: BOQItem) -> str:
        return str(item.boq_type or "").strip().upper()

    def legacy_raw_boq_type(item: BOQItem) -> str:
        return str(item.boq_type or "").upper()

    totals = projected_boq_totals(current_items)
    return LegacyBudgetFacts(
        project_id=project_id,
        contingency_budget=_money(contingency_budget),
        item_count=len(current_items),
        root_row_count=len(roots),
        root_all_total=_money(
            sum((_decimal(item.grand_total) for item in roots), ZERO)
        ),
        root_customer_total=_money(
            sum(
                (
                    _decimal(item.grand_total)
                    for item in roots
                    if boq_type(item) == "CUSTOMER"
                ),
                ZERO,
            )
        ),
        dashboard_root_customer_total=_money(
            sum(
                (
                    _decimal(item.grand_total)
                    for item in roots
                    if legacy_raw_boq_type(item) != "SUBCONTRACTOR"
                ),
                ZERO,
            )
        ),
        dashboard_root_subcontractor_total=_money(
            sum(
                (
                    _decimal(item.grand_total)
                    for item in roots
                    if legacy_raw_boq_type(item) == "SUBCONTRACTOR"
                ),
                ZERO,
            )
        ),
        projected_customer_total=_money(totals.customer_total),
        projected_subcontractor_total=_money(totals.subcontractor_total),
        leaf_customer_total=_money(
            sum(
                (
                    _decimal(item.grand_total)
                    for item in leaves
                    if legacy_raw_boq_type(item) != "SUBCONTRACTOR"
                ),
                ZERO,
            )
        ),
        leaf_subcontractor_total=_money(
            sum(
                (
                    _decimal(item.grand_total)
                    for item in leaves
                    if legacy_raw_boq_type(item) == "SUBCONTRACTOR"
                ),
                ZERO,
            )
        ),
    )


async def load_legacy_budget_facts(
    db: AsyncSession,
    project_ids: Sequence[UUID],
    *,
    as_of: datetime | None = None,
) -> dict[UUID, LegacyBudgetFacts]:
    unique_ids = list(dict.fromkeys(project_ids))
    if not unique_ids:
        return {}
    projects = list(
        (
            await db.execute(
                select(Project).options(noload("*")).where(Project.id.in_(unique_ids))
            )
        )
        .scalars()
        .all()
    )
    item_statement = (
        select(BOQItem).options(noload("*")).where(BOQItem.project_id.in_(unique_ids))
    )
    if as_of is None:
        item_statement = item_statement.where(BOQItem.valid_to.is_(None))
    else:
        item_statement = item_statement.where(
            or_(BOQItem.valid_from.is_(None), BOQItem.valid_from <= as_of),
            or_(BOQItem.valid_to.is_(None), BOQItem.valid_to > as_of),
        )
    items = list((await db.execute(item_statement)).scalars().all())
    items_by_project: dict[UUID, list[BOQItem]] = {item: [] for item in unique_ids}
    for item in items:
        items_by_project.setdefault(item.project_id, []).append(item)
    return {
        project.id: legacy_budget_facts_from_items(
            project_id=project.id,
            contingency_budget=project.contingency_budget,
            items=items_by_project.get(project.id, []),
        )
        for project in projects
    }


def _legacy_snapshot(
    facts: LegacyBudgetFacts,
    *,
    as_of: datetime,
) -> ProjectBudgetSnapshot:
    has_data = facts.item_count > 0
    return ProjectBudgetSnapshot(
        source_kind="LEGACY",
        status="READY" if has_data else "NO_BUDGET_DATA",
        project_id=facts.project_id,
        baseline_id=None,
        baseline_version=None,
        main_revision_id=None,
        accepted_change_order_ids=[],
        cost_plan_version=None,
        calculation_version="legacy-scd2-v1",
        activated_at=None,
        net_sell_ex_vat=(
            _money_string(facts.projected_customer_total) if has_data else None
        ),
        original_estimated_cost=None,
        agreed_cost=None,
        forecast_cost=None,
        forecast_margin=None,
        cost_completeness=CostCompleteness(
            state="LEGACY_UNVERIFIED" if has_data else "NOT_APPLICABLE",
            required_count=0,
            priced_count=0,
            missing_component_ids=[],
        ),
        forecast_basis="LEGACY_SYNC" if has_data else "NONE",
        as_of=as_of,
    )


def _context(
    snapshot: ProjectBudgetSnapshot,
    facts: LegacyBudgetFacts,
) -> ProjectBudgetReadContext:
    # Phase 1 public consumers intentionally use these legacy projections even
    # while the canonical internal snapshot is introduced.
    return ProjectBudgetReadContext(
        snapshot=snapshot,
        legacy_project_list_budget=_money_string(facts.project_list_budget) or "0.00",
        legacy_dashboard_budget=_money_string(facts.dashboard_budget) or "0.00",
        legacy_fund_forecast_base=_money_string(facts.fund_forecast_base) or "0.00",
        legacy_chat_budget=_money_string(facts.chat_budget) or "0.00",
        legacy_mcp_customer_budget=_money_string(facts.mcp_customer_budget) or "0.00",
    )


BudgetConsumer = Literal["PROJECT_LIST", "DASHBOARD", "FUNDS", "CHAT", "MCP"]


def active_budget_amount(
    context: ProjectBudgetReadContext,
    *,
    consumer: BudgetConsumer,
) -> str | None:
    """Project one approved active source into a consumer-specific amount.

    Legacy projections intentionally retain the Phase 0 compatibility formulas.
    Once a project is activated on V2, every current-budget reader selects the
    same snapshot: sell-side readers use the active baseline net sell and Funds
    uses its published forecast margin. UNKNOWN_COST remains ``None`` rather
    than being normalized to zero.
    """

    snapshot = context.snapshot
    if snapshot.source_kind == "V2":
        if consumer == "FUNDS":
            return snapshot.forecast_margin if snapshot.status == "READY" else None
        return snapshot.net_sell_ex_vat

    legacy_amounts = {
        "PROJECT_LIST": context.legacy_project_list_budget,
        "DASHBOARD": context.legacy_dashboard_budget,
        "FUNDS": context.legacy_fund_forecast_base,
        "CHAT": context.legacy_chat_budget,
        "MCP": context.legacy_mcp_customer_budget,
    }
    return legacy_amounts[consumer]


def budget_snapshot_payload(context: ProjectBudgetReadContext) -> dict[str, object]:
    """Return the stable public metadata shared by current-budget consumers."""

    return context.snapshot.model_dump(mode="json")


async def load_project_budget_contexts(
    db: AsyncSession,
    project_ids: Sequence[UUID],
    *,
    as_of: datetime | None = None,
) -> dict[UUID, ProjectBudgetReadContext]:
    unique_ids = list(dict.fromkeys(project_ids))
    historical_at = _as_utc(as_of) if as_of is not None else None
    read_at = historical_at or datetime.now(UTC)
    facts_by_project = await load_legacy_budget_facts(
        db, unique_ids, as_of=historical_at
    )
    if not facts_by_project:
        return {}
    source_rows = list(
        (
            await db.execute(
                select(BOQV2ProjectBudgetSource)
                .options(noload("*"))
                .where(BOQV2ProjectBudgetSource.project_id.in_(unique_ids))
            )
        )
        .scalars()
        .all()
    )
    source_by_project = {row.project_id: row for row in source_rows}
    v2_project_ids = [
        project_id
        for project_id, source in source_by_project.items()
        if source.source_kind == "V2"
    ]
    baseline_by_project: dict[UUID, BOQV2ProjectBaseline] = {}
    cost_plan_by_id: dict[UUID, BOQV2CostPlan] = {}
    change_orders_by_baseline: dict[UUID, list[UUID]] = {}
    missing_components_by_plan: dict[UUID, list[UUID]] = {}
    if v2_project_ids:
        baseline_statement = (
            select(BOQV2ProjectBaseline)
            .options(noload("*"))
            .where(BOQV2ProjectBaseline.project_id.in_(v2_project_ids))
        )
        if historical_at is None:
            baseline_statement = baseline_statement.where(
                BOQV2ProjectBaseline.is_active.is_(True)
            )
        else:
            baseline_statement = baseline_statement.where(
                BOQV2ProjectBaseline.effective_from <= historical_at,
                or_(
                    BOQV2ProjectBaseline.effective_to.is_(None),
                    BOQV2ProjectBaseline.effective_to > historical_at,
                ),
            )
        baselines = list((await db.execute(baseline_statement)).scalars().all())
        baseline_by_project = {row.project_id: row for row in baselines}
        cost_plan_ids = [row.cost_plan_id for row in baselines if row.cost_plan_id]
        if cost_plan_ids:
            plans = list(
                (
                    await db.execute(
                        select(BOQV2CostPlan)
                        .options(noload("*"))
                        .where(BOQV2CostPlan.id.in_(cost_plan_ids))
                    )
                )
                .scalars()
                .all()
            )
            cost_plan_by_id = {row.id: row for row in plans}
            missing_component_rows = (
                await db.execute(
                    select(
                        BOQV2CostComponent.cost_plan_id,
                        BOQV2CostComponent.id,
                    ).where(
                        BOQV2CostComponent.cost_plan_id.in_(cost_plan_ids),
                        BOQV2CostComponent.cost_state == "UNKNOWN",
                    )
                )
            ).all()
            for cost_plan_id, component_id in missing_component_rows:
                missing_components_by_plan.setdefault(cost_plan_id, []).append(
                    component_id
                )
        baseline_ids = [row.id for row in baselines]
        if baseline_ids:
            co_rows = (
                await db.execute(
                    select(
                        BOQV2BaselineChangeOrder.baseline_id,
                        BOQV2BaselineChangeOrder.revision_id,
                    )
                    .where(BOQV2BaselineChangeOrder.baseline_id.in_(baseline_ids))
                    .order_by(
                        BOQV2BaselineChangeOrder.baseline_id,
                        BOQV2BaselineChangeOrder.position,
                    )
                )
            ).all()
            for baseline_id, revision_id in co_rows:
                change_orders_by_baseline.setdefault(baseline_id, []).append(
                    revision_id
                )
            for revision_ids in change_orders_by_baseline.values():
                revision_ids.sort(key=str)
        for component_ids in missing_components_by_plan.values():
            component_ids.sort(key=str)

    contexts: dict[UUID, ProjectBudgetReadContext] = {}
    for project_id, facts in facts_by_project.items():
        source = source_by_project.get(project_id)
        if source is None or source.source_kind == "LEGACY":
            contexts[project_id] = _context(
                _legacy_snapshot(facts, as_of=read_at), facts
            )
            continue
        baseline = baseline_by_project.get(project_id)
        if baseline is None:
            if (
                historical_at is not None
                and source.updated_at is not None
                and historical_at < _as_utc(source.updated_at)
            ):
                contexts[project_id] = _context(
                    _legacy_snapshot(facts, as_of=read_at), facts
                )
                continue
            snapshot = ProjectBudgetSnapshot(
                source_kind="V2",
                status="NO_ACTIVE_BASELINE",
                project_id=project_id,
                accepted_change_order_ids=[],
                calculation_version=CALCULATION_VERSION,
                net_sell_ex_vat=None,
                cost_completeness=CostCompleteness(
                    state="NOT_APPLICABLE",
                    required_count=0,
                    priced_count=0,
                    missing_component_ids=[],
                ),
                forecast_basis="NONE",
                as_of=read_at,
            )
            contexts[project_id] = _context(snapshot, facts)
            continue
        plan = cost_plan_by_id.get(baseline.cost_plan_id)
        complete = bool(
            plan
            and plan.completeness_state == "COMPLETE"
            and plan.forecast_cost is not None
        )
        snapshot = ProjectBudgetSnapshot(
            source_kind="V2",
            status="READY" if complete else "UNKNOWN_COST",
            project_id=project_id,
            baseline_id=baseline.id,
            baseline_version=baseline.version,
            main_revision_id=baseline.main_revision_id,
            accepted_change_order_ids=change_orders_by_baseline.get(baseline.id, []),
            cost_plan_version=plan.version if plan else None,
            calculation_version=baseline.calculation_version,
            activated_at=baseline.activated_at,
            net_sell_ex_vat=_money_string(baseline.net_sell_ex_vat),
            original_estimated_cost=_money_string(
                plan.original_estimated_cost
                if plan
                else baseline.original_estimated_cost
            ),
            agreed_cost=_money_string(
                plan.agreed_cost if plan else baseline.agreed_cost
            ),
            forecast_cost=_money_string(plan.forecast_cost) if complete else None,
            forecast_margin=(
                _money_string(
                    _money(baseline.net_sell_ex_vat) - _money(plan.forecast_cost)
                )
                if complete and plan
                else None
            ),
            cost_completeness=CostCompleteness(
                state="COMPLETE" if complete else "INCOMPLETE",
                required_count=plan.required_count if plan else 0,
                priced_count=plan.priced_count if plan else 0,
                missing_component_ids=(
                    missing_components_by_plan.get(plan.id, []) if plan else []
                ),
            ),
            forecast_basis=(
                "AGREED"
                if complete and plan and plan.agreed_cost is not None
                else "ESTIMATED"
                if complete
                else "PARTLY_AGREED"
                if plan and plan.agreed_cost is not None
                else "NONE"
            ),
            as_of=read_at,
        )
        contexts[project_id] = _context(snapshot, facts)
    return contexts


async def load_project_budget_context(
    db: AsyncSession,
    project_id: UUID,
    *,
    as_of: datetime | None = None,
) -> ProjectBudgetReadContext | None:
    return (await load_project_budget_contexts(db, [project_id], as_of=as_of)).get(
        project_id
    )


async def lock_project_budget_state(
    db: AsyncSession,
    project_ids: Sequence[UUID],
) -> None:
    """Acquire the contract lock order before Funds mutates related balances."""

    unique_ids = sorted(set(project_ids), key=str)
    await acquire_project_budget_locks(db, unique_ids)
    await db.execute(
        select(BOQV2ProjectBudgetSource)
        .where(BOQV2ProjectBudgetSource.project_id.in_(unique_ids))
        .order_by(BOQV2ProjectBudgetSource.project_id)
        .with_for_update()
    )
    baseline_rows = list(
        (
            await db.execute(
                select(BOQV2ProjectBaseline)
                .where(
                    BOQV2ProjectBaseline.project_id.in_(unique_ids),
                    BOQV2ProjectBaseline.is_active.is_(True),
                )
                .order_by(BOQV2ProjectBaseline.project_id)
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    cost_plan_ids = list(
        dict.fromkeys(row.cost_plan_id for row in baseline_rows if row.cost_plan_id)
    )
    for cost_plan_id in cost_plan_ids:
        await db.execute(
            select(BOQV2CostPlan)
            .where(BOQV2CostPlan.id == cost_plan_id)
            .with_for_update()
        )


def budget_source_fingerprint(snapshot: ProjectBudgetSnapshot) -> dict[str, object]:
    return {
        "source_kind": snapshot.source_kind,
        "status": snapshot.status,
        "baseline_id": str(snapshot.baseline_id or ""),
        "baseline_version": snapshot.baseline_version,
        "main_revision_id": str(snapshot.main_revision_id or ""),
        "accepted_change_order_ids": [
            str(item) for item in snapshot.accepted_change_order_ids
        ],
        "cost_plan_version": snapshot.cost_plan_version,
        "cost_completeness": snapshot.cost_completeness.model_dump(mode="json"),
        "calculation_version": snapshot.calculation_version,
    }
