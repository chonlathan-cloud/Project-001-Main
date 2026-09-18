"""Server-authoritative fund calculation, posting, reversal, and opening balance."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.config import get_settings
from app.models.boq import Project
from app.models.funds import FundAllocation, FundAuditEvent, FundBucket, FundLedgerEntry
from app.schemas.fund_schema import (
    FundAllocationListResponse,
    FundAllocationParty,
    FundAllocationResponse,
    FundBucketOption,
    FundSummaryResponse,
)
from app.services.project_budget_service import (
    active_budget_amount,
    budget_source_fingerprint,
    load_project_budget_context,
    lock_project_budget_state,
)

MONEY_QUANTUM = Decimal("0.01")
ZERO = Decimal("0.00")
BANGKOK = ZoneInfo("Asia/Bangkok")
OPERATIONS_SYSTEM_KEY = "OPERATIONS"


class FundDomainError(Exception):
    """A stable business error suitable for a structured API response."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.context = context or {}


@dataclass(frozen=True)
class AvailableValues:
    raw_forecast_available: Decimal
    available_margin_to_allocate: Decimal
    forecast_deficit: Decimal


def _assert_outward_budget_ready(budget_context) -> None:
    if (
        budget_context is not None
        and budget_context.snapshot.source_kind == "V2"
        and budget_context.snapshot.status != "READY"
    ):
        raise FundDomainError(
            "BOQ_BUDGET_NOT_READY",
            "The source Project budget is not ready for a new outward allocation.",
            status_code=409,
            context={"budget_status": budget_context.snapshot.status},
        )


def money(value: object) -> Decimal:
    """Normalize a persisted/API money value to fixed two-decimal precision."""

    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_available_values(
    *,
    forecast_base: object = ZERO,
    forecast_allocated_in: object = ZERO,
    forecast_allocated_out: object = ZERO,
    forecast_reserve: object = ZERO,
) -> AvailableValues:
    """Apply the forecast-margin formula without actual cashflow inputs."""

    raw = money(
        money(forecast_base)
        + money(forecast_allocated_in)
        - money(forecast_allocated_out)
        - money(forecast_reserve)
    )
    return AvailableValues(
        raw_forecast_available=raw,
        available_margin_to_allocate=max(ZERO, raw),
        forecast_deficit=max(ZERO, -raw),
    )


def is_first_day_of_month(value: date) -> bool:
    return value.day == 1


def build_balance_version(payload: dict[str, object]) -> str:
    """Build a stable opaque version that changes with relevant source activity."""

    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:32]


def _ledger_totals(
    entries: list[FundLedgerEntry],
    *,
    start_date: date | None,
    cutoff: date | None = None,
) -> dict[str, Decimal]:
    totals = {
        "opening_forecast_balance": ZERO,
        "forecast_allocated_in": ZERO,
        "forecast_allocated_out": ZERO,
    }
    for entry in entries:
        effective_date = entry.effective_date
        if start_date and effective_date < start_date:
            continue
        if cutoff and effective_date >= cutoff:
            continue
        amount = money(entry.amount)
        if entry.entry_type == "OPENING_BALANCE":
            if entry.direction == "CREDIT":
                totals["opening_forecast_balance"] = money(
                    totals["opening_forecast_balance"] + amount
                )
            continue
        if entry.entry_type not in {"ALLOCATION", "REVERSAL"}:
            continue
        if entry.direction == "CREDIT":
            totals["forecast_allocated_in"] = money(
                totals["forecast_allocated_in"] + amount
            )
        elif entry.direction == "DEBIT":
            totals["forecast_allocated_out"] = money(
                totals["forecast_allocated_out"] + amount
            )
    return totals


