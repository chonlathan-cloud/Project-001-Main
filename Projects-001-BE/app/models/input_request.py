"""
ORM models for the Input page flow.

This domain is separate from installments/bills so the frontend can submit
general income/expense requests without forcing them into the approval model.
"""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
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


class InputRequest(Base):
    __tablename__ = "input_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )

    subcontractor_id = Column(String, nullable=True)
    entry_type = Column(String, nullable=False)  # EXPENSE | INCOME
    requester_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    request_date = Column(Date, nullable=False)

    work_type = Column(String, nullable=True)
    request_type = Column(String, nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    note = Column(Text, nullable=True)
    vendor_name = Column(String, nullable=True)
    vendor_tax_id = Column(String, nullable=True)
    vendor_branch = Column(String, nullable=True)
    vendor_address = Column(Text, nullable=True)
    receipt_no = Column(String, nullable=True)
    document_date = Column(Date, nullable=True)
    accounting_vat_mode = Column(String, nullable=True)  # no_vat | vat_inclusive | vat_exclusive
    accounting_wht_rate = Column(Numeric(5, 2), nullable=True)

    bank_name = Column(String, nullable=True)
    account_no = Column(String, nullable=True)
    account_name = Column(String, nullable=True)

    amount = Column(Numeric(15, 2), nullable=False, default=0)
    approved_amount = Column(Numeric(15, 2), nullable=True)

    receipt_file_name = Column(String, nullable=True)
    receipt_content_type = Column(String, nullable=True)
    receipt_storage_key = Column(String, nullable=True)
    ocr_raw_json = Column(JSON, nullable=True)
    ocr_low_confidence_fields = Column(JSON, nullable=True)
    is_duplicate_flag = Column(Boolean, nullable=False, default=False)
    duplicate_reason = Column(Text, nullable=True)
    duplicate_of_request_id = Column(UUID(as_uuid=True), nullable=True)

    status = Column(String, nullable=False, default="PENDING_ADMIN")
    review_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_reference = Column(String, nullable=True)

    accounting_ready = Column(Boolean, nullable=False, default=False)
    accounting_readiness_errors = Column(JSON, nullable=False, default=list)
    flowaccount_sync_status = Column(String, nullable=False, default="NOT_READY")
    flowaccount_expense_id = Column(String, nullable=True)
    flowaccount_document_no = Column(String, nullable=True)
    flowaccount_external_document_id = Column(String, nullable=True)
    flowaccount_synced_at = Column(DateTime(timezone=True), nullable=True)
    flowaccount_sync_error = Column(Text, nullable=True)
    flowaccount_attachment_status = Column(String, nullable=False, default="NOT_READY")
    flowaccount_attachment_error = Column(Text, nullable=True)
    flowaccount_attachment_synced_at = Column(DateTime(timezone=True), nullable=True)
    flowaccount_supplier_invoice_status = Column(String, nullable=False, default="NOT_READY")
    flowaccount_supplier_invoice_error = Column(Text, nullable=True)
    flowaccount_supplier_invoice_id = Column(String, nullable=True)
    flowaccount_supplier_invoice_synced_at = Column(DateTime(timezone=True), nullable=True)
    flowaccount_payment_status = Column(String, nullable=False, default="NOT_READY")
    flowaccount_payment_error = Column(Text, nullable=True)
    flowaccount_payment_synced_at = Column(DateTime(timezone=True), nullable=True)
    flowaccount_linked_manually = Column(Boolean, nullable=False, default=False)
    flowaccount_duplicate_override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    project = relationship("Project", back_populates="input_requests", lazy="selectin")
    line_items = relationship(
        "InputRequestLineItem",
        back_populates="input_request",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InputRequestLineItem.line_no",
    )
    payment = relationship(
        "InputPayment",
        back_populates="input_request",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,
    )


class InputRequestLineItem(Base):
    __tablename__ = "input_request_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    input_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("input_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_no = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=False)
    qty = Column(Numeric(15, 4), nullable=False, default=1)
    unit_price = Column(Numeric(15, 2), nullable=False, default=0)
    amount = Column(Numeric(15, 2), nullable=False, default=0)
    work_type = Column(String, nullable=True)
    request_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    input_request = relationship("InputRequest", back_populates="line_items")


class InputPaymentReferenceCounter(Base):
    """Atomic daily sequence used by human-readable payment references."""

    __tablename__ = "input_payment_reference_counters"

    reference_date = Column(Date, primary_key=True)
    entry_type = Column(String, primary_key=True)  # EXPENSE | INCOME
    last_sequence = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InputPayment(Base):
    """One full settlement for an approved Input request in the beta workflow."""

    __tablename__ = "input_payments"
    __table_args__ = (
        UniqueConstraint("input_request_id", name="uq_input_payments_input_request_id"),
        UniqueConstraint("internal_reference", name="uq_input_payments_internal_reference"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    input_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("input_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    internal_reference = Column(String, nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False)
    payment_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    bank_transfer_reference = Column(String, nullable=True)
    paid_storage_prefix = Column(String, nullable=False)
    recorded_by = Column(String, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    input_request = relationship("InputRequest", back_populates="payment")
    confirmations = relationship(
        "InputPaymentConfirmation",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="InputPaymentConfirmation.created_at.desc()",
    )


class InputPaymentConfirmation(Base):
    """Subcontractor evidence confirming that a payment was received."""

    __tablename__ = "input_payment_confirmations"
    __table_args__ = (
        UniqueConstraint(
            "payment_id",
            "idempotency_key",
            name="uq_input_payment_confirmations_idempotency",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("input_payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subcontractor_id = Column(String, nullable=False, index=True)
    idempotency_key = Column(String, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="SUBMITTED")
    received_date = Column(Date, nullable=False)
    received_full_amount = Column(Boolean, nullable=False, default=True)
    note = Column(Text, nullable=True)
    file_name = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_key = Column(String, nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(String, nullable=True)
    verification_note = Column(Text, nullable=True)
    superseded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    payment = relationship("InputPayment", back_populates="confirmations")


class InputOptionSuggestion(Base):
    __tablename__ = "input_option_suggestions"

    option_type = Column(String, primary_key=True)
    value = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
