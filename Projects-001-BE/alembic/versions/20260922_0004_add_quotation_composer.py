"""add quotation document composer and visual media

Revision ID: 20260922_0004
Revises: 20260917_0003
Create Date: 2026-09-22 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260922_0004"
down_revision: Union[str, Sequence[str], None] = "20260917_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "boq_v2_quotation_sections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("section_type", sa.String(length=24), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title_th", sa.String(length=500), nullable=True),
        sa.Column("title_en", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "section_type IN ('SUMMARY', 'DETAILED_BOQ', 'VISUAL', 'PAYMENT_TERMS', 'TERMS', 'ACCEPTANCE')",
            name="ck_boq_v2_quote_section_type",
        ),
        sa.CheckConstraint("position >= 0", name="ck_boq_v2_quote_section_position"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id", "section_type", name="uq_boq_v2_quote_section_type"),
        sa.UniqueConstraint("revision_id", "position", name="uq_boq_v2_quote_section_position"),
    )
    op.create_index(
        "ix_boq_v2_quote_section_project",
        "boq_v2_quotation_sections",
        ["project_id", "revision_id"],
    )

    op.create_table(
        "boq_v2_quotation_media",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("origin_type", sa.String(length=20), nullable=False),
        sa.Column("origin_id", sa.String(length=255), nullable=True),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("origin_type IN ('UPLOAD', 'DAILY_REPORT', 'INSPECTION')", name="ck_boq_v2_quote_media_origin"),
        sa.CheckConstraint("size_bytes > 0", name="ck_boq_v2_quote_media_size"),
        sa.CheckConstraint("width > 0 AND height > 0", name="ck_boq_v2_quote_media_dimensions"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_boq_v2_quote_media_project", "boq_v2_quotation_media", ["project_id", "created_at"])
    op.create_index("ix_boq_v2_quote_media_revision", "boq_v2_quotation_media", ["revision_id", "created_at"])

    op.create_table(
        "boq_v2_quotation_visual_pages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("revision_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("layout", sa.String(length=16), server_default=sa.text("'TWO_UP'"), nullable=False),
        sa.Column("title_th", sa.String(length=500), nullable=True),
        sa.Column("title_en", sa.String(length=500), nullable=True),
        sa.Column("description_th", sa.Text(), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("layout IN ('SINGLE', 'TWO_UP', 'FOUR_UP')", name="ck_boq_v2_quote_visual_layout"),
        sa.CheckConstraint("position >= 0", name="ck_boq_v2_quote_visual_position"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["revision_id"], ["boq_v2_revisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id", "position", name="uq_boq_v2_quote_visual_position"),
    )
    op.create_index("ix_boq_v2_quote_visual_project", "boq_v2_quotation_visual_pages", ["project_id", "revision_id"])

    op.create_table(
        "boq_v2_quotation_visual_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("page_id", sa.UUID(), nullable=False),
        sa.Column("media_id", sa.UUID(), nullable=False),
        sa.Column("scope_logical_id", sa.UUID(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("caption_th", sa.Text(), nullable=True),
        sa.Column("caption_en", sa.Text(), nullable=True),
        sa.CheckConstraint("position >= 0", name="ck_boq_v2_quote_entry_position"),
        sa.ForeignKeyConstraint(["media_id"], ["boq_v2_quotation_media.id"]),
        sa.ForeignKeyConstraint(["page_id"], ["boq_v2_quotation_visual_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id", "media_id", name="uq_boq_v2_quote_entry_media"),
        sa.UniqueConstraint("page_id", "position", name="uq_boq_v2_quote_entry_position"),
    )
    op.create_index("ix_boq_v2_quote_entry_media", "boq_v2_quotation_visual_entries", ["media_id"])


def downgrade() -> None:
    op.drop_index("ix_boq_v2_quote_entry_media", table_name="boq_v2_quotation_visual_entries")
    op.drop_table("boq_v2_quotation_visual_entries")
    op.drop_index("ix_boq_v2_quote_visual_project", table_name="boq_v2_quotation_visual_pages")
    op.drop_table("boq_v2_quotation_visual_pages")
    op.drop_index("ix_boq_v2_quote_media_revision", table_name="boq_v2_quotation_media")
    op.drop_index("ix_boq_v2_quote_media_project", table_name="boq_v2_quotation_media")
    op.drop_table("boq_v2_quotation_media")
    op.drop_index("ix_boq_v2_quote_section_project", table_name="boq_v2_quotation_sections")
    op.drop_table("boq_v2_quotation_sections")
