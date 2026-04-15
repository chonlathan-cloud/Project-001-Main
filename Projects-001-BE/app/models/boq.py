"""
ORM Models — BOQ Domain (projects, boq_items).
Columns match TDD Section 1.1 EXACTLY.
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Table: projects
# ---------------------------------------------------------------------------
class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    project_type = Column(String, nullable=False)
    overhead_percent = Column(Numeric(5, 2), default=0)
    profit_percent = Column(Numeric(5, 2), default=0)
    vat_percent = Column(Numeric(5, 2), default=7.00)
    contingency_budget = Column(Numeric(15, 2), default=0)
    status = Column(String, nullable=False, server_default=text("'ACTIVE'"))

    # Relationships
    boq_items = relationship("BOQItem", back_populates="project", lazy="selectin")
    input_requests = relationship(
        "InputRequest", back_populates="project", lazy="selectin"
    )


# ---------------------------------------------------------------------------
# Table: boq_items  (Supports WBS and Material/Labor)
# ---------------------------------------------------------------------------
class BOQItem(Base):
    __tablename__ = "boq_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )

    # BOQ classification
    boq_type = Column(String, nullable=False)          # CUSTOMER | SUBCONTRACTOR
    sheet_name = Column(String, nullable=True)          # e.g. 'AC', 'SN', 'EE'

    # WBS Hierarchy
    wbs_level = Column(Integer, nullable=False)         # 1=Main, 2=Sub, 3=Item
    parent_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_items.id"), nullable=True
    )

    # Item details
    item_no = Column(String, nullable=True)             # e.g. '1', '2.1', '-'
    description = Column(String, nullable=True)
    qty = Column(Numeric(15, 2), default=0)
    unit = Column(String, nullable=True)

    # Material vs Labor pricing
    material_unit_price = Column(Numeric(15, 2), default=0)
    labor_unit_price = Column(Numeric(15, 2), default=0)
    total_material = Column(Numeric(15, 2), default=0)
    total_labor = Column(Numeric(15, 2), default=0)
    grand_total = Column(Numeric(15, 2), default=0)

    # AI Vector for Semantic Search (pgvector)
    embedding = Column(Vector(768), nullable=True)

    # SCD Type 2 versioning
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)  # NULL = current

    # Relationships
    project = relationship("Project", back_populates="boq_items")
    children = relationship(
        "BOQItem",
        backref="parent",  # BOQItem.parent -> parent BOQItem
        remote_side=[id],
        lazy="selectin",
    )
    installments = relationship(
        "Installment", back_populates="boq_item", lazy="selectin"
    )