async def _bucket_context(
    db: AsyncSession,
    project_id: UUID,
    *,
    lock: bool = False,
) -> tuple[FundBucket, Project]:
    statement = (
        select(FundBucket, Project)
        .join(Project, Project.id == FundBucket.project_id)
        .options(noload("*"))
        .where(Project.id == project_id)
    )
    if lock:
        statement = statement.with_for_update(of=FundBucket)
    row = (await db.execute(statement)).first()
    if row is None:
        project_exists = (
            await db.execute(select(Project.id).where(Project.id == project_id))
        ).scalar_one_or_none()
        code = "FUND_BUCKET_MISSING" if project_exists else "PROJECT_NOT_FOUND"
        raise FundDomainError(
            code,
            "The Project fund bucket is not configured." if project_exists else "Project not found.",
            status_code=404,
            context={"project_id": str(project_id)},
        )
    return row[0], row[1]


def _source_fingerprint(
    bucket: FundBucket,
    entries: list[FundLedgerEntry],
    values: AvailableValues,
    *,
    forecast_base_type: str,
    forecast_base: Decimal | None,
    budget_source: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "bucket": [
            str(bucket.id),
            str(bucket.status),
            str(bucket.balance_start_date or ""),
            str(money(bucket.protected_reserve)),
        ],
        "forecast_base": [
            forecast_base_type,
            None if forecast_base is None else str(money(forecast_base)),
        ],
        "budget_source": budget_source or {"source_kind": "LEGACY"},
        "values": [
            str(values.raw_forecast_available),
            str(values.available_margin_to_allocate),
            str(values.forecast_deficit),
        ],
        "ledger": sorted(
            [
                str(entry.id),
                str(entry.direction),
                str(entry.entry_type),
                str(money(entry.amount)),
                str(entry.effective_date),
            ]
            for entry in entries
        ),
    }


