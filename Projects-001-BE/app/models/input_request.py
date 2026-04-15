"""
ORM models for the Input page flow.

This domain is separate from installments/bills so the frontend can submit
general income/expense requests without forcing them into the approval model.
"""

import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class InputRequest(Base):
    __tablename__ = "input_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )

    entry_type = Column(String, nullable=False)  # EXPENSE | INCOME
    requester_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    request_date = Column(Date, nullable=False)

    work_type = Column(String, nullable=True)
    request_type = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    vendor_name = Column(String, nullable=True)
    receipt_no = Column(String, nullable=True)
    document_date = Column(Date, nullable=True)

    bank_name = Column(String, nullable=True)
    account_no = Column(String, nullable=True)
    account_name = Column(String, nullable=True)

    amount = Column(Numeric(15, 2), nullable=False, default=0)
    approved_amount = Column(Numeric(15, 2), nullable=True)

    receipt_file_name = Column(String, nullable=True)
    receipt_content_type = Column(String, nullable=True)
    receipt_storage_key = Column(String, nullable=True)
    is_duplicate_flag = Column(Boolean, nullable=False, default=False)
    duplicate_reason = Column(Text, nullable=True)
    duplicate_of_request_id = Column(UUID(as_uuid=True), nullable=True)

    status = Column(String, nullable=False, default="PENDING_ADMIN")
    review_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_reference = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    project = relationship("Project", back_populates="input_requests", lazy="selectin")
