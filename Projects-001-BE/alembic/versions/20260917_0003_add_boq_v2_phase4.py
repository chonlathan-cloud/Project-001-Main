"""add BOQ V2 vendor cost and price database

Revision ID: 20260917_0003
Revises: 20260917_0002
Create Date: 2026-09-17 14:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260917_0003"
down_revision: Union[str, Sequence[str], None] = "20260917_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_boq_v2_export_audience", "boq_v2_export_artifacts", type_="check")
    op.drop_constraint("ck_boq_v2_internal_export_xlsx_only", "boq_v2_export_artifacts", type_="check")
    op.create_check_constraint(
        "ck_boq_v2_export_audience",
        "boq_v2_export_artifacts",
        "audience IN ('CUSTOMER', 'INTERNAL', 'RFQ', 'VENDOR')",
    )
    op.create_check_constraint(
        "ck_boq_v2_internal_export_xlsx_only",
        "boq_v2_export_artifacts",
        "audience <> 'INTERNAL' OR file_format = 'XLSX'",
    )
    op.add_column("boq_v2_export_artifacts", sa.Column("vendor_id", sa.UUID(), nullable=True))
    op.add_column("boq_v2_export_artifacts", sa.Column("audience_payload", sa.JSON(), nullable=True))
    op.create_table(
        "boq_v2_vendors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.String(length=500), nullable=False),
        sa.Column("commercial_reference", sa.String(length=255), nullable=True),
        sa.Column("linked_party_reference", sa.String(length=255), nullable=True),
        sa.Column("tax_id", sa.String(length=64), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_detail", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name="ck_boq_v2_vendor_status"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_boq_v2_vendor_project_name", "boq_v2_vendors", ["project_id", "display_name"])

    op.create_table(
        "boq_v2_catalog_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=1000), nullable=False),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=500), nullable=True),
        sa.Column("tags", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'ARCHIVED')", name="ck_boq_v2_catalog_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_boq_v2_catalog_code"),
    )
    op.create_index("ix_boq_v2_catalog_search", "boq_v2_catalog_items", ["status", "category", "name"])

    op.add_column("boq_v2_scope_nodes", sa.Column("catalog_item_id", sa.UUID(), nullable=True))
    op.add_column("boq_v2_scope_nodes", sa.Column("catalog_item_version", sa.Integer(), nullable=True))
    op.add_column("boq_v2_scope_nodes", sa.Column("source_logical_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_boq_v2_scope_catalog_item",
        "boq_v2_scope_nodes",
        "boq_v2_catalog_items",
        ["catalog_item_id"],
        ["id"],
    )

    op.add_column("boq_v2_cost_plans", sa.Column("source_baseline_id", sa.UUID(), nullable=True))
    op.add_column("boq_v2_cost_plans", sa.Column("predecessor_plan_id", sa.UUID(), nullable=True))
    op.add_column("boq_v2_cost_plans", sa.Column("lock_version", sa.Integer(), server_default=sa.text("1"), nullable=False))
    op.add_column("boq_v2_cost_plans", sa.Column("estimated_cost", sa.Numeric(20, 2), nullable=True))
    op.add_column("boq_v2_cost_plans", sa.Column("published_by", sa.String(), nullable=True))
    op.add_column("boq_v2_cost_plans", sa.Column("publish_reason", sa.Text(), nullable=True))
    op.add_column("boq_v2_cost_plans", sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("ck_boq_v2_cost_plan_lock_version", "boq_v2_cost_plans", "lock_version > 0")
    op.create_foreign_key(
        "fk_boq_v2_cost_plan_source_baseline",
        "boq_v2_cost_plans",
        "boq_v2_project_baselines",
        ["source_baseline_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_boq_v2_cost_plan_predecessor",
        "boq_v2_cost_plans",
        "boq_v2_cost_plans",
        ["predecessor_plan_id"],
        ["id"],
    )

    for name, column in (
        ("source_component_id", sa.Column("source_component_id", sa.UUID(), nullable=True)),
        ("original_unit_rate", sa.Column("original_unit_rate", sa.Numeric(20, 4), nullable=True)),
        ("original_total", sa.Column("original_total", sa.Numeric(20, 2), nullable=True)),
        ("agreed_unit_rate", sa.Column("agreed_unit_rate", sa.Numeric(20, 4), nullable=True)),
        ("agreed_total", sa.Column("agreed_total", sa.Numeric(20, 2), nullable=True)),
        ("selected_vendor_id", sa.Column("selected_vendor_id", sa.UUID(), nullable=True)),
        ("selected_offer_line_id", sa.Column("selected_offer_line_id", sa.UUID(), nullable=True)),
        ("selection_id", sa.Column("selection_id", sa.UUID(), nullable=True)),
    ):
        del name
        op.add_column("boq_v2_cost_components", column)

    op.create_table(
        "boq_v2_vendor_offers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("vendor_id", sa.UUID(), nullable=False),
        sa.Column("quotation_reference", sa.String(length=255), nullable=True),
        sa.Column("quotation_date", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=8), server_default=sa.text("'THB'"), nullable=False),
        sa.Column("tax_basis", sa.String(length=20), nullable=False),
        sa.Column("tax_rate", sa.Numeric(20, 4), nullable=True),
        sa.Column("discount_type", sa.String(length=16), server_default=sa.text("'NONE'"), nullable=False),
        sa.Column("discount_value", sa.Numeric(20, 4), server_default=sa.text("0"), nullable=False),
        sa.Column("included_charges", sa.Text(), nullable=True),
        sa.Column("charges_amount", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("evidence_storage_key", sa.String(), nullable=True),
        sa.Column("evidence_filename", sa.String(length=255), nullable=True),
        sa.Column("evidence_content_type", sa.String(length=120), nullable=True),
        sa.Column("evidence_size_bytes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'SUPERSEDED', 'WITHDRAWN')", name="ck_boq_v2_vendor_offer_status"),
        sa.CheckConstraint("currency = 'THB'", name="ck_boq_v2_vendor_offer_currency"),
        sa.CheckConstraint("tax_basis IN ('EXCLUSIVE_VAT', 'INCLUSIVE_VAT', 'NO_VAT', 'UNKNOWN')", name="ck_boq_v2_vendor_offer_tax_basis"),
        sa.CheckConstraint("discount_type IN ('NONE', 'PERCENT', 'FIXED')", name="ck_boq_v2_vendor_offer_discount_type"),
        sa.CheckConstraint("discount_value >= 0", name="ck_boq_v2_vendor_offer_discount_value"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["boq_v2_vendors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_boq_v2_offer_project_date", "boq_v2_vendor_offers", ["project_id", "quotation_date"])
    op.create_index("ix_boq_v2_offer_vendor_date", "boq_v2_vendor_offers", ["vendor_id", "quotation_date"])

    op.create_table(
        "boq_v2_vendor_offer_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("offer_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("scope_node_id", sa.UUID(), nullable=False),
        sa.Column("source_component_id", sa.UUID(), nullable=False),
        sa.Column("component_type", sa.String(length=16), nullable=False),
        sa.Column("basis_version", sa.Integer(), nullable=False),
        sa.Column("required_quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("offered_quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("unit", sa.String(length=120), nullable=True),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("unit_rate", sa.Numeric(20, 4), nullable=False),
        sa.Column("subtotal", sa.Numeric(20, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("charges_amount", sa.Numeric(20, 2), server_default=sa.text("0"), nullable=False),
        sa.Column("original_total", sa.Numeric(20, 2), nullable=False),
        sa.Column("normalized_unit_rate_ex_vat", sa.Numeric(20, 4), nullable=True),
        sa.Column("normalized_total_ex_vat", sa.Numeric(20, 2), nullable=True),
        sa.Column("coverage_state", sa.String(length=16), nullable=False),
        sa.Column("comparison_state", sa.String(length=32), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("component_type IN ('MATERIAL', 'LABOR')", name="ck_boq_v2_offer_line_component_type"),
        sa.CheckConstraint("offered_quantity > 0", name="ck_boq_v2_offer_line_quantity"),
        sa.CheckConstraint("unit_rate >= 0", name="ck_boq_v2_offer_line_rate"),
        sa.CheckConstraint("coverage_state IN ('FULL', 'PARTIAL', 'EXCESS')", name="ck_boq_v2_offer_line_coverage"),
        sa.CheckConstraint("comparison_state IN ('EQUIVALENT', 'UNIT_MISMATCH', 'SPEC_MISMATCH', 'UNIT_AND_SPEC_MISMATCH')", name="ck_boq_v2_offer_line_comparison"),
        sa.ForeignKeyConstraint(["offer_id"], ["boq_v2_vendor_offers.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"]),
        sa.ForeignKeyConstraint(["scope_node_id"], ["boq_v2_scope_nodes.id"]),
        sa.ForeignKeyConstraint(["source_component_id"], ["boq_v2_cost_components.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offer_id", "scope_node_id", "component_type", name="uq_boq_v2_offer_line_component"),
    )
    op.create_index("ix_boq_v2_offer_line_component", "boq_v2_vendor_offer_lines", ["project_id", "scope_node_id", "component_type"])

    op.create_table(
        "boq_v2_cost_selections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("scope_node_id", sa.UUID(), nullable=False),
        sa.Column("component_type", sa.String(length=16), nullable=False),
        sa.Column("offer_line_id", sa.UUID(), nullable=False),
        sa.Column("selected_basis_version", sa.Integer(), nullable=False),
        sa.Column("basis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("warning_reason", sa.Text(), nullable=True),
        sa.Column("warning_acknowledged", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("selected_by", sa.String(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("confirmed_by", sa.String(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_plan_id", sa.UUID(), nullable=True),
        sa.CheckConstraint("status IN ('DRAFT', 'CONFIRMED', 'STALE', 'REPLACED')", name="ck_boq_v2_cost_selection_status"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"]),
        sa.ForeignKeyConstraint(["scope_node_id"], ["boq_v2_scope_nodes.id"]),
        sa.ForeignKeyConstraint(["offer_line_id"], ["boq_v2_vendor_offer_lines.id"]),
        sa.ForeignKeyConstraint(["cost_plan_id"], ["boq_v2_cost_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_boq_v2_selection_offer_line", "boq_v2_cost_selections", ["offer_line_id"])
    op.create_index(
        "uq_boq_v2_current_cost_selection",
        "boq_v2_cost_selections",
        ["project_id", "scope_node_id", "component_type"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    op.create_table(
        "boq_v2_price_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_key", sa.String(length=500), nullable=False),
        sa.Column("sample_key", sa.String(length=500), nullable=False),
        sa.Column("observation_kind", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("revision_id", sa.UUID(), nullable=True),
        sa.Column("scope_node_id", sa.UUID(), nullable=True),
        sa.Column("logical_item_id", sa.UUID(), nullable=True),
        sa.Column("component_type", sa.String(length=16), nullable=True),
        sa.Column("catalog_item_id", sa.UUID(), nullable=True),
        sa.Column("source_event_type", sa.String(length=64), nullable=False),
        sa.Column("source_event_id", sa.UUID(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit", sa.String(length=120), nullable=True),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("tax_basis", sa.String(length=20), nullable=True),
        sa.Column("currency", sa.String(length=8), server_default=sa.text("'THB'"), nullable=False),
        sa.Column("unit_rate", sa.Numeric(20, 4), nullable=False),
        sa.Column("total", sa.Numeric(20, 2), nullable=False),
        sa.Column("vendor_id", sa.UUID(), nullable=True),
        sa.Column("lineage_root_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("observation_kind IN ('OFFERED_SELL', 'ACCEPTED_SELL', 'ESTIMATED_COST', 'VENDOR_OFFERED_COST', 'AGREED_VENDOR_COST')", name="ck_boq_v2_price_observation_kind"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["boq_v2_catalog_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key", name="uq_boq_v2_price_observation_event"),
    )
    op.create_index("ix_boq_v2_observation_catalog_date", "boq_v2_price_observations", ["catalog_item_id", "observed_at"])
    op.create_index("ix_boq_v2_observation_sample", "boq_v2_price_observations", ["sample_key", "observation_kind"])
    op.create_index("ix_boq_v2_observation_project_date", "boq_v2_price_observations", ["project_id", "observed_at"])

    op.create_table(
        "boq_v2_catalog_price_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("catalog_item_id", sa.UUID(), nullable=False),
        sa.Column("price_kind", sa.String(length=24), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("tax_basis", sa.String(length=20), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default=sa.text("'THB'"), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("source_observation_id", sa.UUID(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("price_kind IN ('MATERIAL_SELL', 'LABOR_SELL', 'MATERIAL_COST', 'LABOR_COST')", name="ck_boq_v2_catalog_price_kind"),
        sa.CheckConstraint("tax_basis IN ('EXCLUSIVE_VAT', 'INCLUSIVE_VAT', 'NO_VAT', 'UNKNOWN')", name="ck_boq_v2_catalog_price_tax_basis"),
        sa.CheckConstraint("amount >= 0", name="ck_boq_v2_catalog_price_amount"),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["boq_v2_catalog_items.id"]),
        sa.ForeignKeyConstraint(["source_observation_id"], ["boq_v2_price_observations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("catalog_item_id", "price_kind", "version", name="uq_boq_v2_catalog_price_version"),
    )
    op.create_index(
        "uq_boq_v2_catalog_current_price",
        "boq_v2_catalog_price_versions",
        ["catalog_item_id", "price_kind"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )

    op.create_foreign_key("fk_boq_v2_component_selected_vendor", "boq_v2_cost_components", "boq_v2_vendors", ["selected_vendor_id"], ["id"])
    op.create_foreign_key("fk_boq_v2_component_selected_offer", "boq_v2_cost_components", "boq_v2_vendor_offer_lines", ["selected_offer_line_id"], ["id"])
    op.create_foreign_key("fk_boq_v2_component_selection", "boq_v2_cost_components", "boq_v2_cost_selections", ["selection_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_boq_v2_component_selection", "boq_v2_cost_components", type_="foreignkey")
    op.drop_constraint("fk_boq_v2_component_selected_offer", "boq_v2_cost_components", type_="foreignkey")
    op.drop_constraint("fk_boq_v2_component_selected_vendor", "boq_v2_cost_components", type_="foreignkey")
    op.drop_index("uq_boq_v2_catalog_current_price", table_name="boq_v2_catalog_price_versions")
    op.drop_table("boq_v2_catalog_price_versions")
    op.drop_index("ix_boq_v2_observation_project_date", table_name="boq_v2_price_observations")
    op.drop_index("ix_boq_v2_observation_sample", table_name="boq_v2_price_observations")
    op.drop_index("ix_boq_v2_observation_catalog_date", table_name="boq_v2_price_observations")
    op.drop_table("boq_v2_price_observations")
    op.drop_index("uq_boq_v2_current_cost_selection", table_name="boq_v2_cost_selections")
    op.drop_index("ix_boq_v2_selection_offer_line", table_name="boq_v2_cost_selections")
    op.drop_table("boq_v2_cost_selections")
    op.drop_index("ix_boq_v2_offer_line_component", table_name="boq_v2_vendor_offer_lines")
    op.drop_table("boq_v2_vendor_offer_lines")
    op.drop_index("ix_boq_v2_offer_vendor_date", table_name="boq_v2_vendor_offers")
    op.drop_index("ix_boq_v2_offer_project_date", table_name="boq_v2_vendor_offers")
    op.drop_table("boq_v2_vendor_offers")
    for column in (
        "selection_id", "selected_offer_line_id", "selected_vendor_id", "agreed_total",
        "agreed_unit_rate", "original_total", "original_unit_rate", "source_component_id",
    ):
        op.drop_column("boq_v2_cost_components", column)
    op.drop_constraint("fk_boq_v2_cost_plan_predecessor", "boq_v2_cost_plans", type_="foreignkey")
    op.drop_constraint("fk_boq_v2_cost_plan_source_baseline", "boq_v2_cost_plans", type_="foreignkey")
    op.drop_constraint("ck_boq_v2_cost_plan_lock_version", "boq_v2_cost_plans", type_="check")
    for column in (
        "effective_at", "publish_reason", "published_by", "estimated_cost", "lock_version",
        "predecessor_plan_id", "source_baseline_id",
    ):
        op.drop_column("boq_v2_cost_plans", column)
    op.drop_constraint("fk_boq_v2_scope_catalog_item", "boq_v2_scope_nodes", type_="foreignkey")
    op.drop_column("boq_v2_scope_nodes", "source_logical_id")
    op.drop_column("boq_v2_scope_nodes", "catalog_item_version")
    op.drop_column("boq_v2_scope_nodes", "catalog_item_id")
    op.drop_index("ix_boq_v2_catalog_search", table_name="boq_v2_catalog_items")
    op.drop_table("boq_v2_catalog_items")
    op.drop_index("ix_boq_v2_vendor_project_name", table_name="boq_v2_vendors")
    op.drop_table("boq_v2_vendors")
    op.drop_column("boq_v2_export_artifacts", "audience_payload")
    op.drop_column("boq_v2_export_artifacts", "vendor_id")
    op.drop_constraint("ck_boq_v2_internal_export_xlsx_only", "boq_v2_export_artifacts", type_="check")
    op.drop_constraint("ck_boq_v2_export_audience", "boq_v2_export_artifacts", type_="check")
    op.create_check_constraint(
        "ck_boq_v2_export_audience",
        "boq_v2_export_artifacts",
        "audience IN ('CUSTOMER', 'INTERNAL')",
    )
    op.create_check_constraint(
        "ck_boq_v2_internal_export_xlsx_only",
        "boq_v2_export_artifacts",
        "audience = 'CUSTOMER' OR file_format = 'XLSX'",
    )