async def calculate_fund_summary(
    db: AsyncSession,
    project_id: UUID,
    *,
    locked_context: tuple[FundBucket, Project] | None = None,
) -> FundSummaryResponse:
    bucket, project = locked_context or await _bucket_context(db, project_id)
    entries = list(
        (
            await db.execute(
                select(FundLedgerEntry)
                .options(noload("*"))
                .where(FundLedgerEntry.bucket_id == bucket.id)
            )
        ).scalars().all()
    )

    now = datetime.now(UTC)
    today = now.astimezone(BANGKOK).date()
    ledger_totals = _ledger_totals(entries, start_date=bucket.balance_start_date)
    is_operations = project.system_key == OPERATIONS_SYSTEM_KEY
    forecast_base_type = (
        "OPENING_FORECAST_BALANCE" if is_operations else "PROJECTED_BOQ_MARGIN"
    )
    budget_context = (
        None if is_operations else await load_project_budget_context(db, project.id)
    )
    active_margin = (
        None
        if is_operations or budget_context is None
        else active_budget_amount(budget_context, consumer="FUNDS")
    )
    forecast_available_known = bool(
        is_operations or budget_context is None or active_margin is not None
    )
    projected_boq_margin = (
        money(active_margin)
        if not is_operations and active_margin is not None
        else ZERO
        if not is_operations and budget_context is None
        else None
    )
    opening_forecast_balance = ledger_totals["opening_forecast_balance"]
    forecast_base = opening_forecast_balance if is_operations else projected_boq_margin
    calculation_base = forecast_base if forecast_base is not None else ZERO
    values = calculate_available_values(
        forecast_base=calculation_base,
        forecast_allocated_in=ledger_totals["forecast_allocated_in"],
        forecast_allocated_out=ledger_totals["forecast_allocated_out"],
        forecast_reserve=bucket.protected_reserve,
    )

    monthly_forecast_opening: Decimal | None = None
    monthly_forecast_closing: Decimal | None = None
    if is_operations and bucket.balance_start_date is not None:
        month_start = today.replace(day=1)
        historical_ledger = _ledger_totals(
            entries,
            start_date=bucket.balance_start_date,
            cutoff=month_start,
        )
        if bucket.balance_start_date == month_start:
            activation_opening = _ledger_totals(
                entries,
                start_date=bucket.balance_start_date,
            )["opening_forecast_balance"]
            historical_ledger["opening_forecast_balance"] = activation_opening
        monthly_forecast_opening = calculate_available_values(
            forecast_base=historical_ledger["opening_forecast_balance"],
            forecast_allocated_in=historical_ledger["forecast_allocated_in"],
            forecast_allocated_out=historical_ledger["forecast_allocated_out"],
            forecast_reserve=bucket.protected_reserve,
        ).raw_forecast_available
        monthly_forecast_closing = values.raw_forecast_available

    version = build_balance_version(
        _source_fingerprint(
            bucket,
            entries,
            values,
            forecast_base_type=forecast_base_type,
            forecast_base=forecast_base,
            budget_source=(
                budget_source_fingerprint(budget_context.snapshot)
                if budget_context is not None
                else {"source_kind": "OPERATIONS"}
            ),
        )
    )
    opening_forecast_balance_set = bucket.balance_start_date is not None
    return FundSummaryResponse(
        project_id=project.id,
        bucket_id=bucket.id,
        currency=bucket.currency,
        forecast_base_type=forecast_base_type,
        projected_boq_margin=projected_boq_margin,
        opening_forecast_balance=opening_forecast_balance,
        forecast_allocated_in=ledger_totals["forecast_allocated_in"],
        forecast_allocated_out=ledger_totals["forecast_allocated_out"],
        forecast_reserve=money(bucket.protected_reserve),
        raw_forecast_available=(
            values.raw_forecast_available if forecast_available_known else None
        ),
        available_margin_to_allocate=(
            values.available_margin_to_allocate if forecast_available_known else None
        ),
        forecast_deficit=values.forecast_deficit if forecast_available_known else None,
        monthly_forecast_opening=monthly_forecast_opening,
        monthly_forecast_closing=monthly_forecast_closing,
        balance_start_date=bucket.balance_start_date,
        bucket_status=bucket.status,
        opening_forecast_balance_set=opening_forecast_balance_set,
        mutations_enabled=get_settings().fund_allocation_enabled,
        calculated_at=now,
        version=version,
        budget_snapshot=(budget_context.snapshot if budget_context is not None else None),
        forecast_available_known=forecast_available_known,
        correction_available_margin=values.available_margin_to_allocate,
        allocated_in=ledger_totals["forecast_allocated_in"],
        allocated_out=ledger_totals["forecast_allocated_out"],
        protected_reserve=money(bucket.protected_reserve),
        raw_available=(values.raw_forecast_available if forecast_available_known else None),
        available_to_allocate=(
            values.available_margin_to_allocate if forecast_available_known else None
        ),
        funding_deficit=values.forecast_deficit if forecast_available_known else None,
        opening_balance=opening_forecast_balance if is_operations else None,
        monthly_opening=monthly_forecast_opening,
        monthly_closing=monthly_forecast_closing,
        opening_balance_set=opening_forecast_balance_set,
    )


async def list_bucket_options(db: AsyncSession) -> list[FundBucketOption]:
    rows = (
        await db.execute(
            select(FundBucket, Project)
            .join(Project, Project.id == FundBucket.project_id)
            .options(noload("*"))
            .order_by(
                (Project.system_key == OPERATIONS_SYSTEM_KEY).desc(),
                Project.name.asc(),
            )
        )
    ).all()
    if not any(project.system_key == OPERATIONS_SYSTEM_KEY for _, project in rows):
        raise FundDomainError(
            "OPERATIONS_BUCKET_MISSING",
            "Company Operations is not configured. Run the audited bootstrap migration.",
            status_code=503,
        )
    options: list[FundBucketOption] = []
    for bucket, project in rows:
        summary = await calculate_fund_summary(
            db,
            project.id,
            locked_context=(bucket, project),
        )
        active = (
            str(project.status or "").upper() == "ACTIVE"
            and (
                bucket.status == "ACTIVE"
                or (bucket.bucket_type == "OPERATIONS" and bucket.status == "SETUP")
            )
        )
        options.append(
            FundBucketOption(
                bucket_id=bucket.id,
                project_id=project.id,
                project_name=project.name,
                project_type=project.project_type,
                system_key=project.system_key,
                bucket_type=bucket.bucket_type,
                status=bucket.status,
                currency=bucket.currency,
                available_margin_to_allocate=summary.available_margin_to_allocate,
                available_to_allocate=summary.available_margin_to_allocate,
                version=summary.version,
                is_active=active,
                budget_source_kind=(
                    summary.budget_snapshot.source_kind
                    if summary.budget_snapshot is not None
                    else "OPERATIONS"
                ),
                budget_status=(
                    summary.budget_snapshot.status
                    if summary.budget_snapshot is not None
                    else "READY"
                ),
            )
        )
    return options


