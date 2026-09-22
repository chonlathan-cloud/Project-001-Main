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


class BOQV2QuotationSection(Base):
    __tablename__ = "boq_v2_quotation_sections"
    __table_args__ = (
        CheckConstraint(
            "section_type IN ('SUMMARY', 'DETAILED_BOQ', 'VISUAL', "
            "'PAYMENT_TERMS', 'TERMS', 'ACCEPTANCE')",
            name="ck_boq_v2_quote_section_type",
        ),
        CheckConstraint("position >= 0", name="ck_boq_v2_quote_section_position"),
        UniqueConstraint(
            "revision_id", "section_type", name="uq_boq_v2_quote_section_type"
        ),
        UniqueConstraint(
            "revision_id", "position", name="uq_boq_v2_quote_section_position"
        ),
        Index("ix_boq_v2_quote_section_project", "project_id", "revision_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("boq_v2_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    section_type = Column(String(24), nullable=False)
    enabled = Column(Boolean, nullable=False, server_default=text("true"))
    position = Column(Integer, nullable=False)
    title_th = Column(String(500), nullable=True)
    title_en = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2QuotationMedia(Base):
    __tablename__ = "boq_v2_quotation_media"
    __table_args__ = (
        CheckConstraint(
            "origin_type IN ('UPLOAD', 'DAILY_REPORT', 'INSPECTION')",
            name="ck_boq_v2_quote_media_origin",
        ),
        CheckConstraint("size_bytes > 0", name="ck_boq_v2_quote_media_size"),
        CheckConstraint(
            "width > 0 AND height > 0", name="ck_boq_v2_quote_media_dimensions"
        ),
        Index("ix_boq_v2_quote_media_project", "project_id", "created_at"),
        Index("ix_boq_v2_quote_media_revision", "revision_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("boq_v2_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    origin_type = Column(String(20), nullable=False)
    origin_id = Column(String(255), nullable=True)
    storage_key = Column(String, nullable=False)
    original_filename = Column(String(500), nullable=True)
    content_type = Column(String(120), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2QuotationVisualPage(Base):
    __tablename__ = "boq_v2_quotation_visual_pages"
    __table_args__ = (
        CheckConstraint(
            "layout IN ('SINGLE', 'TWO_UP', 'FOUR_UP')",
            name="ck_boq_v2_quote_visual_layout",
        ),
        CheckConstraint("position >= 0", name="ck_boq_v2_quote_visual_position"),
        UniqueConstraint(
            "revision_id", "position", name="uq_boq_v2_quote_visual_position"
        ),
        Index("ix_boq_v2_quote_visual_project", "project_id", "revision_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    revision_id = Column(
        UUID(as_uuid=True),
        ForeignKey("boq_v2_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    position = Column(Integer, nullable=False)
    layout = Column(String(16), nullable=False, server_default=text("'TWO_UP'"))
    title_th = Column(String(500), nullable=True)
    title_en = Column(String(500), nullable=True)
    description_th = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2QuotationVisualEntry(Base):
    __tablename__ = "boq_v2_quotation_visual_entries"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_boq_v2_quote_entry_position"),
        UniqueConstraint("page_id", "position", name="uq_boq_v2_quote_entry_position"),
        UniqueConstraint("page_id", "media_id", name="uq_boq_v2_quote_entry_media"),
        Index("ix_boq_v2_quote_entry_media", "media_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(
        UUID(as_uuid=True),
        ForeignKey("boq_v2_quotation_visual_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_id = Column(
        UUID(as_uuid=True),
        ForeignKey("boq_v2_quotation_media.id"),
        nullable=False,
    )
    scope_logical_id = Column(UUID(as_uuid=True), nullable=True)
    position = Column(Integer, nullable=False)
    caption_th = Column(Text, nullable=True)
    caption_en = Column(Text, nullable=True)


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
    catalog_item_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_catalog_items.id"), nullable=True
    )
    catalog_item_version = Column(Integer, nullable=True)
    source_logical_id = Column(UUID(as_uuid=True), nullable=True)
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
        CheckConstraint("lock_version > 0", name="ck_boq_v2_cost_plan_lock_version"),
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
    source_baseline_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "boq_v2_project_baselines.id",
            name="fk_boq_v2_cost_plan_source_baseline",
            use_alter=True,
        ),
        nullable=True,
    )
    predecessor_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_cost_plans.id"), nullable=True
    )
    version = Column(Integer, nullable=False)
    lock_version = Column(Integer, nullable=False, server_default=text("1"))
    status = Column(String(16), nullable=False, server_default=text("'WORKING'"))
    is_current = Column(Boolean, nullable=False, server_default=text("true"))
    completeness_state = Column(
        String(16), nullable=False, server_default=text("'INCOMPLETE'")
    )
    required_count = Column(Integer, nullable=False, server_default=text("0"))
    priced_count = Column(Integer, nullable=False, server_default=text("0"))
    original_estimated_cost = Column(MONEY, nullable=True)
    estimated_cost = Column(MONEY, nullable=True)
    agreed_cost = Column(MONEY, nullable=True)
    forecast_cost = Column(MONEY, nullable=True)
    calculation_version = Column(
        String(32), nullable=False, server_default=text("'boq-v2-calc-v1'")
    )
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(String, nullable=True)
    publish_reason = Column(Text, nullable=True)
    effective_at = Column(DateTime(timezone=True), nullable=True)
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
    source_component_id = Column(UUID(as_uuid=True), nullable=True)
    cost_state = Column(String(20), nullable=False, server_default=text("'UNKNOWN'"))
    original_unit_rate = Column(QUANTITY, nullable=True)
    original_total = Column(MONEY, nullable=True)
    unit_rate = Column(QUANTITY, nullable=True)
    total = Column(MONEY, nullable=True)
    agreed_unit_rate = Column(QUANTITY, nullable=True)
    agreed_total = Column(MONEY, nullable=True)
    selected_vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("boq_v2_vendors.id", name="fk_boq_v2_component_selected_vendor", use_alter=True),
        nullable=True,
    )
    selected_offer_line_id = Column(
        UUID(as_uuid=True),
        ForeignKey("boq_v2_vendor_offer_lines.id", name="fk_boq_v2_component_selected_offer", use_alter=True),
        nullable=True,
    )
    selection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("boq_v2_cost_selections.id", name="fk_boq_v2_component_selection", use_alter=True),
        nullable=True,
    )
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
            "audience IN ('CUSTOMER', 'INTERNAL', 'RFQ', 'VENDOR')",
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
            "audience <> 'INTERNAL' OR file_format = 'XLSX'",
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
    vendor_id = Column(UUID(as_uuid=True), nullable=True)
    audience_payload = Column(JSON, nullable=True)
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


class BOQV2Vendor(Base):
    __tablename__ = "boq_v2_vendors"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'ARCHIVED')", name="ck_boq_v2_vendor_status"
        ),
        Index("ix_boq_v2_vendor_project_name", "project_id", "display_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    display_name = Column(String(500), nullable=False)
    commercial_reference = Column(String(255), nullable=True)
    linked_party_reference = Column(String(255), nullable=True)
    tax_id = Column(String(64), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_detail = Column(String(1000), nullable=True)
    status = Column(String(16), nullable=False, server_default=text("'ACTIVE'"))
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2VendorOffer(Base):
    __tablename__ = "boq_v2_vendor_offers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'SUPERSEDED', 'WITHDRAWN')",
            name="ck_boq_v2_vendor_offer_status",
        ),
        CheckConstraint("currency = 'THB'", name="ck_boq_v2_vendor_offer_currency"),
        CheckConstraint(
            "tax_basis IN ('EXCLUSIVE_VAT', 'INCLUSIVE_VAT', 'NO_VAT', 'UNKNOWN')",
            name="ck_boq_v2_vendor_offer_tax_basis",
        ),
        CheckConstraint(
            "discount_type IN ('NONE', 'PERCENT', 'FIXED')",
            name="ck_boq_v2_vendor_offer_discount_type",
        ),
        CheckConstraint(
            "discount_value >= 0", name="ck_boq_v2_vendor_offer_discount_value"
        ),
        Index("ix_boq_v2_offer_project_date", "project_id", "quotation_date"),
        Index("ix_boq_v2_offer_vendor_date", "vendor_id", "quotation_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    vendor_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_vendors.id"), nullable=False
    )
    quotation_reference = Column(String(255), nullable=True)
    quotation_date = Column(Date, nullable=False)
    valid_until = Column(Date, nullable=True)
    currency = Column(String(8), nullable=False, server_default=text("'THB'"))
    tax_basis = Column(String(20), nullable=False)
    tax_rate = Column(QUANTITY, nullable=True)
    discount_type = Column(String(16), nullable=False, server_default=text("'NONE'"))
    discount_value = Column(QUANTITY, nullable=False, server_default=text("0"))
    included_charges = Column(Text, nullable=True)
    charges_amount = Column(MONEY, nullable=False, server_default=text("0"))
    evidence_storage_key = Column(String, nullable=True)
    evidence_filename = Column(String(255), nullable=True)
    evidence_content_type = Column(String(120), nullable=True)
    evidence_size_bytes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(16), nullable=False, server_default=text("'ACTIVE'"))
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2VendorOfferLine(Base):
    __tablename__ = "boq_v2_vendor_offer_lines"
    __table_args__ = (
        CheckConstraint(
            "component_type IN ('MATERIAL', 'LABOR')",
            name="ck_boq_v2_offer_line_component_type",
        ),
        CheckConstraint("offered_quantity > 0", name="ck_boq_v2_offer_line_quantity"),
        CheckConstraint("unit_rate >= 0", name="ck_boq_v2_offer_line_rate"),
        CheckConstraint(
            "coverage_state IN ('FULL', 'PARTIAL', 'EXCESS')",
            name="ck_boq_v2_offer_line_coverage",
        ),
        CheckConstraint(
            "comparison_state IN ('EQUIVALENT', 'UNIT_MISMATCH', 'SPEC_MISMATCH', "
            "'UNIT_AND_SPEC_MISMATCH')",
            name="ck_boq_v2_offer_line_comparison",
        ),
        UniqueConstraint(
            "offer_id", "scope_node_id", "component_type",
            name="uq_boq_v2_offer_line_component",
        ),
        Index(
            "ix_boq_v2_offer_line_component", "project_id", "scope_node_id", "component_type"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_vendor_offers.id"), nullable=False
    )
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    scope_node_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_scope_nodes.id"), nullable=False
    )
    source_component_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_cost_components.id"), nullable=False
    )
    component_type = Column(String(16), nullable=False)
    basis_version = Column(Integer, nullable=False)
    required_quantity = Column(QUANTITY, nullable=False)
    offered_quantity = Column(QUANTITY, nullable=False)
    unit = Column(String(120), nullable=True)
    specification = Column(Text, nullable=True)
    unit_rate = Column(QUANTITY, nullable=False)
    subtotal = Column(MONEY, nullable=False)
    discount_amount = Column(MONEY, nullable=False, server_default=text("0"))
    charges_amount = Column(MONEY, nullable=False, server_default=text("0"))
    original_total = Column(MONEY, nullable=False)
    normalized_unit_rate_ex_vat = Column(QUANTITY, nullable=True)
    normalized_total_ex_vat = Column(MONEY, nullable=True)
    coverage_state = Column(String(16), nullable=False)
    comparison_state = Column(String(32), nullable=False)
    basis_fingerprint = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2CostSelection(Base):
    __tablename__ = "boq_v2_cost_selections"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'STALE', 'REPLACED')",
            name="ck_boq_v2_cost_selection_status",
        ),
        Index(
            "uq_boq_v2_current_cost_selection",
            "project_id", "scope_node_id", "component_type",
            unique=True,
            postgresql_where=text("is_current"),
        ),
        Index("ix_boq_v2_selection_offer_line", "offer_line_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    revision_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_revisions.id"), nullable=False
    )
    scope_node_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_scope_nodes.id"), nullable=False
    )
    component_type = Column(String(16), nullable=False)
    offer_line_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_vendor_offer_lines.id"), nullable=False
    )
    selected_basis_version = Column(Integer, nullable=False)
    basis_fingerprint = Column(String(64), nullable=False)
    status = Column(String(16), nullable=False, server_default=text("'DRAFT'"))
    is_current = Column(Boolean, nullable=False, server_default=text("true"))
    warning_reason = Column(Text, nullable=True)
    warning_acknowledged = Column(Boolean, nullable=False, server_default=text("false"))
    selected_by = Column(String, nullable=False)
    selected_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmed_by = Column(String, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cost_plan_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_cost_plans.id"), nullable=True
    )


