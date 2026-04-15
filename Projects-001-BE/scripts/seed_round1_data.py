"""
Deterministic development seed for round 1 features:
  - Dashboard
  - Projects / Project Detail / BOQ
  - Bills admin list / edit / approve

Usage:
  ./venv/bin/python scripts/seed_round1_data.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from app.core.database import AsyncSessionLocal, Base  # <--- ตรวจสอบว่ามี Base อยู่ตรงนี้!
from app.models.boq import BOQItem, Project
from app.models.finance import Installment, Transaction
from app.models.input_request import InputRequest  # noqa: F401
from app.services.finance_service import calculate_net_payable

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("localhost", "127.0.0.1")
if "?ssl=" not in DATABASE_URL:
    DATABASE_URL += "?ssl=disable"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": False} 
)

SEED_NAMESPACE = uuid.UUID("bc8ac73f-c4fd-47c0-a26e-bcb9d1d8a2b8")


@dataclass(frozen=True)
class InstallmentSpec:
    boq_key: str
    expense_category: str
    expense_type: str
    cost_type: str
    installment_no: str
    amount: str
    status: str
    due_date: str
    is_overdue: bool = False
    approved_at: str | None = None


def seeded_uuid(*parts: str) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, "::".join(parts))


def decimal_of(value: Any) -> Decimal:
    return Decimal(str(value))


PROJECT_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "key": "bangna-warehouse-fitout",
        "name": "Bangna Warehouse Fit-Out",
        "project_type": "WAREHOUSE",
        "overhead_percent": "8.50",
        "profit_percent": "14.75",
        "vat_percent": "7.00",
        "contingency_budget": "3850000.00",
        "status": "ACTIVE",
        "boq": [
            {
                "key": "structure",
                "item_no": "1",
                "description": "Structure Works",
                "sheet_name": "STR",
                "children": [
                    {
                        "key": "foundation",
                        "item_no": "1.1",
                        "description": "Foundation",
                        "children": [
                            {
                                "key": "pile_work",
                                "item_no": "1.1.1",
                                "description": "Piling Work",
                                "qty": "1",
                                "unit": "lot",
                                "material": "850000.00",
                                "labor": "270000.00",
                            },
                            {
                                "key": "footing_work",
                                "item_no": "1.1.2",
                                "description": "Footing and Tie Beam",
                                "qty": "1",
                                "unit": "lot",
                                "material": "480000.00",
                                "labor": "160000.00",
                            },
                        ],
                    },
                    {
                        "key": "superstructure",
                        "item_no": "1.2",
                        "description": "Superstructure",
                        "children": [
                            {
                                "key": "steel_frame",
                                "item_no": "1.2.1",
                                "description": "Steel Frame Installation",
                                "qty": "1",
                                "unit": "lot",
                                "material": "620000.00",
                                "labor": "180000.00",
                            },
                        ],
                    },
                ],
            },
            {
                "key": "architectural",
                "item_no": "2",
                "description": "Architectural Works",
                "sheet_name": "ARC",
                "children": [
                    {
                        "key": "finishes",
                        "item_no": "2.1",
                        "description": "Finishes",
                        "children": [
                            {
                                "key": "roof_cladding",
                                "item_no": "2.1.1",
                                "description": "Roof and Cladding",
                                "qty": "1",
                                "unit": "lot",
                                "material": "620000.00",
                                "labor": "170000.00",
                            },
                            {
                                "key": "painting",
                                "item_no": "2.1.2",
                                "description": "Painting and Marking",
                                "qty": "1",
                                "unit": "lot",
                                "material": "80000.00",
                                "labor": "70000.00",
                            },
                        ],
                    },
                ],
            },
        ],
        "installments": [
            InstallmentSpec(
                boq_key="pile_work",
                expense_category="Structure",
                expense_type="Installment",
                cost_type="BOTH",
                installment_no="BW-001",
                amount="420000.00",
                status="APPROVED",
                due_date="2026-01-15",
                approved_at="2026-01-18T10:30:00+00:00",
            ),
            InstallmentSpec(
                boq_key="footing_work",
                expense_category="Structure",
                expense_type="Installment",
                cost_type="BOTH",
                installment_no="BW-002",
                amount="300000.00",
                status="APPROVED",
                due_date="2026-02-12",
                approved_at="2026-02-14T08:45:00+00:00",
            ),
            InstallmentSpec(
                boq_key="roof_cladding",
                expense_category="Architectural",
                expense_type="Installment",
                cost_type="BOTH",
                installment_no="BW-003",
                amount="260000.00",
                status="PENDING",
                due_date="2026-03-25",
            ),
        ],
    },
    {
        "key": "chiangmai-hotel-renovation",
        "name": "Chiang Mai Hotel Renovation",
        "project_type": "HOTEL",
        "overhead_percent": "9.00",
        "profit_percent": "11.50",
        "vat_percent": "7.00",
        "contingency_budget": "5200000.00",
        "status": "ACTIVE",
        "boq": [
            {
                "key": "demolition",
                "item_no": "1",
                "description": "Demolition and Preparation",
                "sheet_name": "PREP",
                "children": [
                    {
                        "key": "stripout",
                        "item_no": "1.1",
                        "description": "Strip Out",
                        "children": [
                            {
                                "key": "room_stripout",
                                "item_no": "1.1.1",
                                "description": "Guest Room Strip Out",
                                "qty": "1",
                                "unit": "lot",
                                "material": "120000.00",
                                "labor": "280000.00",
                            },
                        ],
                    },
                ],
            },
            {
                "key": "renovation",
                "item_no": "2",
                "description": "Renovation Works",
                "sheet_name": "REN",
                "children": [
                    {
                        "key": "guestroom_fitout",
                        "item_no": "2.1",
                        "description": "Guest Room Fit-Out",
                        "children": [
                            {
                                "key": "ceiling_finish",
                                "item_no": "2.1.1",
                                "description": "Ceiling and Wall Finish",
                                "qty": "1",
                                "unit": "lot",
                                "material": "980000.00",
                                "labor": "360000.00",
                            },
                            {
                                "key": "bathroom_upgrade",
                                "item_no": "2.1.2",
                                "description": "Bathroom Upgrade",
                                "qty": "1",
                                "unit": "lot",
                                "material": "730000.00",
                                "labor": "270000.00",
                            },
                        ],
                    },
                    {
                        "key": "mep_upgrade",
                        "item_no": "2.2",
                        "description": "MEP Upgrade",
                        "children": [
                            {
                                "key": "hvac_upgrade",
                                "item_no": "2.2.1",
                                "description": "HVAC Upgrade",
                                "qty": "1",
                                "unit": "lot",
                                "material": "1050000.00",
                                "labor": "410000.00",
                            },
                        ],
                    },
                ],
            },
        ],
        "installments": [
            InstallmentSpec(
                boq_key="room_stripout",
                expense_category="Preparation",
                expense_type="Labor",
                cost_type="LABOR",
                installment_no="CM-001",
                amount="180000.00",
                status="APPROVED",
                due_date="2026-01-28",
                approved_at="2026-02-02T07:15:00+00:00",
            ),
            InstallmentSpec(
                boq_key="ceiling_finish",
                expense_category="Finishing",
                expense_type="Installment",
                cost_type="BOTH",
                installment_no="CM-002",
                amount="520000.00",
                status="PENDING",
                due_date="2026-03-10",
                is_overdue=True,
            ),
            InstallmentSpec(
                boq_key="bathroom_upgrade",
                expense_category="Finishing",
                expense_type="Material",
                cost_type="MATERIAL",
                installment_no="CM-003",
                amount="410000.00",
                status="LOCKED",
                due_date="2026-04-05",
            ),
            InstallmentSpec(
                boq_key="hvac_upgrade",
                expense_category="MEP",
                expense_type="Installment",
                cost_type="BOTH",
                installment_no="CM-004",
                amount="640000.00",
                status="PENDING",
                due_date="2026-03-18",
                is_overdue=True,
            ),
        ],
    },
    {
        "key": "rayong-factory-mep-upgrade",
        "name": "Rayong Factory MEP Upgrade",
        "project_type": "INDUSTRIAL",
        "overhead_percent": "7.25",
        "profit_percent": "12.20",
        "vat_percent": "7.00",
        "contingency_budget": "4400000.00",
        "status": "ACTIVE",
        "boq": [
            {
                "key": "electrical",
                "item_no": "1",
                "description": "Electrical Works",
                "sheet_name": "ELEC",
                "children": [
                    {
                        "key": "power_distribution",
                        "item_no": "1.1",
                        "description": "Power Distribution",
                        "children": [
                            {
                                "key": "main_panel",
                                "item_no": "1.1.1",
                                "description": "Main Panel Replacement",
                                "qty": "1",
                                "unit": "lot",
                                "material": "820000.00",
                                "labor": "210000.00",
                            },
                            {
                                "key": "cable_tray",
                                "item_no": "1.1.2",
                                "description": "Cable Tray and Wiring",
                                "qty": "1",
                                "unit": "lot",
                                "material": "540000.00",
                                "labor": "180000.00",
                            },
                        ],
                    },
                ],
            },
            {
                "key": "mechanical",
                "item_no": "2",
                "description": "Mechanical Works",
                "sheet_name": "MECH",
                "children": [
                    {
                        "key": "pump_system",
                        "item_no": "2.1",
                        "description": "Pump System",
                        "children": [
                            {
                                "key": "booster_pump",
                                "item_no": "2.1.1",
                                "description": "Booster Pump Replacement",
                                "qty": "1",
                                "unit": "lot",
                                "material": "790000.00",
                                "labor": "200000.00",
                            },
                            {
                                "key": "pipe_rerouting",
                                "item_no": "2.1.2",
                                "description": "Pipe Rerouting",
                                "qty": "1",
                                "unit": "lot",
                                "material": "470000.00",
                                "labor": "190000.00",
                            },
                        ],
                    },
                ],
            },
        ],
        "installments": [
            InstallmentSpec(
                boq_key="main_panel",
                expense_category="Electrical",
                expense_type="Material",
                cost_type="MATERIAL",
                installment_no="RY-001",
                amount="330000.00",
                status="APPROVED",
                due_date="2026-01-20",
                approved_at="2026-01-24T09:00:00+00:00",
            ),
            InstallmentSpec(
                boq_key="cable_tray",
                expense_category="Electrical",
                expense_type="Installment",
                cost_type="BOTH",
                installment_no="RY-002",
                amount="280000.00",
                status="APPROVED",
                due_date="2026-02-25",
                approved_at="2026-02-27T13:15:00+00:00",
            ),
            InstallmentSpec(
                boq_key="booster_pump",
                expense_category="Mechanical",
                expense_type="Installment",
                cost_type="BOTH",
                installment_no="RY-003",
                amount="360000.00",
                status="PENDING",
                due_date="2026-03-30",
            ),
            InstallmentSpec(
                boq_key="pipe_rerouting",
                expense_category="Mechanical",
                expense_type="Labor",
                cost_type="LABOR",
                installment_no="RY-004",
                amount="190000.00",
                status="LOCKED",
                due_date="2026-04-12",
            ),
        ],
    },
    {
        "key": "phuket-sales-gallery",
        "name": "Phuket Sales Gallery",
        "project_type": "COMMERCIAL",
        "overhead_percent": "8.00",
        "profit_percent": "16.40",
        "vat_percent": "7.00",
        "contingency_budget": "2700000.00",
        "status": "COMPLETED",
        "boq": [
            {
                "key": "interior",
                "item_no": "1",
                "description": "Interior Works",
                "sheet_name": "INT",
                "children": [
                    {
                        "key": "showroom_fitout",
                        "item_no": "1.1",
                        "description": "Showroom Fit-Out",
                        "children": [
                            {
                                "key": "custom_joinery",
                                "item_no": "1.1.1",
                                "description": "Custom Joinery",
                                "qty": "1",
                                "unit": "lot",
                                "material": "620000.00",
                                "labor": "190000.00",
                            },
                            {
                                "key": "lighting_scene",
                                "item_no": "1.1.2",
                                "description": "Lighting Scene Installation",
                                "qty": "1",
                                "unit": "lot",
                                "material": "310000.00",
                                "labor": "95000.00",
                            },
                        ],
                    },
                ],
            },
            {
                "key": "landscape",
                "item_no": "2",
                "description": "Landscape and Exterior",
                "sheet_name": "EXT",
                "children": [
                    {
                        "key": "entrance_feature",
                        "item_no": "2.1",
                        "description": "Entrance Feature",
                        "children": [
                            {
                                "key": "hardscape",
                                "item_no": "2.1.1",
                                "description": "Hardscape and Signage",
                                "qty": "1",
                                "unit": "lot",
                                "material": "980000.00",
                                "labor": "205000.00",
                            },
                        ],
                    },
                ],
            },
        ],
        "installments": [
            InstallmentSpec(
                boq_key="custom_joinery",
                expense_category="Interior",
                expense_type="Installment",
                cost_type="BOTH",
                installment_no="PK-001",
                amount="290000.00",
                status="APPROVED",
                due_date="2025-12-22",
                approved_at="2025-12-27T10:00:00+00:00",
            ),
            InstallmentSpec(
                boq_key="lighting_scene",
                expense_category="Interior",
                expense_type="Material",
                cost_type="MATERIAL",
                installment_no="PK-002",
                amount="170000.00",
                status="APPROVED",
                due_date="2026-01-18",
                approved_at="2026-01-22T11:20:00+00:00",
            ),
            InstallmentSpec(
                boq_key="hardscape",
                expense_category="Exterior",
                expense_type="Installment",
                cost_type="BOTH",
                installment_no="PK-003",
                amount="360000.00",
                status="APPROVED",
                due_date="2026-02-18",
                approved_at="2026-02-20T15:40:00+00:00",
            ),
        ],
    },
]


def parse_approved_at(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def parse_due_date(value: str) -> date:
    return date.fromisoformat(value)


def month_label(value: date | datetime) -> str:
    return value.strftime("%b")


async def reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def create_boq_tree(
    *,
    session: AsyncSession,
    project_id: uuid.UUID,
    project_key: str,
    nodes: list[dict[str, Any]],
    parent_id: uuid.UUID | None = None,
    lookup: dict[str, BOQItem],
) -> Decimal:
    total = Decimal("0")

    for node in nodes:
        node_id = seeded_uuid(project_key, "boq", node["key"])
        children = node.get("children", [])

        if children:
            child_total = Decimal("0")
            material_total = Decimal("0")
            labor_total = Decimal("0")
            boq_item = BOQItem(
                id=node_id,
                project_id=project_id,
                boq_type="CUSTOMER",
                sheet_name=node.get("sheet_name"),
                wbs_level=int(str(node["item_no"]).count(".") + 1),
                parent_id=parent_id,
                item_no=node["item_no"],
                description=node["description"],
                qty=Decimal("0"),
                unit=None,
                material_unit_price=Decimal("0"),
                labor_unit_price=Decimal("0"),
                total_material=material_total,
                total_labor=labor_total,
                grand_total=child_total,
                valid_from=datetime.now(timezone.utc),
                valid_to=None,
            )
            session.add(boq_item)
            lookup[node["key"]] = boq_item

            child_total = await create_boq_tree(
                session=session,
                project_id=project_id,
                project_key=project_key,
                nodes=children,
                parent_id=node_id,
                lookup=lookup,
            )
            material_total = sum(
                decimal_of(lookup[child["key"]].total_material or 0) for child in children
            )
            labor_total = sum(
                decimal_of(lookup[child["key"]].total_labor or 0) for child in children
            )
            boq_item.total_material = material_total
            boq_item.total_labor = labor_total
            boq_item.grand_total = child_total
            total += child_total
        else:
            qty = decimal_of(node["qty"])
            material_total = decimal_of(node["material"])
            labor_total = decimal_of(node["labor"])
            grand_total = material_total + labor_total
            boq_item = BOQItem(
                id=node_id,
                project_id=project_id,
                boq_type="CUSTOMER",
                sheet_name=node.get("sheet_name"),
                wbs_level=int(str(node["item_no"]).count(".") + 1),
                parent_id=parent_id,
                item_no=node["item_no"],
                description=node["description"],
                qty=qty,
                unit=node["unit"],
                material_unit_price=(material_total / qty) if qty else Decimal("0"),
                labor_unit_price=(labor_total / qty) if qty else Decimal("0"),
                total_material=material_total,
                total_labor=labor_total,
                grand_total=grand_total,
                valid_from=datetime.now(timezone.utc),
                valid_to=None,
            )
            session.add(boq_item)
            lookup[node["key"]] = boq_item
            total += grand_total

    return total


async def seed_data() -> dict[str, int]:
    counts = defaultdict(int)

    async with AsyncSessionLocal() as session:
        for blueprint in PROJECT_BLUEPRINTS:
            project_id = seeded_uuid(blueprint["key"], "project")
            project = Project(
                id=project_id,
                name=blueprint["name"],
                project_type=blueprint["project_type"],
                overhead_percent=decimal_of(blueprint["overhead_percent"]),
                profit_percent=decimal_of(blueprint["profit_percent"]),
                vat_percent=decimal_of(blueprint["vat_percent"]),
                contingency_budget=decimal_of(blueprint["contingency_budget"]),
                status=blueprint["status"],
            )
            session.add(project)
            counts["projects"] += 1

            boq_lookup: dict[str, BOQItem] = {}
            await create_boq_tree(
                session=session,
                project_id=project_id,
                project_key=blueprint["key"],
                nodes=blueprint["boq"],
                lookup=boq_lookup,
            )
            counts["boq_items"] += len(boq_lookup)

            for spec in blueprint["installments"]:
                installment_id = seeded_uuid(blueprint["key"], "installment", spec.installment_no)
                installment = Installment(
                    id=installment_id,
                    boq_item_id=boq_lookup[spec.boq_key].id,
                    expense_category=spec.expense_category,
                    expense_type=spec.expense_type,
                    cost_type=spec.cost_type,
                    installment_no=spec.installment_no,
                    amount=decimal_of(spec.amount),
                    status=spec.status,
                    due_date=parse_due_date(spec.due_date),
                    is_overdue=spec.is_overdue,
                )
                session.add(installment)
                counts["installments"] += 1

                approved_at = parse_approved_at(spec.approved_at)
                if spec.status == "APPROVED" and approved_at is not None:
                    breakdown = await calculate_net_payable(decimal_of(spec.amount))
                    transaction = Transaction(
                        id=seeded_uuid(blueprint["key"], "transaction", spec.installment_no),
                        installment_id=installment_id,
                        base_amount=decimal_of(breakdown["base_amount"]),
                        vat_amount=decimal_of(breakdown["vat_amount"]),
                        wht_amount=decimal_of(breakdown["wht_amount"]),
                        retention_amount=decimal_of(breakdown["retention_amount"]),
                        advance_deduction=decimal_of(breakdown["advance_deduction"]),
                        net_payable=decimal_of(breakdown["net_payable"]),
                        approved_at=approved_at,
                    )
                    session.add(transaction)
                    counts["transactions"] += 1

        await session.commit()

    return dict(counts)


async def print_summary() -> None:
    async with AsyncSessionLocal() as session:
        projects = (await session.execute(text("select count(*) from projects"))).scalar() or 0
        boq_items = (await session.execute(text("select count(*) from boq_items"))).scalar() or 0
        installments = (
            await session.execute(text("select count(*) from installments"))
        ).scalar() or 0
        transactions = (
            await session.execute(text("select count(*) from transactions"))
        ).scalar() or 0
        pending = (
            await session.execute(
                text("select count(*) from installments where status = 'PENDING'")
            )
        ).scalar() or 0
        overdue = (
            await session.execute(
                text(
                    "select coalesce(sum(amount), 0) from installments "
                    "where is_overdue = true and status <> 'APPROVED'"
                )
            )
        ).scalar() or 0

    print("Seed completed successfully.")
    print(f"DATABASE_URL={os.getenv('DATABASE_URL')}")
    print(f"projects={projects}")
    print(f"boq_items={boq_items}")
    print(f"installments={installments}")
    print(f"transactions={transactions}")
    print(f"pending_installments={pending}")
    print(f"overdue_amount={overdue}")


async def main() -> None:
    await reset_schema()
    await seed_data()
    await print_summary()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
