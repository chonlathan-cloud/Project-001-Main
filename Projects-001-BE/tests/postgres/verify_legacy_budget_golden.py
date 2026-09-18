"""Verify current legacy budget projections against the Phase 0 golden fixture."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse
from uuid import NAMESPACE_URL, UUID, uuid5


BACKEND_DIR = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    BACKEND_DIR / "tests/fixtures/boq_v2_phase0/legacy_budget_consumers.json"
)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _safe_url() -> str:
    value = os.environ.get("PHASE0_DATABASE_URL", "").strip()
    if not value:
        raise SystemExit("PHASE0_DATABASE_URL is required; backend .env is not allowed")
    parsed = urlparse(value)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing non-loopback Phase 0 database")
    if not parsed.path.lstrip("/").endswith("_test"):
        raise SystemExit("Refusing database whose name does not end with _test")
    return value


def _money(value: object) -> str:
    return str(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


async def main() -> None:
    database_url = _safe_url()
    os.environ["DATABASE_URL"] = database_url

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.api.v1.dashboard import get_dashboard_summary
    from app.api.v1.projects import get_project_boq, list_projects
    from app.models.boq import BOQItem, Project
    from app.services.chat_analytics_service import _build_project_rollups, _load_snapshot
    from app.services.mcp_read_service import _current_customer_budget
    from app.services.project_budget_service import (
        active_budget_amount,
        load_project_budget_context,
    )

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    scenarios = fixture["scenarios"]
    project_ids = {
        "dual_boq": UUID("71000000-0000-4000-8000-000000000001"),
        "subcontractor_only": UUID("71000000-0000-4000-8000-000000000002"),
        "no_boq": UUID("71000000-0000-4000-8000-000000000003"),
    }

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    actual_by_scenario: dict[str, dict[str, object]] = {}

    async with session_factory() as session:
        transaction = await session.begin()
        try:
            for scenario in scenarios:
                scenario_id = scenario["id"]
                values = scenario["inputs"]
                project_id = project_ids[scenario_id]
                session.add(
                    Project(
                        id=project_id,
                        name=f"Phase0 {scenario_id}",
                        project_type="CONSTRUCTION",
                        status="ACTIVE",
                        contingency_budget=Decimal(values["contingency_budget"]),
                    )
                )
                for boq_type, key, suffix in (
                    ("CUSTOMER", "customer_root_total", "1"),
                    ("SUBCONTRACTOR", "subcontractor_root_total", "2"),
                ):
                    amount = Decimal(values[key])
                    if amount == 0:
                        continue
                    session.add(
                        BOQItem(
                            id=uuid5(
                                NAMESPACE_URL,
                                f"phase0:{scenario_id}:{boq_type}:{suffix}",
                            ),
                            project_id=project_id,
                            boq_type=boq_type,
                            sheet_name="Phase0",
                            wbs_level=1,
                            parent_id=None,
                            item_no="1",
                            description="Golden root",
                            qty=Decimal("1.00"),
                            unit="LS",
                            material_unit_price=amount,
                            labor_unit_price=Decimal("0.00"),
                            total_material=amount,
                            total_labor=Decimal("0.00"),
                            grand_total=amount,
                            valid_to=None,
                        )
                    )
            await session.flush()

            project_list = await list_projects(session, None)
            project_list_by_id = {
                str(item.project_id): item for item in project_list.data
            }
            dashboard = await get_dashboard_summary(session, None)
            dashboard_by_id = {
                item.project_id: item for item in dashboard.data.project_health
            }

            for scenario in scenarios:
                scenario_id = scenario["id"]
                values = scenario["inputs"]
                project_id = project_ids[scenario_id]
                detail = await get_project_boq(project_id, session, None)
                summary = detail.data.compare_summary
                budget_context = await load_project_budget_context(session, project_id)
                fund_margin = active_budget_amount(
                    budget_context, consumer="FUNDS"
                ) if budget_context is not None else "0.00"
                mcp_budget = await _current_customer_budget(session, project_id)
                chat_snapshot = await _load_snapshot(session, project_id)
                chat_rollup = _build_project_rollups(chat_snapshot, None)[project_id]

                customer = Decimal(values["customer_root_total"])
                subcontractor = Decimal(values["subcontractor_root_total"])
                contingency = Decimal(values["contingency_budget"])
                if customer:
                    frontend_total = customer
                    frontend_source = "Customer BOQ"
                elif subcontractor:
                    frontend_total = subcontractor
                    frontend_source = "Subcontractor BOQ"
                else:
                    frontend_total = contingency
                    frontend_source = "Project budget"

                actual_by_scenario[scenario_id] = {
                    "project_list_total_budget": _money(
                        project_list_by_id[str(project_id)].total_budget
                    ),
                    "project_detail_customer_total_budget": _money(
                        summary.customer_total_budget
                    ),
                    "project_detail_subcontractor_total_budget": _money(
                        summary.subcontractor_total_budget
                    ),
                    "project_detail_total_variance": _money(summary.total_variance),
                    "project_detail_margin_percent": (
                        _money(summary.margin_percent)
                        if summary.margin_percent is not None
                        else None
                    ),
                    "fund_forecast_base": _money(fund_margin),
                    "dashboard_total_budget": _money(
                        dashboard_by_id[str(project_id)].total_budget
                    ),
                    "chat_display_budget": _money(chat_rollup["budget_baseline"]),
                    "mcp_current_boq_budget": {
                        "amount": _money(mcp_budget),
                        "currency": "THB",
                    },
                    "frontend_card_total_budget": _money(frontend_total),
                    "frontend_card_budget_source": frontend_source,
                }

            failures = []
            for scenario in scenarios:
                scenario_id = scenario["id"]
                expected = scenario["expected"]
                actual = actual_by_scenario[scenario_id]
                if actual != expected:
                    failures.append(
                        {"scenario": scenario_id, "expected": expected, "actual": actual}
                    )
            if failures:
                raise AssertionError(json.dumps(failures, indent=2, sort_keys=True))
        finally:
            await transaction.rollback()
            await engine.dispose()

    print(
        json.dumps(
            {
                "golden_contract_version": fixture["contract_version"],
                "verified_scenarios": sorted(actual_by_scenario),
                "consumer_projections_per_scenario": len(
                    scenarios[0]["expected"]
                ),
                "result": "pass",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
