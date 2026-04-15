"""
Finance Service — Core Business Logic.

Implements:
  - Net Payable calculation  (BRD §3.5)
  - Split Installment / Advance Payment  (BRD §2.1, LLD §3.3)

All DB operations use SQLAlchemy 2.0 async syntax.
"""

import logging
import uuid
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import Installment, Transaction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Net Payable Calculation  (BRD §3.5)
#   Net Payable = (Base Amount + VAT) - WHT - Advance Deduction - Retention
# ---------------------------------------------------------------------------
async def calculate_net_payable(
    base_amount: Decimal,
    vat_rate: Decimal = Decimal("0.07"),
    wht_rate: Decimal = Decimal("0.03"),
    retention_rate: Decimal = Decimal("0.05"),
    advance_deduction: Decimal = Decimal("0"),
) -> dict:
    """
    Calculate the net payable amount after all deductions.

    Args:
        base_amount:       The gross bill amount.
        vat_rate:          VAT rate from the subcontractor profile (e.g. 0.07).
        wht_rate:          Withholding-tax rate (e.g. 0.03).
        retention_rate:    Performance-guarantee retention (e.g. 0.05).
        advance_deduction: Any prior advance amount to be repaid.

    Returns:
        dict with every component and the final net_payable.
    """
    vat_amount = base_amount * vat_rate
    wht_amount = base_amount * wht_rate
    retention_amount = base_amount * retention_rate
    net_payable = (base_amount + vat_amount) - wht_amount - advance_deduction - retention_amount

    return {
        "base_amount": float(base_amount),
        "vat_amount": float(vat_amount),
        "wht_amount": float(wht_amount),
        "retention_amount": float(retention_amount),
        "advance_deduction": float(advance_deduction),
        "net_payable": float(net_payable),
    }


# ---------------------------------------------------------------------------
# Split Installment / Advance Payment  (BRD §2.1, LLD §3.3)
# ---------------------------------------------------------------------------
async def process_advance_request(
    session: AsyncSession,
    installment_id: UUID,
    advance_percent: float,
) -> dict:
    """
    Split an existing installment into an ADVANCE portion and a REMAINING
    portion.  Uses SELECT … FOR UPDATE to prevent race conditions.

    Business rules (BRD §2.1):
      - Advance may not exceed 50 % of the installment amount.
      - Original record becomes "<no>.2-REM" (status LOCKED).
      - New record becomes "<no>.1-ADV" (status PENDING_ADMIN).
      - Total value stays exactly 100 % of the original BOQ.

    Args:
        session:          An AsyncSession (already inside a request scope).
        installment_id:   UUID of the installment to split.
        advance_percent:  Percentage to advance (0 < x ≤ 50).

    Returns:
        dict describing the two resulting installment records.

    Raises:
        HTTPException 404  if the installment does not exist.
        HTTPException 400  if the percent exceeds the allowed limit.
        HTTPException 500  on any unexpected DB error (after rollback).
    """
    try:
        # 1. Lock the row to prevent concurrent modifications
        result = await session.execute(
            select(Installment)
            .filter_by(id=installment_id)
            .with_for_update()
        )
        installment = result.scalar_one_or_none()

        if installment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Installment {installment_id} not found.",
            )

        # 2. Validate advance percentage
        if advance_percent <= 0 or advance_percent > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Advance percent must be between 0 (exclusive) and 50 (inclusive).",
            )

        # 3. Calculate split amounts
        advance_amount = installment.amount * Decimal(str(advance_percent)) / Decimal("100")
        remaining_amount = installment.amount - advance_amount

        original_no = installment.installment_no or "1"

        # 4. Create the ADVANCE record (e.g. "2.1-ADV")
        advance_record = Installment(
            id=uuid.uuid4(),
            boq_item_id=installment.boq_item_id,
            expense_category=installment.expense_category,
            expense_type=installment.expense_type,
            cost_type=installment.cost_type,
            installment_no=f"{original_no}.1-ADV",
            amount=advance_amount,
            status="PENDING_ADMIN",
            due_date=installment.due_date,
            is_overdue=False,
        )
        session.add(advance_record)

        # 5. Update the original record to REMAINING (e.g. "2.2-REM")
        installment.installment_no = f"{original_no}.2-REM"
        installment.amount = remaining_amount
        installment.status = "LOCKED"

        # 6. Commit the transaction
        await session.commit()

        logger.info(
            "Advance processed: %s → ADV %.2f / REM %.2f",
            installment_id,
            advance_amount,
            remaining_amount,
        )

        return {
            "advance": {
                "id": str(advance_record.id),
                "installment_no": advance_record.installment_no,
                "amount": float(advance_amount),
                "status": advance_record.status,
            },
            "remaining": {
                "id": str(installment.id),
                "installment_no": installment.installment_no,
                "amount": float(remaining_amount),
                "status": installment.status,
            },
        }

    except HTTPException:
        # Re-raise known HTTP errors without rolling back
        raise

    except Exception as exc:
        await session.rollback()
        logger.exception("Failed to process advance for installment %s", installment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process advance request: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Record Approved Transaction  (TDD Router 6)
# ---------------------------------------------------------------------------
async def record_approved_transaction(
    session: AsyncSession,
    installment_id: UUID,
    base_amount: Decimal,
    vat_rate: Decimal = Decimal("0.07"),
    wht_rate: Decimal = Decimal("0.03"),
    retention_rate: Decimal = Decimal("0.05"),
    advance_deduction: Decimal = Decimal("0"),
) -> Transaction:
    """
    Create a Transaction record when an Admin approves a bill.

    Calculates the net payable and persists the full deduction breakdown.
    """
    try:
        breakdown = await calculate_net_payable(
            base_amount=base_amount,
            vat_rate=vat_rate,
            wht_rate=wht_rate,
            retention_rate=retention_rate,
            advance_deduction=advance_deduction,
        )

        transaction = Transaction(
            id=uuid.uuid4(),
            installment_id=installment_id,
            base_amount=Decimal(str(breakdown["base_amount"])),
            vat_amount=Decimal(str(breakdown["vat_amount"])),
            wht_amount=Decimal(str(breakdown["wht_amount"])),
            retention_amount=Decimal(str(breakdown["retention_amount"])),
            advance_deduction=Decimal(str(breakdown["advance_deduction"])),
            net_payable=Decimal(str(breakdown["net_payable"])),
        )
        session.add(transaction)
        await session.commit()

        logger.info(
            "Transaction recorded for installment %s — net payable: %.2f",
            installment_id,
            breakdown["net_payable"],
        )
        return transaction

    except Exception as exc:
        await session.rollback()
        logger.exception("Failed to record transaction for installment %s", installment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record transaction: {exc}",
        ) from exc
