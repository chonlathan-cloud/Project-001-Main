"""Quotation document composition persistence shared by preview and export paths."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boq_v2 import (
    BOQV2QuotationMedia,
    BOQV2QuotationSection,
    BOQV2QuotationVisualEntry,
    BOQV2QuotationVisualPage,
    BOQV2Revision,
    BOQV2ScopeNode,
)
from app.schemas.boq_v2_schema import (
    BOQV2QuotationDraft,
    BOQV2QuotationMediaResponse,
    BOQV2QuotationSectionDraft,
    BOQV2QuotationSectionResponse,
    BOQV2QuotationVisualPageDraft,
    BOQV2QuotationVisualEntryResponse,
    BOQV2QuotationVisualPageResponse,
)
from app.services.boq_domain_service import BOQDomainError


DOCUMENT_SCHEMA_VERSION = "boq-v2-document-snapshot-v2"
SECTION_ORDER = (
    "SUMMARY",
    "DETAILED_BOQ",
    "VISUAL",
    "PAYMENT_TERMS",
    "TERMS",
    "ACCEPTANCE",
)
SECTION_TITLES = {
    "SUMMARY": ("สรุปใบเสนอราคา", "Quotation Summary"),
    "DETAILED_BOQ": ("รายละเอียด BOQ", "Detailed BOQ"),
    "VISUAL": ("รูปภาพและรายละเอียดงาน", "Visual / Work Detail"),
    "PAYMENT_TERMS": ("เงื่อนไขการชำระเงิน", "Payment Terms"),
    "TERMS": ("ข้อกำหนดและเงื่อนไข", "Terms & Conditions"),
    "ACCEPTANCE": ("การยอมรับใบเสนอราคา", "Acceptance"),
}


def _timestamp(value: datetime | None) -> str:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(UTC).isoformat().replace("+00:00", "Z")


def default_sections(
    document_pages: list[str] | None = None,
) -> list[BOQV2QuotationSectionDraft]:
    pages = set(document_pages or ["BOQ", "PAYMENT_TERMS", "COMMERCIAL_TERMS"])
    enabled = {
        "SUMMARY": True,
        "DETAILED_BOQ": True,
        "VISUAL": False,
        "PAYMENT_TERMS": "PAYMENT_TERMS" in pages,
        "TERMS": "COMMERCIAL_TERMS" in pages,
        "ACCEPTANCE": False,
    }
    return [
        BOQV2QuotationSectionDraft(
            section_type=section_type,
            enabled=enabled[section_type],
            position=position,
            title_th=SECTION_TITLES[section_type][0],
            title_en=SECTION_TITLES[section_type][1],
        )
        for position, section_type in enumerate(SECTION_ORDER)
    ]


def legacy_pages_from_sections(sections: list[BOQV2QuotationSectionDraft]) -> list[str]:
    enabled = {item.section_type for item in sections if item.enabled}
    pages = ["BOQ"]
    if "PAYMENT_TERMS" in enabled:
        pages.append("PAYMENT_TERMS")
    if "TERMS" in enabled:
        pages.append("COMMERCIAL_TERMS")
    return pages


async def load_composition(
    db: AsyncSession,
    *,
    revision_id: UUID,
    legacy_document_pages: list[str] | None,
) -> tuple[
    list[BOQV2QuotationSectionResponse],
    list[BOQV2QuotationVisualPageResponse],
    list[BOQV2QuotationMediaResponse],
]:
    sections = list(
        (
            await db.execute(
                select(BOQV2QuotationSection)
                .where(BOQV2QuotationSection.revision_id == revision_id)
                .order_by(BOQV2QuotationSection.position)
            )
        ).scalars()
    )
    if sections:
        section_payload = [
            BOQV2QuotationSectionResponse(
                id=item.id,
                section_type=item.section_type,
                enabled=item.enabled,
                position=item.position,
                title_th=item.title_th,
                title_en=item.title_en,
            )
            for item in sections
        ]
    else:
        section_payload = [
            BOQV2QuotationSectionResponse(id=None, **item.model_dump())
            for item in default_sections(legacy_document_pages)
        ]

    pages = list(
        (
            await db.execute(
                select(BOQV2QuotationVisualPage)
                .where(BOQV2QuotationVisualPage.revision_id == revision_id)
                .order_by(BOQV2QuotationVisualPage.position)
            )
        ).scalars()
    )
    page_ids = [item.id for item in pages]
    entries = []
    if page_ids:
        entries = list(
            (
                await db.execute(
                    select(BOQV2QuotationVisualEntry)
                    .where(BOQV2QuotationVisualEntry.page_id.in_(page_ids))
                    .order_by(
                        BOQV2QuotationVisualEntry.page_id,
                        BOQV2QuotationVisualEntry.position,
                    )
                )
            ).scalars()
        )
    entries_by_page: dict[UUID, list[BOQV2QuotationVisualEntry]] = {}
    for entry in entries:
        entries_by_page.setdefault(entry.page_id, []).append(entry)
    page_payload = [
        BOQV2QuotationVisualPageResponse(
            id=page.id,
            position=page.position,
            layout=page.layout,
            title_th=page.title_th,
            title_en=page.title_en,
            description_th=page.description_th,
            description_en=page.description_en,
            entries=[
                BOQV2QuotationVisualEntryResponse(
                    id=entry.id,
                    media_id=entry.media_id,
                    position=entry.position,
                    scope_logical_id=entry.scope_logical_id,
                    caption_th=entry.caption_th,
                    caption_en=entry.caption_en,
                )
                for entry in entries_by_page.get(page.id, [])
            ],
        )
        for page in pages
    ]

    media = list(
        (
            await db.execute(
                select(BOQV2QuotationMedia)
                .where(BOQV2QuotationMedia.revision_id == revision_id)
                .order_by(BOQV2QuotationMedia.created_at, BOQV2QuotationMedia.id)
            )
        ).scalars()
    )
    media_payload = [
        BOQV2QuotationMediaResponse(
            id=item.id,
            origin_type=item.origin_type,
            origin_id=item.origin_id,
            original_filename=item.original_filename,
            content_type=item.content_type,
            size_bytes=item.size_bytes,
            width=item.width,
            height=item.height,
            sha256=item.sha256,
            created_at=_timestamp(item.created_at),
        )
        for item in media
    ]
    return section_payload, page_payload, media_payload


async def replace_composition(
    db: AsyncSession,
    *,
    revision: BOQV2Revision,
    quotation: BOQV2QuotationDraft,
    valid_scope_logical_ids: set[UUID],
) -> None:
    sections = quotation.document_sections or default_sections(quotation.document_pages)
    referenced_media_ids = {
        entry.media_id for page in quotation.visual_pages for entry in page.entries
    }
    if referenced_media_ids:
        owned_media_ids = set(
            (
                await db.execute(
                    select(BOQV2QuotationMedia.id).where(
                        BOQV2QuotationMedia.id.in_(referenced_media_ids),
                        BOQV2QuotationMedia.revision_id == revision.id,
                        BOQV2QuotationMedia.project_id == revision.project_id,
                    )
                )
            ).scalars()
        )
        if owned_media_ids != referenced_media_ids:
            raise BOQDomainError(
                "QUOTATION_MEDIA_NOT_OWNED",
                "Visual media must belong to this quotation revision",
            )
    for page in quotation.visual_pages:
        for entry in page.entries:
            if (
                entry.scope_logical_id is not None
                and entry.scope_logical_id not in valid_scope_logical_ids
            ):
                raise BOQDomainError(
                    "QUOTATION_VISUAL_SCOPE_INVALID",
                    "Visual entry scope does not belong to this revision",
                )

    existing_page_ids = list(
        (
            await db.execute(
                select(BOQV2QuotationVisualPage.id).where(
                    BOQV2QuotationVisualPage.revision_id == revision.id
                )
            )
        ).scalars()
    )
    if existing_page_ids:
        await db.execute(
            delete(BOQV2QuotationVisualEntry).where(
                BOQV2QuotationVisualEntry.page_id.in_(existing_page_ids)
            )
        )
    await db.execute(
        delete(BOQV2QuotationVisualPage).where(
            BOQV2QuotationVisualPage.revision_id == revision.id
        )
    )
    await db.execute(
        delete(BOQV2QuotationSection).where(
            BOQV2QuotationSection.revision_id == revision.id
        )
    )
    await db.flush()

    for section in sections:
        db.add(
            BOQV2QuotationSection(
                id=uuid4(),
                project_id=revision.project_id,
                revision_id=revision.id,
                section_type=section.section_type,
                enabled=section.enabled,
                position=section.position,
                title_th=section.title_th,
                title_en=section.title_en,
            )
        )
    for page in quotation.visual_pages:
        page_row = BOQV2QuotationVisualPage(
            id=uuid4(),
            project_id=revision.project_id,
            revision_id=revision.id,
            position=page.position,
            layout=page.layout,
            title_th=page.title_th,
            title_en=page.title_en,
            description_th=page.description_th,
            description_en=page.description_en,
        )
        db.add(page_row)
        await db.flush()
        for entry in page.entries:
            db.add(
                BOQV2QuotationVisualEntry(
                    id=uuid4(),
                    page_id=page_row.id,
                    media_id=entry.media_id,
                    scope_logical_id=entry.scope_logical_id,
                    position=entry.position,
                    caption_th=entry.caption_th,
                    caption_en=entry.caption_en,
                )
            )
    revision.document_pages = legacy_pages_from_sections(sections)
    await db.flush()


async def create_default_composition(
    db: AsyncSession,
    *,
    revision: BOQV2Revision,
) -> None:
    quotation = BOQV2QuotationDraft(
        document_pages=list(revision.document_pages or []),
        document_sections=default_sections(list(revision.document_pages or [])),
    )
    await replace_composition(
        db,
        revision=revision,
        quotation=quotation,
        valid_scope_logical_ids=set(),
    )


async def clone_composition(
    db: AsyncSession,
    *,
    source_revision: BOQV2Revision,
    target_revision: BOQV2Revision,
    include_media: bool = True,
) -> None:
    sections, pages, media = await load_composition(
        db,
        revision_id=source_revision.id,
        legacy_document_pages=list(source_revision.document_pages or []),
    )
    media_id_map: dict[UUID, UUID] = {}
    if include_media and media:
        source_rows = list(
            (
                await db.execute(
                    select(BOQV2QuotationMedia).where(
                        BOQV2QuotationMedia.revision_id == source_revision.id
                    )
                )
            ).scalars()
        )
        for item in source_rows:
            target_id = uuid4()
            media_id_map[item.id] = target_id
            db.add(
                BOQV2QuotationMedia(
                    id=target_id,
                    project_id=target_revision.project_id,
                    revision_id=target_revision.id,
                    origin_type=item.origin_type,
                    origin_id=item.origin_id,
                    storage_key=item.storage_key,
                    original_filename=item.original_filename,
                    content_type=item.content_type,
                    size_bytes=item.size_bytes,
                    width=item.width,
                    height=item.height,
                    sha256=item.sha256,
                    created_by=target_revision.created_by,
                )
            )
    target_pages = []
    if include_media:
        for page in pages:
            target_pages.append(
                {
                    **page.model_dump(exclude={"id", "entries"}),
                    "entries": [
                        {
                            **entry.model_dump(exclude={"id", "media_id"}),
                            "media_id": media_id_map[entry.media_id],
                        }
                        for entry in page.entries
                        if entry.media_id in media_id_map
                    ],
                }
            )
    draft = BOQV2QuotationDraft(
        document_pages=list(source_revision.document_pages or []),
        document_sections=[item.model_dump(exclude={"id"}) for item in sections],
        visual_pages=target_pages,
    )
    target_scope_logical_ids = set(
        (
            await db.execute(
                select(BOQV2ScopeNode.logical_id).where(
                    BOQV2ScopeNode.revision_id == target_revision.id
                )
            )
        ).scalars()
    )
    await replace_composition(
        db,
        revision=target_revision,
        quotation=draft,
        valid_scope_logical_ids=target_scope_logical_ids,
    )


async def snapshot_composition_manifest(
    db: AsyncSession,
    *,
    revision: BOQV2Revision,
    include_storage: bool,
) -> dict[str, object]:
    sections, pages, media = await load_composition(
        db,
        revision_id=revision.id,
        legacy_document_pages=list(revision.document_pages or []),
    )
    referenced = {entry.media_id for page in pages for entry in page.entries}
    media_rows: dict[UUID, BOQV2QuotationMedia] = {}
    if referenced:
        media_rows = {
            item.id: item
            for item in (
                await db.execute(
                    select(BOQV2QuotationMedia).where(
                        BOQV2QuotationMedia.id.in_(referenced),
                        BOQV2QuotationMedia.revision_id == revision.id,
                    )
                )
            ).scalars()
        }
    if set(media_rows) != referenced:
        raise BOQDomainError(
            "QUOTATION_MEDIA_NOT_OWNED",
            "Frozen visual media must belong to this quotation revision",
        )
    try:
        BOQV2QuotationDraft(
            document_pages=list(revision.document_pages or []),
            document_sections=[
                BOQV2QuotationSectionDraft.model_validate(
                    item.model_dump(exclude={"id"})
                )
                for item in sections
            ],
            visual_pages=[
                BOQV2QuotationVisualPageDraft.model_validate(
                    {
                        **page.model_dump(exclude={"id", "entries"}),
                        "entries": [
                            entry.model_dump(exclude={"id"}) for entry in page.entries
                        ],
                    }
                )
                for page in pages
            ],
        )
    except ValidationError as error:
        raise BOQDomainError(
            "QUOTATION_DOCUMENT_INVALID",
            "Quotation sections or visual pages are invalid",
        ) from error
    media_manifest = []
    for item in media:
        if item.id not in referenced:
            continue
        row = media_rows[item.id]
        payload: dict[str, object] = {
            "id": str(item.id),
            "origin_type": item.origin_type,
            "origin_id": item.origin_id,
            "original_filename": item.original_filename,
            "content_type": item.content_type,
            "size_bytes": item.size_bytes,
            "width": item.width,
            "height": item.height,
            "sha256": item.sha256,
        }
        if include_storage:
            payload["storage_key"] = row.storage_key
        media_manifest.append(payload)
    return {
        "schema_version": DOCUMENT_SCHEMA_VERSION,
        "sections": [item.model_dump(mode="json") for item in sections],
        "visual_pages": [item.model_dump(mode="json") for item in pages],
        "media_assets": media_manifest,
    }
