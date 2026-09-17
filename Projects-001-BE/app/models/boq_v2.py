"""Additive BOQ V2 foundation models.

These tables are intentionally not exposed through public mutation routes in
Phase 1. Existing projects continue to resolve to the legacy BOQ source unless
an explicit future cutover command creates a V2 source selection.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


QUANTITY = Numeric(20, 4)
MONEY = Numeric(20, 2)


class BOQV2DocumentSequence(Base):
    __tablename__ = "boq_v2_document_sequences"
    __table_args__ = (
        CheckConstraint("next_value > 0", name="ck_boq_v2_document_sequence_value"),
    )

    sequence_key = Column(String(32), primary_key=True)
    next_value = Column(Integer, nullable=False, server_default=text("1"))
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2Document(Base):
    __tablename__ = "boq_v2_documents"
    __table_args__ = (
        CheckConstraint(
            "document_kind IN ('MAIN', 'ALTERNATIVE', 'CHANGE_ORDER')",
            name="ck_boq_v2_document_kind",
        ),
        CheckConstraint(
            "(document_kind = 'CHANGE_ORDER' AND direction IN ('ADD', 'DEDUCT')) "
            "OR (document_kind <> 'CHANGE_ORDER' AND direction IS NULL)",
            name="ck_boq_v2_document_direction",
        ),
        CheckConstraint(
            "(document_kind = 'ALTERNATIVE' AND alternative_group_id IS NOT NULL) "
            "OR (document_kind <> 'ALTERNATIVE' AND alternative_group_id IS NULL)",
            name="ck_boq_v2_document_alternative_group",
        ),
        CheckConstraint(
            "(document_kind = 'CHANGE_ORDER' AND base_baseline_id IS NOT NULL "
            "AND base_baseline_version IS NOT NULL) OR "
            "(document_kind <> 'CHANGE_ORDER' AND base_baseline_id IS NULL "
            "AND base_baseline_version IS NULL)",
            name="ck_boq_v2_document_change_order_baseline",
        ),
        CheckConstraint(
            "revision_counter > 0", name="ck_boq_v2_document_revision_counter"
        ),
        UniqueConstraint("document_number", name="uq_boq_v2_document_number"),
        Index("ix_boq_v2_documents_project", "project_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    document_number = Column(String(64), nullable=False)
    document_kind = Column(String(24), nullable=False)
    direction = Column(String(8), nullable=True)
    alternative_group_id = Column(UUID(as_uuid=True), nullable=True)
    base_baseline_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "boq_v2_project_baselines.id",
            name="fk_boq_v2_documents_base_baseline",
            use_alter=True,
        ),
        nullable=True,
    )
    base_baseline_version = Column(Integer, nullable=True)
    revision_counter = Column(Integer, nullable=False, server_default=text("1"))
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2Revision(Base):
    __tablename__ = "boq_v2_revisions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'ISSUED', 'ACCEPTED', 'WITHDRAWN', "
            "'REJECTED', 'SUPERSEDED')",
            name="ck_boq_v2_revision_status",
        ),
        CheckConstraint("revision_number > 0", name="ck_boq_v2_revision_number"),
        CheckConstraint("version > 0", name="ck_boq_v2_revision_version"),
        CheckConstraint("currency = 'THB'", name="ck_boq_v2_revision_currency"),
        CheckConstraint(
            "vat_rate >= 0 AND vat_rate <= 100",
            name="ck_boq_v2_revision_vat_rate",
        ),
        CheckConstraint(
            "discount_type IN ('NONE', 'PERCENT', 'FIXED')",
            name="ck_boq_v2_revision_discount_type",
        ),
        CheckConstraint(
            "discount_value >= 0 AND discount_amount >= 0 AND subtotal >= 0 "
            "AND vat_amount >= 0 AND grand_total >= 0",
            name="ck_boq_v2_revision_document_totals",
        ),
        CheckConstraint(
            "(base_baseline_id IS NULL AND base_baseline_version IS NULL) OR "
            "(base_baseline_id IS NOT NULL AND base_baseline_version IS NOT NULL)",
            name="ck_boq_v2_revision_baseline_identity",
        ),
        CheckConstraint(
            "required_cost_count >= 0 AND priced_cost_count >= 0 "
            "AND priced_cost_count <= required_cost_count",
            name="ck_boq_v2_revision_cost_counts",
        ),
        UniqueConstraint(
            "document_id", "revision_number", name="uq_boq_v2_revision_number"
        ),
        Index("ix_boq_v2_revisions_project_status", "project_id", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_documents.id"), nullable=False
    )
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    predecessor_revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=True
    )
    base_baseline_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "boq_v2_project_baselines.id",
            name="fk_boq_v2_revisions_base_baseline",
            use_alter=True,
        ),
        nullable=True,
    )
    base_baseline_version = Column(Integer, nullable=True)
    revision_number = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, server_default=text("'DRAFT'"))
    version = Column(Integer, nullable=False, server_default=text("1"))
    calculation_version = Column(
        String(32), nullable=False, server_default=text("'boq-v2-calc-v1'")
    )
    quotation_title = Column(String(500), nullable=True)
    customer_name = Column(String(500), nullable=True)
    customer_address = Column(Text, nullable=True)
    customer_tax_id = Column(String(64), nullable=True)
    customer_contact = Column(String(255), nullable=True)
    quotation_date = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    currency = Column(String(3), nullable=False, server_default=text("'THB'"))
    vat_rate = Column(QUANTITY, nullable=False, server_default=text("7"))
    discount_type = Column(String(16), nullable=False, server_default=text("'NONE'"))
    discount_value = Column(QUANTITY, nullable=False, server_default=text("0"))
    subtotal = Column(MONEY, nullable=False, server_default=text("0"))
    discount_amount = Column(MONEY, nullable=False, server_default=text("0"))
    net_sell_ex_vat = Column(MONEY, nullable=True)
    vat_amount = Column(MONEY, nullable=False, server_default=text("0"))
    grand_total = Column(MONEY, nullable=False, server_default=text("0"))
    payment_schedule = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    commercial_terms = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    document_pages = Column(
        JSON,
        nullable=False,
        server_default=text("'[\"BOQ\", \"PAYMENT_TERMS\", \"COMMERCIAL_TERMS\"]'::json"),
    )
    known_estimated_cost = Column(MONEY, nullable=True)
    forecast_cost = Column(MONEY, nullable=True)
    forecast_margin = Column(MONEY, nullable=True)
    required_cost_count = Column(Integer, nullable=False, server_default=text("0"))
    priced_cost_count = Column(Integer, nullable=False, server_default=text("0"))
    issued_by = Column(String, nullable=True)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2ScopeNode(Base):
    __tablename__ = "boq_v2_scope_nodes"
    __table_args__ = (
        CheckConstraint(
            "node_kind IN ('SECTION', 'CATEGORY', 'SUBCATEGORY', 'ITEM')",
            name="ck_boq_v2_scope_node_kind",
        ),
        CheckConstraint(
            "inclusion_state IN ('REQUIRED', 'OPTIONAL', 'EXCLUDED')",
            name="ck_boq_v2_scope_inclusion_state",
        ),
        CheckConstraint("position >= 0", name="ck_boq_v2_scope_position"),
        CheckConstraint(
            "quantity IS NULL OR quantity >= 0", name="ck_boq_v2_scope_quantity"
        ),
        CheckConstraint(
            "sell_material_unit_rate IS NULL OR sell_material_unit_rate >= 0",
            name="ck_boq_v2_scope_sell_material_rate",
        ),
        CheckConstraint(
            "sell_labor_unit_rate IS NULL OR sell_labor_unit_rate >= 0",
            name="ck_boq_v2_scope_sell_labor_rate",
        ),
        CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name="ck_boq_v2_scope_not_self_parent",
        ),
        CheckConstraint(
            "node_kind = 'ITEM' OR "
            "(quantity IS NULL AND unit IS NULL AND sell_material_unit_rate IS NULL "
            "AND sell_labor_unit_rate IS NULL AND sell_total = 0)",
            name="ck_boq_v2_structural_node_no_financials",
        ),
        UniqueConstraint(
            "revision_id", "logical_id", name="uq_boq_v2_scope_revision_logical"
        ),
        UniqueConstraint(
            "revision_id",
            "parent_id",
            "position",
            name="uq_boq_v2_scope_sibling_position",
        ),
        Index(
            "uq_boq_v2_scope_root_position",
            "revision_id",
            "position",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
        Index("ix_boq_v2_scope_project_revision", "project_id", "revision_id"),
        Index("ix_boq_v2_scope_parent", "revision_id", "parent_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    logical_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    parent_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_scope_nodes.id"), nullable=True
    )
    node_kind = Column(String(16), nullable=False)
    inclusion_state = Column(
        String(16), nullable=False, server_default=text("'REQUIRED'")
    )
    position = Column(Integer, nullable=False)
    item_code = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    specification = Column(Text, nullable=True)
    quantity = Column(QUANTITY, nullable=True)
    unit = Column(String, nullable=True)
    sell_material_unit_rate = Column(QUANTITY, nullable=True)
    sell_labor_unit_rate = Column(QUANTITY, nullable=True)
    sell_total = Column(MONEY, nullable=False, server_default=text("0"))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2CostPlan(Base):
    __tablename__ = "boq_v2_cost_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('WORKING', 'PUBLISHED', 'SUPERSEDED')",
            name="ck_boq_v2_cost_plan_status",
        ),
        CheckConstraint("version > 0", name="ck_boq_v2_cost_plan_version"),
        CheckConstraint(
            "completeness_state IN ('COMPLETE', 'INCOMPLETE')",
            name="ck_boq_v2_cost_plan_completeness",
        ),
        CheckConstraint(
            "required_count >= 0 AND priced_count >= 0 AND priced_count <= required_count",
            name="ck_boq_v2_cost_plan_counts",
        ),
        CheckConstraint(
            "completeness_state = 'INCOMPLETE' OR "
            "(required_count = priced_count AND forecast_cost IS NOT NULL)",
            name="ck_boq_v2_complete_cost_plan_values",
        ),
        UniqueConstraint("project_id", "version", name="uq_boq_v2_cost_plan_version"),
        Index(
            "uq_boq_v2_current_cost_plan",
            "project_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    scope_revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    version = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, server_default=text("'WORKING'"))
    is_current = Column(Boolean, nullable=False, server_default=text("true"))
    completeness_state = Column(
        String(16), nullable=False, server_default=text("'INCOMPLETE'")
    )
    required_count = Column(Integer, nullable=False, server_default=text("0"))
    priced_count = Column(Integer, nullable=False, server_default=text("0"))
    original_estimated_cost = Column(MONEY, nullable=True)
    agreed_cost = Column(MONEY, nullable=True)
    forecast_cost = Column(MONEY, nullable=True)
    calculation_version = Column(
        String(32), nullable=False, server_default=text("'boq-v2-calc-v1'")
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2CostComponent(Base):
    __tablename__ = "boq_v2_cost_components"
    __table_args__ = (
        CheckConstraint(
            "component_type IN ('MATERIAL', 'LABOR')",
            name="ck_boq_v2_cost_component_type",
        ),
        CheckConstraint(
            "quantity_basis IN ('INHERITED', 'OVERRIDDEN')",
            name="ck_boq_v2_cost_quantity_basis",
        ),
        CheckConstraint(
            "cost_state IN ('UNKNOWN', 'PRICED', 'NOT_APPLICABLE')",
            name="ck_boq_v2_cost_state",
        ),
        CheckConstraint("quantity >= 0", name="ck_boq_v2_cost_quantity"),
        CheckConstraint(
            "(cost_state = 'UNKNOWN' AND unit_rate IS NULL AND total IS NULL) OR "
            "(cost_state = 'NOT_APPLICABLE' AND unit_rate IS NULL AND total = 0) OR "
            "(cost_state = 'PRICED' AND unit_rate IS NOT NULL AND unit_rate >= 0 "
            "AND total IS NOT NULL)",
            name="ck_boq_v2_cost_state_values",
        ),
        CheckConstraint(
            "cost_state <> 'PRICED' OR unit_rate <> 0 OR "
            "length(trim(coalesce(explicit_zero_reason, ''))) > 0",
            name="ck_boq_v2_cost_explicit_zero_reason",
        ),
        UniqueConstraint(
            "cost_plan_id",
            "scope_node_id",
            "component_type",
            name="uq_boq_v2_cost_plan_node_component",
        ),
        Index("ix_boq_v2_cost_components_node", "scope_node_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cost_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_cost_plans.id"), nullable=False
    )
    scope_node_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_scope_nodes.id"), nullable=False
    )
    component_type = Column(String(16), nullable=False)
    quantity_basis = Column(
        String(16), nullable=False, server_default=text("'INHERITED'")
    )
    quantity = Column(QUANTITY, nullable=False)
    unit = Column(String, nullable=True)
    specification = Column(Text, nullable=True)
    basis_version = Column(Integer, nullable=False, server_default=text("1"))
    cost_state = Column(String(20), nullable=False, server_default=text("'UNKNOWN'"))
    unit_rate = Column(QUANTITY, nullable=True)
    total = Column(MONEY, nullable=True)
    explicit_zero_reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2ProjectBaseline(Base):
    __tablename__ = "boq_v2_project_baselines"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_boq_v2_baseline_version"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_boq_v2_baseline_effective_range",
        ),
        CheckConstraint(
            "NOT is_active OR (activated_at IS NOT NULL AND effective_to IS NULL)",
            name="ck_boq_v2_active_baseline_identity",
        ),
        UniqueConstraint("project_id", "version", name="uq_boq_v2_baseline_version"),
        Index(
            "uq_boq_v2_active_project_baseline",
            "project_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, nullable=False)
    main_revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    main_snapshot_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revision_snapshots.id"), nullable=True
    )
    cost_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_cost_plans.id"), nullable=True
    )
    is_active = Column(Boolean, nullable=False, server_default=text("false"))
    calculation_version = Column(
        String(32), nullable=False, server_default=text("'boq-v2-calc-v1'")
    )
    net_sell_ex_vat = Column(MONEY, nullable=False)
    original_estimated_cost = Column(MONEY, nullable=True)
    agreed_cost = Column(MONEY, nullable=True)
    forecast_cost = Column(MONEY, nullable=True)
    forecast_margin = Column(MONEY, nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2BaselineChangeOrder(Base):
    __tablename__ = "boq_v2_baseline_change_orders"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_boq_v2_baseline_co_position"),
        UniqueConstraint(
            "baseline_id", "revision_id", name="uq_boq_v2_baseline_co_revision"
        ),
        UniqueConstraint(
            "baseline_id", "document_id", name="uq_boq_v2_baseline_co_document"
        ),
        UniqueConstraint(
            "baseline_id", "position", name="uq_boq_v2_baseline_co_position"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    baseline_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_project_baselines.id"), nullable=False
    )
    revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_documents.id"), nullable=False
    )
    snapshot_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revision_snapshots.id"), nullable=False
    )
    position = Column(Integer, nullable=False)


class BOQV2ChangeOrderDeduction(Base):
    __tablename__ = "boq_v2_change_order_deductions"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_boq_v2_co_deduction_quantity"),
        CheckConstraint("amount >= 0", name="ck_boq_v2_co_deduction_amount"),
        UniqueConstraint(
            "revision_id",
            "target_logical_id",
            name="uq_boq_v2_co_deduction_target",
        ),
        Index(
            "ix_boq_v2_co_deduction_project_target",
            "project_id",
            "target_logical_id",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_documents.id"), nullable=False
    )
    revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    base_baseline_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_project_baselines.id"), nullable=False
    )
    base_baseline_version = Column(Integer, nullable=False)
    target_revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    target_logical_id = Column(UUID(as_uuid=True), nullable=False)
    quantity = Column(QUANTITY, nullable=False)
    unit_rate = Column(QUANTITY, nullable=False)
    amount = Column(MONEY, nullable=False)


class BOQV2RevisionSnapshot(Base):
    __tablename__ = "boq_v2_revision_snapshots"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('PREVIEW', 'ISSUE')",
            name="ck_boq_v2_snapshot_purpose",
        ),
        CheckConstraint(
            "lifecycle_status IN ('DRAFT', 'ISSUED')",
            name="ck_boq_v2_snapshot_lifecycle_status",
        ),
        CheckConstraint("source_version > 0", name="ck_boq_v2_snapshot_version"),
        UniqueConstraint(
            "revision_id",
            "source_version",
            "purpose",
            name="uq_boq_v2_snapshot_revision_version_purpose",
        ),
        Index("ix_boq_v2_snapshot_project_created", "project_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_documents.id"), nullable=False
    )
    revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    source_version = Column(Integer, nullable=False)
    purpose = Column(String(16), nullable=False)
    lifecycle_status = Column(String(16), nullable=False)
    calculation_version = Column(String(32), nullable=False)
    customer_payload = Column(JSON, nullable=False)
    internal_payload = Column(JSON, nullable=False)
    payload_sha256 = Column(String(64), nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2Acceptance(Base):
    __tablename__ = "boq_v2_acceptances"
    __table_args__ = (
        UniqueConstraint("revision_id", name="uq_boq_v2_acceptance_revision"),
        Index("ix_boq_v2_acceptance_project_recorded", "project_id", "recorded_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_documents.id"), nullable=False
    )
    revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    snapshot_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revision_snapshots.id"), nullable=False
    )
    agreed_date = Column(Date, nullable=False)
    actor = Column(String, nullable=False)
    evidence_reference = Column(String(1000), nullable=True)
    note = Column(Text, nullable=True)
    recorded_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2ExportArtifact(Base):
    __tablename__ = "boq_v2_export_artifacts"
    __table_args__ = (
        CheckConstraint(
            "audience IN ('CUSTOMER', 'INTERNAL')",
            name="ck_boq_v2_export_audience",
        ),
        CheckConstraint(
            "file_format IN ('XLSX', 'PDF')",
            name="ck_boq_v2_export_format",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'READY', 'FAILED')",
            name="ck_boq_v2_export_status",
        ),
        CheckConstraint(
            "audience = 'CUSTOMER' OR file_format = 'XLSX'",
            name="ck_boq_v2_internal_export_xlsx_only",
        ),
        Index("ix_boq_v2_export_project_created", "project_id", "created_at"),
        Index("ix_boq_v2_export_revision_created", "revision_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_documents.id"), nullable=False
    )
    revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    snapshot_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revision_snapshots.id"), nullable=False
    )
    calculation_version = Column(String(32), nullable=False)
    audience = Column(String(16), nullable=False)
    file_format = Column(String(8), nullable=False)
    cost_plan_version = Column(Integer, nullable=True)
    status = Column(String(16), nullable=False, server_default=text("'PENDING'"))
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(120), nullable=False)
    storage_key = Column(String, nullable=True)
    sha256 = Column(String(64), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    error_code = Column(String(120), nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)


class BOQV2ProjectBudgetSource(Base):
    __tablename__ = "boq_v2_project_budget_sources"
    __table_args__ = (
        CheckConstraint(
            "source_kind IN ('LEGACY', 'V2')", name="ck_boq_v2_budget_source_kind"
        ),
        CheckConstraint("version > 0", name="ck_boq_v2_budget_source_version"),
    )

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True)
    source_kind = Column(String(8), nullable=False, server_default=text("'LEGACY'"))
    version = Column(Integer, nullable=False, server_default=text("1"))
    updated_by = Column(String, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2CommandIdempotency(Base):
    __tablename__ = "boq_v2_command_idempotency"
    __table_args__ = (
        CheckConstraint(
            "status IN ('STARTED', 'COMPLETED', 'FAILED')",
            name="ck_boq_v2_idempotency_status",
        ),
        UniqueConstraint(
            "actor",
            "project_id",
            "command_type",
            "idempotency_key",
            name="uq_boq_v2_command_idempotency",
        ),
        Index("ix_boq_v2_idempotency_project_created", "project_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor = Column(String, nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    command_type = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False)
    request_hash = Column(String(64), nullable=False)
    aggregate_id = Column(UUID(as_uuid=True), nullable=True)
    response_reference = Column(JSON, nullable=True)
    status = Column(String(16), nullable=False, server_default=text("'STARTED'"))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)


class BOQV2AuditEvent(Base):
    __tablename__ = "boq_v2_audit_events"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_boq_v2_audit_event_key"),
        Index("ix_boq_v2_audit_project_created", "project_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_key = Column(String, nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    actor = Column(String, nullable=False)
    command_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    calculation_version = Column(String(32), nullable=True)
    before_reference = Column(JSON, nullable=True)
    after_reference = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