class BOQV2CatalogItem(Base):
    __tablename__ = "boq_v2_catalog_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'ARCHIVED')", name="ck_boq_v2_catalog_status"
        ),
        UniqueConstraint("code", name="uq_boq_v2_catalog_code"),
        Index("ix_boq_v2_catalog_search", "status", "category", "name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(255), nullable=False)
    name = Column(String(1000), nullable=False)
    specification = Column(Text, nullable=True)
    unit = Column(String(120), nullable=False)
    category = Column(String(500), nullable=True)
    tags = Column(JSON, nullable=False, server_default=text("'[]'::json"))
    status = Column(String(16), nullable=False, server_default=text("'ACTIVE'"))
    version = Column(Integer, nullable=False, server_default=text("1"))
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_by = Column(String, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2CatalogPriceVersion(Base):
    __tablename__ = "boq_v2_catalog_price_versions"
    __table_args__ = (
        CheckConstraint(
            "price_kind IN ('MATERIAL_SELL', 'LABOR_SELL', 'MATERIAL_COST', 'LABOR_COST')",
            name="ck_boq_v2_catalog_price_kind",
        ),
        CheckConstraint(
            "tax_basis IN ('EXCLUSIVE_VAT', 'INCLUSIVE_VAT', 'NO_VAT', 'UNKNOWN')",
            name="ck_boq_v2_catalog_price_tax_basis",
        ),
        CheckConstraint("amount >= 0", name="ck_boq_v2_catalog_price_amount"),
        UniqueConstraint(
            "catalog_item_id", "price_kind", "version",
            name="uq_boq_v2_catalog_price_version",
        ),
        Index(
            "uq_boq_v2_catalog_current_price", "catalog_item_id", "price_kind",
            unique=True, postgresql_where=text("is_current")
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_item_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_catalog_items.id"), nullable=False
    )
    price_kind = Column(String(24), nullable=False)
    version = Column(Integer, nullable=False)
    amount = Column(QUANTITY, nullable=False)
    tax_basis = Column(String(20), nullable=False)
    currency = Column(String(8), nullable=False, server_default=text("'THB'"))
    effective_date = Column(Date, nullable=False)
    source_observation_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_price_observations.id"), nullable=True
    )
    reason = Column(Text, nullable=False)
    is_current = Column(Boolean, nullable=False, server_default=text("true"))
    created_by = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BOQV2PriceObservation(Base):
    __tablename__ = "boq_v2_price_observations"
    __table_args__ = (
        CheckConstraint(
            "observation_kind IN ('OFFERED_SELL', 'ACCEPTED_SELL', 'ESTIMATED_COST', "
            "'VENDOR_OFFERED_COST', 'AGREED_VENDOR_COST')",
            name="ck_boq_v2_price_observation_kind",
        ),
        UniqueConstraint("event_key", name="uq_boq_v2_price_observation_event"),
        Index("ix_boq_v2_observation_catalog_date", "catalog_item_id", "observed_at"),
        Index("ix_boq_v2_observation_sample", "sample_key", "observation_kind"),
        Index("ix_boq_v2_observation_project_date", "project_id", "observed_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_key = Column(String(500), nullable=False)
    sample_key = Column(String(500), nullable=False)
    observation_kind = Column(String(32), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), nullable=True)
    revision_id = Column(UUID(as_uuid=True), nullable=True)
    scope_node_id = Column(UUID(as_uuid=True), nullable=True)
    logical_item_id = Column(UUID(as_uuid=True), nullable=True)
    component_type = Column(String(16), nullable=True)
    catalog_item_id = Column(
        UUID(as_uuid=True), ForeignKey("boq_v2_catalog_items.id"), nullable=True
    )
    source_event_type = Column(String(64), nullable=False)
    source_event_id = Column(UUID(as_uuid=True), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    quantity = Column(QUANTITY, nullable=True)
    unit = Column(String(120), nullable=True)
    specification = Column(Text, nullable=True)
    tax_basis = Column(String(20), nullable=True)
    currency = Column(String(8), nullable=False, server_default=text("'THB'"))
    unit_rate = Column(QUANTITY, nullable=False)
    total = Column(MONEY, nullable=False)
    vendor_id = Column(UUID(as_uuid=True), nullable=True)
    lineage_root_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
