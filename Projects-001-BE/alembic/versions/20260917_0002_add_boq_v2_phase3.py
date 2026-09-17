"""add BOQ V2 quotation lifecycle and export metadata

Revision ID: 20260917_0002
Revises: 20260915_0001
Create Date: 2026-09-17 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260917_0002"
down_revision: Union[str, Sequence[str], None] = "20260915_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "boq_v2_document_sequences",
        sa.Column("sequence_key", sa.String(length=32), nullable=False),
        sa.Column(
            "next_value",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "next_value > 0", name="ck_boq_v2_document_sequence_value"
        ),
        sa.PrimaryKeyConstraint("sequence_key"),
    )

    op.add_column(
        "boq_v2_documents",
        sa.Column("document_number", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "boq_v2_documents",
        sa.Column("base_baseline_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "boq_v2_documents",
        sa.Column("base_baseline_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "boq_v2_documents",
        sa.Column(
            "revision_counter",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE boq_v2_documents "
        "SET document_number = 'LEGACY-' || replace(id::text, '-', '')"
    )
    op.execute(
        "UPDATE boq_v2_documents AS d SET revision_counter = greatest(1, r.maximum) "
        "FROM (SELECT document_id, max(revision_number) AS maximum "
        "FROM boq_v2_revisions GROUP BY document_id) AS r "
        "WHERE r.document_id = d.id"
    )
    op.alter_column("boq_v2_documents", "document_number", nullable=False)
    op.create_unique_constraint(
        "uq_boq_v2_document_number", "boq_v2_documents", ["document_number"]
    )
    op.create_check_constraint(
        "ck_boq_v2_document_revision_counter",
        "boq_v2_documents",
        "revision_counter > 0",
    )
    op.create_check_constraint(
        "ck_boq_v2_document_change_order_baseline",
        "boq_v2_documents",
        "(document_kind = 'CHANGE_ORDER' AND base_baseline_id IS NOT NULL "
        "AND base_baseline_version IS NOT NULL) OR "
        "(document_kind <> 'CHANGE_ORDER' AND base_baseline_id IS NULL "
        "AND base_baseline_version IS NULL)",
    )
    op.create_foreign_key(
        "fk_boq_v2_documents_base_baseline",
        "boq_v2_documents",
        "boq_v2_project_baselines",
        ["base_baseline_id"],
        ["id"],
    )

    revision_columns = (
        sa.Column("base_baseline_id", sa.UUID(), nullable=True),
        sa.Column("base_baseline_version", sa.Integer(), nullable=True),
        sa.Column("quotation_title", sa.String(length=500), nullable=True),
        sa.Column("customer_name", sa.String(length=500), nullable=True),
        sa.Column("customer_address", sa.Text(), nullable=True),
        sa.Column("customer_tax_id", sa.String(length=64), nullable=True),
        sa.Column("customer_contact", sa.String(length=255), nullable=True),
        sa.Column("quotation_date", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'THB'"),
            nullable=False,
        ),
        sa.Column(
            "vat_rate",
            sa.Numeric(20, 4),
            server_default=sa.text("7"),
            nullable=False,
        ),
        sa.Column(
            "discount_type",
            sa.String(length=16),
            server_default=sa.text("'NONE'"),
            nullable=False,
        ),
        sa.Column(
            "discount_value",
            sa.Numeric(20, 4),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(20, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "discount_amount",
            sa.Numeric(20, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "vat_amount",
            sa.Numeric(20, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "grand_total",
            sa.Numeric(20, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "payment_schedule",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "commercial_terms",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "document_pages",
            sa.JSON(),
            server_default=sa.text(
                "'[\"BOQ\", \"PAYMENT_TERMS\", \"COMMERCIAL_TERMS\"]'::json"
            ),
            nullable=False,
        ),
        sa.Column("issued_by", sa.String(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in revision_columns:
        op.add_column("boq_v2_revisions", column)
    op.create_foreign_key(
        "fk_boq_v2_revisions_base_baseline",
        "boq_v2_revisions",
        "boq_v2_project_baselines",
        ["base_baseline_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_boq_v2_revision_baseline_identity",
        "boq_v2_revisions",
        "(base_baseline_id IS NULL AND base_baseline_version IS NULL) OR "
        "(base_baseline_id IS NOT NULL AND base_baseline_version IS NOT NULL)",
    )
    op.execute(
        "UPDATE boq_v2_revisions SET subtotal = coalesce(net_sell_ex_vat, 0), "
        "grand_total = coalesce(net_sell_ex_vat, 0)"
    )
    op.create_check_constraint(
        "ck_boq_v2_revision_currency", "boq_v2_revisions", "currency = 'THB'"
    )
    op.create_check_constraint(
        "ck_boq_v2_revision_vat_rate",
        "boq_v2_revisions",
        "vat_rate >= 0 AND vat_rate <= 100",
    )
    op.create_check_constraint(
        "ck_boq_v2_revision_discount_type",
        "boq_v2_revisions",
        "discount_type IN ('NONE', 'PERCENT', 'FIXED')",
    )
    op.create_check_constraint(
        "ck_boq_v2_revision_document_totals",
        "boq_v2_revisions",
        "discount_value >= 0 AND discount_amount >= 0 AND subtotal >= 0 "
        "AND vat_amount >= 0 AND grand_total >= 0",
    )

    op.create_table(
        "boq_v2_revision_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=16), nullable=False),
        sa.Column("calculation_version", sa.String(length=32), nullable=False),
        sa.Column("customer_payload", sa.JSON(), nullable=False),
        sa.Column("internal_payload", sa.JSON(), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purpose IN ('PREVIEW', 'ISSUE')", name="ck_boq_v2_snapshot_purpose"
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('DRAFT', 'ISSUED')",
            name="ck_boq_v2_snapshot_lifecycle_status",
        ),
        sa.CheckConstraint(
            "source_version > 0", name="ck_boq_v2_snapshot_version"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["boq_v2_documents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "revision_id",
            "source_version",
            "purpose",
            name="uq_boq_v2_snapshot_revision_version_purpose",
        ),
    )
    op.create_index(
        "ix_boq_v2_snapshot_project_created",
        "boq_v2_revision_snapshots",
        ["project_id", "created_at"],
        unique=False,
    )

    op.add_column(
        "boq_v2_project_baselines",
        sa.Column("main_snapshot_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_boq_v2_baseline_main_snapshot",
        "boq_v2_project_baselines",
        "boq_v2_revision_snapshots",
        ["main_snapshot_id"],
        ["id"],
    )

    op.add_column(
        "boq_v2_baseline_change_orders",
        sa.Column("document_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "boq_v2_baseline_change_orders",
        sa.Column("snapshot_id", sa.UUID(), nullable=True),
    )
    op.execute(
        "UPDATE boq_v2_baseline_change_orders AS m SET document_id = r.document_id "
        "FROM boq_v2_revisions AS r WHERE r.id = m.revision_id"
    )
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM boq_v2_baseline_change_orders "
        "WHERE snapshot_id IS NULL) THEN RAISE EXCEPTION "
        "'Phase 3 migration requires empty pre-Phase-3 baseline membership'; "
        "END IF; END $$"
    )
    op.alter_column("boq_v2_baseline_change_orders", "document_id", nullable=False)
    op.alter_column("boq_v2_baseline_change_orders", "snapshot_id", nullable=False)
    op.create_foreign_key(
        "fk_boq_v2_baseline_co_document",
        "boq_v2_baseline_change_orders",
        "boq_v2_documents",
        ["document_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_boq_v2_baseline_co_snapshot",
        "boq_v2_baseline_change_orders",
        "boq_v2_revision_snapshots",
        ["snapshot_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_boq_v2_baseline_co_document",
        "boq_v2_baseline_change_orders",
        ["baseline_id", "document_id"],
    )

    op.create_table(
        "boq_v2_change_order_deductions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("base_baseline_id", sa.UUID(), nullable=False),
        sa.Column("base_baseline_version", sa.Integer(), nullable=False),
        sa.Column("target_revision_id", sa.UUID(), nullable=False),
        sa.Column("target_logical_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("unit_rate", sa.Numeric(20, 4), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False),
        sa.CheckConstraint(
            "amount >= 0", name="ck_boq_v2_co_deduction_amount"
        ),
        sa.CheckConstraint(
            "quantity > 0", name="ck_boq_v2_co_deduction_quantity"
        ),
        sa.ForeignKeyConstraint(["base_baseline_id"], ["boq_v2_project_baselines.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["boq_v2_documents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"]),
        sa.ForeignKeyConstraint(["target_revision_id"], ["boq_v2_revisions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "revision_id",
            "target_logical_id",
            name="uq_boq_v2_co_deduction_target",
        ),
    )
    op.create_index(
        "ix_boq_v2_co_deduction_project_target",
        "boq_v2_change_order_deductions",
        ["project_id", "target_logical_id"],
        unique=False,
    )

    op.create_table(
        "boq_v2_acceptances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("agreed_date", sa.Date(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("evidence_reference", sa.String(length=1000), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["boq_v2_documents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["boq_v2_revision_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id", name="uq_boq_v2_acceptance_revision"),
    )
    op.create_index(
        "ix_boq_v2_acceptance_project_recorded",
        "boq_v2_acceptances",
        ["project_id", "recorded_at"],
        unique=False,
    )

    op.create_table(
        "boq_v2_export_artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("calculation_version", sa.String(length=32), nullable=False),
        sa.Column("audience", sa.String(length=16), nullable=False),
        sa.Column("file_format", sa.String(length=8), nullable=False),
        sa.Column("cost_plan_version", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "audience IN ('CUSTOMER', 'INTERNAL')",
            name="ck_boq_v2_export_audience",
        ),
        sa.CheckConstraint(
            "file_format IN ('XLSX', 'PDF')", name="ck_boq_v2_export_format"
        ),
        sa.CheckConstraint(
            "audience = 'CUSTOMER' OR file_format = 'XLSX'",
            name="ck_boq_v2_internal_export_xlsx_only",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'READY', 'FAILED')",
            name="ck_boq_v2_export_status",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["boq_v2_documents.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["boq_v2_revision_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_boq_v2_export_project_created",
        "boq_v2_export_artifacts",
        ["project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_boq_v2_export_revision_created",
        "boq_v2_export_artifacts",
        ["revision_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    raise RuntimeError("Destructive BOQ V2 downgrade is intentionally unsupported")