async def _advisory_idempotency_lock(db: AsyncSession, key: str) -> None:
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:fund_lock_key))"),
        {"fund_lock_key": f"fund:{key}"},
    )


async def _locked_bucket_contexts(
    db: AsyncSession,
    project_ids: tuple[UUID, UUID],
) -> dict[UUID, tuple[FundBucket, Project]]:
    rows = (
        await db.execute(
            select(FundBucket, Project)
            .join(Project, Project.id == FundBucket.project_id)
            .options(noload("*"))
            .where(Project.id.in_(project_ids))
            .order_by(Project.id.asc())
            .with_for_update(of=FundBucket)
        )
    ).all()
    contexts = {project.id: (bucket, project) for bucket, project in rows}
    for project_id in project_ids:
        if project_id not in contexts:
            raise FundDomainError(
                "FUND_BUCKET_MISSING",
                "A required Project fund bucket is not configured.",
                status_code=404,
                context={"project_id": str(project_id)},
            )
    return contexts


def _validate_active_context(
    context: tuple[FundBucket, Project],
    *,
    target: bool,
) -> None:
    bucket, project = context
    project_is_active = str(project.status or "").upper() == "ACTIVE"
    setup_operations_target = (
        target and bucket.bucket_type == "OPERATIONS" and bucket.status == "SETUP"
    )
    if (
        not project_is_active
        or (bucket.status != "ACTIVE" and not setup_operations_target)
    ):
        code = "TARGET_BUCKET_INACTIVE" if target else "SOURCE_BUCKET_INACTIVE"
        raise FundDomainError(
            code,
            "The destination Bucket must be active." if target else "The source Bucket must be active.",
            status_code=409,
            context={"project_id": str(project.id)},
        )


def _mutation_balance(summary: FundSummaryResponse) -> Decimal:
    """Known public availability, or ledger-only capacity for corrections/incoming."""

    if summary.available_margin_to_allocate is not None:
        return money(summary.available_margin_to_allocate)
    return money(summary.correction_available_margin)


def _reference(prefix: str) -> str:
    today = datetime.now(BANGKOK).strftime("%Y%m%d")
    return f"{prefix}-{today}-{uuid4().hex[:10].upper()}"


async def _party_for_bucket(db: AsyncSession, bucket_id: UUID) -> FundAllocationParty:
    row = (
        await db.execute(
            select(FundBucket, Project)
            .join(Project, Project.id == FundBucket.project_id)
            .options(noload("*"))
            .where(FundBucket.id == bucket_id)
        )
    ).first()
    if row is None:
        raise FundDomainError("FUND_BUCKET_MISSING", "Fund bucket not found.", status_code=404)
    bucket, project = row
    return FundAllocationParty(
        bucket_id=bucket.id,
        project_id=project.id,
        project_name=project.name,
        system_key=project.system_key,
    )


async def serialize_allocation(
    db: AsyncSession,
    allocation: FundAllocation,
) -> FundAllocationResponse:
    return FundAllocationResponse(
        id=allocation.id,
        reference_no=allocation.reference_no,
        source=await _party_for_bucket(db, allocation.source_bucket_id),
        target=await _party_for_bucket(db, allocation.target_bucket_id),
        amount=money(allocation.amount),
        currency=allocation.currency,
        reason=allocation.reason,
        note=allocation.note,
        status=allocation.status,
        reversal_of=allocation.reversal_of,
        created_by=allocation.created_by,
        created_at=allocation.created_at or datetime.now(UTC),
        source_balance_before=money(allocation.source_balance_before),
        source_balance_after=money(allocation.source_balance_after),
        target_balance_before=money(allocation.target_balance_before),
        target_balance_after=money(allocation.target_balance_after),
        source_balance_version=allocation.source_balance_version,
        target_balance_version=allocation.target_balance_version,
    )


