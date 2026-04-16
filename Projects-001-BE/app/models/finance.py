"""
ORM Models — Finance Domain (installments, transactions).
Columns for installments match TDD Section 1.1 EXACTLY.
NOTE: The transactions table schema is inferred from TDD Router 6
      (Admin Approve → record into transactions) and the Net Payable
      formula in Business Requirements Section 3.5.
"""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Table: installments
# ---------------------------------------------------------------------------
class Installment(Base):
    __tablename__ = "installments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boq_item_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_items.id"), nullable=False
    )

    subcontractor_id = Column(String, nullable=True)
    expense_category = Column(String, nullable=True)    # Concrete, Steel, Paint …
    expense_type = Column(String, nullable=True)        # Installment, Labor, Material
    cost_type = Column(String, nullable=True)           # MATERIAL, LABOR, BOTH
    installment_no = Column(String, nullable=True)      # e.g. '2', '2.1-ADVANCE'
    amount = Column(Numeric(15, 2), default=0)
    status = Column(String, nullable=False, server_default="LOCKED")
    due_date = Column(Date, nullable=True)              # Customer-side payment due
    is_overdue = Column(Boolean, default=False)

    # Relationships
    boq_item = relationship("BOQItem", back_populates="installments")
    transactions = relationship(
        "Transaction", back_populates="installment", lazy="selectin"
    )


# ---------------------------------------------------------------------------
# Table: transactions
# Inferred from TDD Router 6 (approve → record) and BRD §3.5 Net Payable:
#   Net Payable = (Base Amount + VAT) - WHT - Advance Deduction - Retention
# ---------------------------------------------------------------------------
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    installment_id = Column(
        UUID(as_uuid=True), ForeignKey("installments.id"), nullable=False
    )

    subcontractor_id = Column(String, nullable=True)
    base_amount = Column(Numeric(15, 2), default=0)
    vat_amount = Column(Numeric(15, 2), default=0)
    wht_amount = Column(Numeric(15, 2), default=0)
    retention_amount = Column(Numeric(15, 2), default=0)
    advance_deduction = Column(Numeric(15, 2), default=0)
    net_payable = Column(Numeric(15, 2), default=0)

    approved_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    installment = relationship("Installment", back_populates="transactions")
