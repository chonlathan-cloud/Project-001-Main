"""Immutable project-fund bucket, allocation, ledger, and audit models."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class FundBucket(Base):
    __tablename__ = "fund_buckets"
    __table_args__ = (
        CheckConstraint("bucket_type IN ('PROJECT', 'OPERATIONS')", name="ck_fund_bucket_type"),
        CheckConstraint("currency = 'THB'", name="ck_fund_bucket_currency"),
        CheckConstraint("status IN ('SETUP', 'ACTIVE', 'LOCKED')", name="ck_fund_bucket_status"),
        CheckConstraint("protected_reserve >= 0", name="ck_fund_bucket_reserve"),
        CheckConstraint(
            "balance_start_date IS NULL OR EXTRACT(DAY FROM balance_start_date) = 1",
            name="ck_fund_bucket_start_month",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    bucket_type = Column(String, nullable=False, default="PROJECT")
    currency = Column(String(3), nullable=False, default="THB")
    balance_start_date = Column(Date, nullable=True)
    protected_reserve = Column(Numeric(15, 2), nullable=False, default=0)
    status = Column(String, nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    project = relationship("Project", back_populates="fund_bucket", lazy="selectin")


class FundAllocation(Base):
    __tablename__ = "fund_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_fund_allocation_positive_amount"),
        CheckConstraint("source_bucket_id <> target_bucket_id", name="ck_fund_allocation_distinct_buckets"),
        CheckConstraint("currency = 'THB'", name="ck_fund_allocation_currency"),
        CheckConstraint("status IN ('POSTED', 'REVERSED')", name="ck_fund_allocation_status"),
        UniqueConstraint("reversal_of", name="uq_fund_allocation_reversal_of"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_no = Column(String, nullable=False, unique=True)
    source_bucket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fund_buckets.id"),
        nullable=False,
        index=True,
    )
    target_bucket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fund_buckets.id"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="THB")
    reason = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="POSTED")
    reversal_of = Column(
        UUID(as_uuid=True),
        ForeignKey("fund_allocations.id"),
        nullable=True,
    )
    idempotency_key = Column(String, nullable=False, unique=True)
    created_by = Column(String, nullable=False)
    source_balance_before = Column(Numeric(15, 2), nullable=False)
    source_balance_after = Column(Numeric(15, 2), nullable=False)
    target_balance_before = Column(Numeric(15, 2), nullable=False)
    target_balance_after = Column(Numeric(15, 2), nullable=False)
    source_balance_version = Column(String, nullable=False)
    target_balance_version = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_bucket = relationship("FundBucket", foreign_keys=[source_bucket_id], lazy="selectin")
    target_bucket = relationship("FundBucket", foreign_keys=[target_bucket_id], lazy="selectin")
    reversed_allocation = relationship(
        "FundAllocation",
        remote_side=[id],
        foreign_keys=[reversal_of],
        lazy="selectin",
        uselist=False,
    )
    ledger_entries = relationship("FundLedgerEntry", back_populates="allocation", lazy="selectin")


class FundLedgerEntry(Base):
    __tablename__ = "fund_ledger_entries"
    __table_args__ = (
        CheckConstraint("direction IN ('DEBIT', 'CREDIT')", name="ck_fund_ledger_direction"),
        CheckConstraint(
            "entry_type IN ('ALLOCATION', 'REVERSAL', 'OPENING_BALANCE', 'ADJUSTMENT')",
            name="ck_fund_ledger_entry_type",
        ),
        CheckConstraint("amount >= 0", name="ck_fund_ledger_nonnegative_amount"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allocation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fund_allocations.id"),
        nullable=True,
        index=True,
    )
    bucket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fund_buckets.id"),
        nullable=False,
        index=True,
    )
    direction = Column(String, nullable=False)
    entry_type = Column(String, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    effective_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    created_by = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    allocation = relationship("FundAllocation", back_populates="ledger_entries", lazy="selectin")
    bucket = relationship("FundBucket", lazy="selectin")


class FundAuditEvent(Base):
    __tablename__ = "fund_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String, nullable=False, index=True)
    allocation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fund_allocations.id"),
        nullable=True,
        index=True,
    )
    bucket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fund_buckets.id"),
        nullable=True,
        index=True,
    )
    actor = Column(String, nullable=False)
    detail = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