async def post_allocation(
    db: AsyncSession,
    *,
    source_project_id: UUID,
    target_project_id: UUID,
    amount: Decimal,
    currency: str,
    reason: str,
    note: str | None,
    expected_source_balance_version: str,
    idempotency_key: str,
    actor: str,
) -> FundAllocationResponse:
    if source_project_id == target_project_id:
        raise FundDomainError(
            "INVALID_SOURCE_TARGET",
            "Source and destination Projects must be different.",
            status_code=400,
        )
    normalized_amount = money(amount)
    allocation: FundAllocation
    async with db.begin():
        await lock_project_budget_state(db, (source_project_id, target_project_id))
        contexts = await _locked_bucket_contexts(
            db,
            (source_project_id, target_project_id),
        )
        await _advisory_idempotency_lock(db, idempotency_key)
        existing = (
            await db.execute(
                select(FundAllocation)
                .options(noload("*"))
                .where(FundAllocation.idempotency_key == idempotency_key)
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing_bucket_rows = (
                await db.execute(
                    select(FundBucket.id, FundBucket.project_id).where(
                        FundBucket.id.in_(
                            (existing.source_bucket_id, existing.target_bucket_id)
                        )
                    )
                )
            ).all()
            existing_project_ids = {
                bucket_id: project_id for bucket_id, project_id in existing_bucket_rows
            }
            if (
                money(existing.amount) != normalized_amount
                or existing_project_ids.get(existing.source_bucket_id) != source_project_id
                or existing_project_ids.get(existing.target_bucket_id) != target_project_id
                or existing.currency != currency
            ):
                raise FundDomainError(
                    "IDEMPOTENCY_KEY_REUSED",
                    "The idempotency key was already used for a different allocation.",
                    status_code=409,
                )
            allocation = existing
        else:
            source_context = contexts[source_project_id]
            target_context = contexts[target_project_id]
            _validate_active_context(source_context, target=False)
            _validate_active_context(target_context, target=True)
            source_budget_context = await load_project_budget_context(
                db, source_project_id
            )
            _assert_outward_budget_ready(source_budget_context)
            source_summary = await calculate_fund_summary(
                db,
                source_project_id,
                locked_context=source_context,
            )
            target_summary = await calculate_fund_summary(
                db,
                target_project_id,
                locked_context=target_context,
            )
            source_available = _mutation_balance(source_summary)
            target_available = _mutation_balance(target_summary)
            if source_summary.version != expected_source_balance_version:
                raise FundDomainError(
                    "STALE_FUND_BALANCE",
                    "The source balance changed. Refresh and review the latest amount.",
                    status_code=409,
                    context={"current_version": source_summary.version},
                )
            if (
                normalized_amount <= ZERO
                or normalized_amount > source_available
            ):
                raise FundDomainError(
                    "INSUFFICIENT_AVAILABLE_MARGIN",
                    "The allocation exceeds the current Available Margin to Allocate.",
                    status_code=409,
                    context={
                        "available_margin_to_allocate": str(
                            source_available
                        ),
                    },
                )

            source_bucket = source_context[0]
            target_bucket = target_context[0]
            allocation = FundAllocation(
                reference_no=_reference("FA"),
                source_bucket_id=source_bucket.id,
                target_bucket_id=target_bucket.id,
                amount=normalized_amount,
                currency=currency,
                reason=reason,
                note=note,
                status="POSTED",
                idempotency_key=idempotency_key,
                created_by=actor,
                source_balance_before=source_available,
                source_balance_after=money(
                    source_available - normalized_amount
                ),
                target_balance_before=target_available,
                target_balance_after=money(
                    target_available + normalized_amount
                ),
                source_balance_version=source_summary.version,
                target_balance_version=target_summary.version,
            )
            db.add(allocation)
            await db.flush()
            today = datetime.now(BANGKOK).date()
            db.add_all(
                [
                    FundLedgerEntry(
                        allocation_id=allocation.id,
                        bucket_id=source_bucket.id,
                        direction="DEBIT",
                        entry_type="ALLOCATION",
                        amount=normalized_amount,
                        effective_date=today,
                        reason=reason,
                        created_by=actor,
                    ),
                    FundLedgerEntry(
                        allocation_id=allocation.id,
                        bucket_id=target_bucket.id,
                        direction="CREDIT",
                        entry_type="ALLOCATION",
                        amount=normalized_amount,
                        effective_date=today,
                        reason=reason,
                        created_by=actor,
                    ),
                    FundAuditEvent(
                        event_type="fund_allocation.created",
                        allocation_id=allocation.id,
                        actor=actor,
                        detail={
                            "source_project_id": str(source_project_id),
                            "target_project_id": str(target_project_id),
                            "amount": str(normalized_amount),
                        },
                    ),
                ]
            )
            await db.flush()
            after_source = await calculate_fund_summary(
                db,
                source_project_id,
                locked_context=source_context,
            )
            after_target = await calculate_fund_summary(
                db,
                target_project_id,
                locked_context=target_context,
            )
            allocation.source_balance_after = _mutation_balance(after_source)
            allocation.target_balance_after = _mutation_balance(after_target)
            allocation.source_balance_version = after_source.version
            allocation.target_balance_version = after_target.version
            await db.flush()
    return await serialize_allocation(db, allocation)


async def reverse_allocation(
    db: AsyncSession,
    *,
    allocation_id: UUID,
    reason: str,
    idempotency_key: str,
    expected_source_balance_version: str | None,
    actor: str,
) -> FundAllocationResponse:
    reversal: FundAllocation
    async with db.begin():
        original_reference = (
            await db.execute(
                select(FundAllocation)
                .options(noload("*"))
                .where(FundAllocation.id == allocation_id)
            )
        ).scalar_one_or_none()
        if original_reference is None:
            raise FundDomainError(
                "ALLOCATION_NOT_FOUND", "Allocation not found.", status_code=404
            )
        source_party = await _party_for_bucket(db, original_reference.target_bucket_id)
        target_party = await _party_for_bucket(db, original_reference.source_bucket_id)
        await lock_project_budget_state(
            db, (source_party.project_id, target_party.project_id)
        )
        contexts = await _locked_bucket_contexts(
            db, (source_party.project_id, target_party.project_id)
        )
        await _advisory_idempotency_lock(db, idempotency_key)
        replay = (
            await db.execute(
                select(FundAllocation)
                .options(noload("*"))
                .where(FundAllocation.idempotency_key == idempotency_key)
            )
        ).scalar_one_or_none()
        if replay is not None:
            if replay.reversal_of != allocation_id:
                raise FundDomainError(
                    "IDEMPOTENCY_KEY_REUSED",
                    "The idempotency key was already used for another operation.",
                    status_code=409,
                )
            reversal = replay
        else:
            original = (
                await db.execute(
                    select(FundAllocation)
                    .options(noload("*"))
                    .where(FundAllocation.id == allocation_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if original is None:
                raise FundDomainError("ALLOCATION_NOT_FOUND", "Allocation not found.", status_code=404)
            if original.status == "REVERSED" or original.reversal_of is not None:
                raise FundDomainError(
                    "ALLOCATION_ALREADY_REVERSED",
                    "This allocation cannot be reversed again.",
                    status_code=409,
                )

            source_context = contexts[source_party.project_id]
            target_context = contexts[target_party.project_id]
            _validate_active_context(source_context, target=False)
            _validate_active_context(target_context, target=True)
            source_summary = await calculate_fund_summary(
                db,
                source_party.project_id,
                locked_context=source_context,
            )
            target_summary = await calculate_fund_summary(
                db,
                target_party.project_id,
                locked_context=target_context,
            )
            source_available = _mutation_balance(source_summary)
            target_available = _mutation_balance(target_summary)
            if (
                expected_source_balance_version
                and source_summary.version != expected_source_balance_version
            ):
                raise FundDomainError(
                    "STALE_FUND_BALANCE",
                    "The returning Bucket balance changed. Refresh before reversing.",
                    status_code=409,
                    context={"current_version": source_summary.version},
                )
            amount = money(original.amount)
            if amount > source_available:
                raise FundDomainError(
                    "REVERSAL_WOULD_OVERDRAW_TARGET",
                    "The returning Bucket does not have enough Available Margin.",
                    status_code=409,
                    context={
                        "available_margin_to_allocate": str(
                            source_available
                        ),
                    },
                )

            reversal = FundAllocation(
                reference_no=_reference("FR"),
                source_bucket_id=original.target_bucket_id,
                target_bucket_id=original.source_bucket_id,
                amount=amount,
                currency=original.currency,
                reason=reason,
                status="POSTED",
                reversal_of=original.id,
                idempotency_key=idempotency_key,
                created_by=actor,
                source_balance_before=source_available,
                source_balance_after=money(
                    source_available - amount
                ),
                target_balance_before=target_available,
                target_balance_after=money(
                    target_available + amount
                ),
                source_balance_version=source_summary.version,
                target_balance_version=target_summary.version,
            )
            original.status = "REVERSED"
            db.add(reversal)
            await db.flush()
            today = datetime.now(BANGKOK).date()
            db.add_all(
                [
                    FundLedgerEntry(
                        allocation_id=reversal.id,
                        bucket_id=original.target_bucket_id,
                        direction="DEBIT",
                        entry_type="REVERSAL",
                        amount=amount,
                        effective_date=today,
                        reason=reason,
                        created_by=actor,
                    ),
                    FundLedgerEntry(
                        allocation_id=reversal.id,
                        bucket_id=original.source_bucket_id,
                        direction="CREDIT",
                        entry_type="REVERSAL",
                        amount=amount,
                        effective_date=today,
                        reason=reason,
                        created_by=actor,
                    ),
                    FundAuditEvent(
                        event_type="fund_allocation.reversed",
                        allocation_id=reversal.id,
                        actor=actor,
                        detail={
                            "original_allocation_id": str(original.id),
                            "amount": str(amount),
                        },
                    ),
                ]
            )
            await db.flush()
            after_source = await calculate_fund_summary(
                db,
                source_party.project_id,
                locked_context=source_context,
            )
            after_target = await calculate_fund_summary(
                db,
                target_party.project_id,
                locked_context=target_context,
            )
            reversal.source_balance_after = _mutation_balance(after_source)
            reversal.target_balance_after = _mutation_balance(after_target)
            reversal.source_balance_version = after_source.version
            reversal.target_balance_version = after_target.version
            await db.flush()
    return await serialize_allocation(db, reversal)


async def set_operations_opening_balance(
    db: AsyncSession,
    *,
    project_id: UUID,
    amount: Decimal,
    activation_month: str,
    reason: str,
    idempotency_key: str,
    actor: str,
) -> FundSummaryResponse:
    effective_date = date.fromisoformat(f"{activation_month}-01")
    if not is_first_day_of_month(effective_date):
        raise FundDomainError(
            "INVALID_BALANCE_START_DATE",
            "Balance Start Date must be the first day of a month.",
            status_code=400,
        )
    async with db.begin():
        await lock_project_budget_state(db, (project_id,))
        bucket, project = await _bucket_context(db, project_id, lock=True)
        await _advisory_idempotency_lock(db, idempotency_key)
        if project.system_key != OPERATIONS_SYSTEM_KEY:
            raise FundDomainError(
                "INVALID_OPERATIONS_BUCKET",
                "Opening Forecast Balance is only available for Company Operations.",
                status_code=400,
            )
        replay = (
            await db.execute(
                select(FundLedgerEntry)
                .options(noload("*"))
                .where(FundLedgerEntry.idempotency_key == idempotency_key)
            )
        ).scalar_one_or_none()
        if replay is not None:
            if (
                replay.bucket_id != bucket.id
                or money(replay.amount) != money(amount)
                or replay.effective_date != effective_date
            ):
                raise FundDomainError(
                    "IDEMPOTENCY_KEY_REUSED",
                    "The idempotency key was already used for another operation.",
                    status_code=409,
                )
        else:
            existing_opening = (
                await db.execute(
                    select(FundLedgerEntry.id)
                    .where(FundLedgerEntry.bucket_id == bucket.id)
                    .where(FundLedgerEntry.entry_type == "OPENING_BALANCE")
                )
            ).scalar_one_or_none()
            if existing_opening is not None or bucket.balance_start_date is not None:
                raise FundDomainError(
                    "OPENING_BALANCE_ALREADY_SET",
                    "The Initial Opening Forecast Balance has already been confirmed.",
                    status_code=409,
                )
            bucket.balance_start_date = effective_date
            bucket.status = "ACTIVE"
            db.add_all(
                [
                    FundLedgerEntry(
                        bucket_id=bucket.id,
                        direction="CREDIT",
                        entry_type="OPENING_BALANCE",
                        amount=money(amount),
                        effective_date=effective_date,
                        reason=reason,
                        created_by=actor,
                        idempotency_key=idempotency_key,
                    ),
                    FundAuditEvent(
                        event_type="operations_bucket.opening_forecast_balance_set",
                        bucket_id=bucket.id,
                        actor=actor,
                        detail={
                            "project_id": str(project.id),
                            "amount": str(money(amount)),
                            "balance_start_date": effective_date.isoformat(),
                        },
                    ),
                ]
            )
            await db.flush()
        summary = await calculate_fund_summary(
            db,
            project_id,
            locked_context=(bucket, project),
        )
    return summary


async def get_allocation(db: AsyncSession, allocation_id: UUID) -> FundAllocationResponse:
    allocation = (
        await db.execute(
            select(FundAllocation)
            .options(noload("*"))
            .where(FundAllocation.id == allocation_id)
        )
    ).scalar_one_or_none()
    if allocation is None:
        raise FundDomainError("ALLOCATION_NOT_FOUND", "Allocation not found.", status_code=404)
    return await serialize_allocation(db, allocation)


def _encode_cursor(created_at: datetime, allocation_id: UUID) -> str:
    raw = f"{created_at.isoformat()}|{allocation_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded).decode("utf-8")
        timestamp, allocation_id = raw.rsplit("|", 1)
        return datetime.fromisoformat(timestamp), UUID(allocation_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise FundDomainError("INVALID_CURSOR", "The allocation cursor is invalid.", status_code=400) from exc


async def list_allocations(
    db: AsyncSession,
    *,
    project_id: UUID | None,
    cursor: str | None,
    limit: int,
) -> FundAllocationListResponse:
    statement = select(FundAllocation).options(noload("*"))
    if project_id is not None:
        bucket_id = (
            await db.execute(select(FundBucket.id).where(FundBucket.project_id == project_id))
        ).scalar_one_or_none()
        if bucket_id is None:
            raise FundDomainError("FUND_BUCKET_MISSING", "Project fund bucket not found.", status_code=404)
        statement = statement.where(
            or_(
                FundAllocation.source_bucket_id == bucket_id,
                FundAllocation.target_bucket_id == bucket_id,
            )
        )
    if cursor:
        cursor_time, cursor_id = _decode_cursor(cursor)
        statement = statement.where(
            or_(
                FundAllocation.created_at < cursor_time,
                and_(
                    FundAllocation.created_at == cursor_time,
                    FundAllocation.id < cursor_id,
                ),
            )
        )
    allocations = list(
        (
            await db.execute(
                statement.order_by(
                    FundAllocation.created_at.desc(),
                    FundAllocation.id.desc(),
                ).limit(limit + 1)
            )
        ).scalars().all()
    )
    has_more = len(allocations) > limit
    page = allocations[:limit]
    items = [await serialize_allocation(db, allocation) for allocation in page]
    next_cursor = (
        _encode_cursor(page[-1].created_at, page[-1].id)
        if has_more and page and page[-1].created_at is not None
        else None
    )
    return FundAllocationListResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )
