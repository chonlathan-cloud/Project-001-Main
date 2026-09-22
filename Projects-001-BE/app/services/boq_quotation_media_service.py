"""Private quotation visual-media upload, import, access, and integrity checks."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.boq_v2 import (
    BOQV2QuotationMedia,
    BOQV2QuotationVisualEntry,
    BOQV2Revision,
)
from app.schemas.boq_quotation_schema import BOQV2MediaCandidate
from app.schemas.boq_v2_schema import BOQV2QuotationMediaResponse
from app.services import daily_report_service, inspection_service
from app.services.boq_domain_service import (
    BOQDomainError,
    assert_expected_version,
    assert_mutable_draft,
)
from app.services.gcs_storage_service import (
    delete_storage_key,
    download_storage_key_bytes,
    generate_signed_url_for_storage_key,
    upload_boq_quotation_media,
)


register_heif_opener()
Image.MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_IMAGE_TYPES = {
    "image/heic",
    "image/heif",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
IMAGE_FORMAT_TYPES = {
    "JPEG": {"image/jpeg", "image/jpg"},
    "PNG": {"image/png"},
    "WEBP": {"image/webp"},
    "HEIF": {"image/heic", "image/heif"},
}


def _timestamp(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        current = value
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        return current.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def _normalize_image(
    file_bytes: bytes, content_type: str | None
) -> tuple[bytes, int, int, str]:
    limit = get_settings().boq_quotation_media_max_bytes
    if not file_bytes:
        raise BOQDomainError(
            "QUOTATION_MEDIA_EMPTY", "Uploaded quotation image is empty"
        )
    if len(file_bytes) > limit:
        raise BOQDomainError(
            "QUOTATION_MEDIA_TOO_LARGE",
            f"Quotation image exceeds the {limit // (1024 * 1024)}MB limit",
        )
    normalized_type = str(content_type or "").lower().strip()
    if normalized_type not in ALLOWED_IMAGE_TYPES:
        raise BOQDomainError(
            "QUOTATION_MEDIA_TYPE_INVALID",
            "Quotation visuals support JPEG, PNG, WebP, HEIC, or HEIF images",
        )
    try:
        with Image.open(BytesIO(file_bytes)) as source:
            detected_format = str(source.format or "").upper()
            expected_types = IMAGE_FORMAT_TYPES.get(detected_format)
            if expected_types is None or normalized_type not in expected_types:
                raise ValueError("declared MIME does not match the decoded image")
            if source.width * source.height > Image.MAX_IMAGE_PIXELS:
                raise ValueError("image dimensions exceed the safe decode limit")
            source.verify()
        with Image.open(BytesIO(file_bytes)) as source:
            image = ImageOps.exif_transpose(source)
            image.load()
            if image.width <= 0 or image.height <= 0:
                raise ValueError("invalid image dimensions")
            if image.mode in {"RGBA", "LA"} or (
                image.mode == "P" and "transparency" in image.info
            ):
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            width, height = image.size
            output = BytesIO()
            image.save(output, format="JPEG", quality=88, optimize=True)
            normalized = output.getvalue()
            if len(normalized) > limit:
                raise ValueError("normalized image exceeds the storage size limit")
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as error:
        raise BOQDomainError(
            "QUOTATION_MEDIA_INVALID",
            "Quotation image is corrupt or cannot be decoded",
        ) from error
    return normalized, width, height, hashlib.sha256(normalized).hexdigest()


async def _locked_revision(
    db: AsyncSession,
    revision_id: UUID,
    *,
    expected_version: int,
) -> BOQV2Revision:
    revision = (
        await db.execute(
            select(BOQV2Revision)
            .where(BOQV2Revision.id == revision_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if revision is None:
        raise BOQDomainError("BOQ_REVISION_NOT_FOUND", "BOQ revision was not found")
    assert_mutable_draft(revision.status)
    assert_expected_version(current=revision.version, expected=expected_version)
    return revision


def _response(
    item: BOQV2QuotationMedia,
    *,
    preview_url: str | None = None,
    expires: int | None = None,
    revision_version: int | None = None,
) -> BOQV2QuotationMediaResponse:
    return BOQV2QuotationMediaResponse(
        id=item.id,
        origin_type=item.origin_type,
        origin_id=item.origin_id,
        original_filename=item.original_filename,
        content_type=item.content_type,
        size_bytes=item.size_bytes,
        width=item.width,
        height=item.height,
        sha256=item.sha256,
        preview_url=preview_url,
        preview_expires_in_minutes=expires,
        revision_version=revision_version,
        created_at=_timestamp(item.created_at) or datetime.now(UTC).isoformat(),
    )


async def _persist_media(
    db: AsyncSession,
    *,
    revision: BOQV2Revision,
    actor: str,
    origin_type: str,
    origin_id: str | None,
    original_filename: str | None,
    file_bytes: bytes,
    content_type: str | None,
) -> BOQV2QuotationMediaResponse:
    normalized, width, height, digest = _normalize_image(file_bytes, content_type)
    media_id = uuid4()
    storage_key = await upload_boq_quotation_media(
        project_id=str(revision.project_id),
        revision_id=str(revision.id),
        media_id=str(media_id),
        file_bytes=normalized,
    )
    item = BOQV2QuotationMedia(
        id=media_id,
        project_id=revision.project_id,
        revision_id=revision.id,
        origin_type=origin_type,
        origin_id=origin_id,
        storage_key=storage_key,
        original_filename=original_filename,
        content_type="image/jpeg",
        size_bytes=len(normalized),
        width=width,
        height=height,
        sha256=digest,
        created_by=actor,
    )
    db.add(item)
    revision.version += 1
    revision.updated_at = datetime.now(UTC)
    await db.flush()
    expires = get_settings().signed_url_expires_minutes
    preview_url = await generate_signed_url_for_storage_key(
        storage_key=storage_key,
        expires_in_minutes=expires,
    )
    return _response(
        item,
        preview_url=preview_url,
        expires=expires,
        revision_version=revision.version,
    )


async def upload_media(
    db: AsyncSession,
    *,
    revision_id: UUID,
    expected_version: int,
    actor: str,
    file_bytes: bytes,
    file_name: str | None,
    content_type: str | None,
) -> BOQV2QuotationMediaResponse:
    revision = await _locked_revision(
        db, revision_id, expected_version=expected_version
    )
    return await _persist_media(
        db,
        revision=revision,
        actor=actor,
        origin_type="UPLOAD",
        origin_id=None,
        original_filename=file_name,
        file_bytes=file_bytes,
        content_type=content_type,
    )


def _source_media(origin_type: str, origin_id: str) -> tuple[dict[str, object], str]:
    if origin_type == "DAILY_REPORT":
        item = daily_report_service.get_media(origin_id)
        storage_key = str(item.get("storage_key") or "")
    else:
        item = inspection_service.get_file(origin_id)
        storage_key = str(item.get("gcs_path") or "")
    if not storage_key:
        raise BOQDomainError(
            "QUOTATION_MEDIA_SOURCE_MISSING",
            "Selected project media does not have a stored image",
        )
    return item, storage_key


async def import_media(
    db: AsyncSession,
    *,
    revision_id: UUID,
    expected_version: int,
    actor: str,
    origin_type: str,
    origin_id: str,
) -> BOQV2QuotationMediaResponse:
    revision = await _locked_revision(
        db, revision_id, expected_version=expected_version
    )
    item, storage_key = await asyncio.to_thread(_source_media, origin_type, origin_id)
    if str(item.get("project_id") or "") != str(revision.project_id):
        raise BOQDomainError(
            "QUOTATION_MEDIA_SOURCE_NOT_FOUND",
            "Selected media does not belong to this project",
        )
    content_type = str(item.get("content_type") or "").lower()
    file_bytes = await download_storage_key_bytes(storage_key)
    return await _persist_media(
        db,
        revision=revision,
        actor=actor,
        origin_type=origin_type,
        origin_id=origin_id,
        original_filename=str(
            item.get("file_name") or item.get("original_filename") or origin_id
        ),
        file_bytes=file_bytes,
        content_type=content_type,
    )


async def list_media_candidates(
    *,
    project_id: UUID,
) -> list[BOQV2MediaCandidate]:
    project_key = str(project_id)
    daily_items, inspection_items = await asyncio.gather(
        asyncio.to_thread(
            daily_report_service.list_media_for_mcp,
            project_ids={project_key},
            limit=200,
        ),
        asyncio.to_thread(
            inspection_service.list_files_for_mcp,
            project_ids={project_key},
            limit=200,
        ),
    )
    candidates: list[tuple[str, dict[str, object], str]] = []
    for origin_type, items, key_name in (
        ("DAILY_REPORT", daily_items, "storage_key"),
        ("INSPECTION", inspection_items, "gcs_path"),
    ):
        for item in items:
            content_type = str(item.get("content_type") or "").lower()
            storage_key = str(item.get(key_name) or "")
            if content_type in ALLOWED_IMAGE_TYPES and storage_key:
                candidates.append((origin_type, item, storage_key))
    expires = get_settings().signed_url_expires_minutes
    urls = await asyncio.gather(
        *[
            generate_signed_url_for_storage_key(
                storage_key=storage_key,
                expires_in_minutes=expires,
            )
            for _, _, storage_key in candidates
        ]
    )
    return [
        BOQV2MediaCandidate(
            origin_type=origin_type,
            origin_id=str(item.get("id")),
            file_name=str(item.get("file_name") or item.get("original_filename") or "")
            or None,
            content_type=str(item.get("content_type") or "") or None,
            size_bytes=int(item.get("size_bytes") or 0) or None,
            created_at=_timestamp(item.get("created_at") or item.get("uploaded_at")),
            preview_url=url,
            preview_expires_in_minutes=expires,
        )
        for (origin_type, item, _), url in zip(candidates, urls, strict=True)
    ]


async def media_access(
    db: AsyncSession,
    *,
    revision_id: UUID,
    media_id: UUID,
) -> BOQV2QuotationMediaResponse:
    item = (
        await db.execute(
            select(BOQV2QuotationMedia).where(
                BOQV2QuotationMedia.id == media_id,
                BOQV2QuotationMedia.revision_id == revision_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise BOQDomainError(
            "QUOTATION_MEDIA_NOT_FOUND",
            "Quotation media does not belong to this revision",
        )
    expires = get_settings().signed_url_expires_minutes
    url = await generate_signed_url_for_storage_key(
        storage_key=item.storage_key,
        expires_in_minutes=expires,
    )
    return _response(item, preview_url=url, expires=expires)


async def delete_media(
    db: AsyncSession,
    *,
    revision_id: UUID,
    media_id: UUID,
    expected_version: int,
) -> dict[str, object]:
    revision = await _locked_revision(
        db, revision_id, expected_version=expected_version
    )
    item = (
        await db.execute(
            select(BOQV2QuotationMedia).where(
                BOQV2QuotationMedia.id == media_id,
                BOQV2QuotationMedia.revision_id == revision.id,
                BOQV2QuotationMedia.project_id == revision.project_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise BOQDomainError(
            "QUOTATION_MEDIA_NOT_FOUND", "Quotation media was not found"
        )
    referenced = (
        await db.execute(
            select(BOQV2QuotationVisualEntry.id)
            .where(BOQV2QuotationVisualEntry.media_id == media_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if referenced is not None:
        raise BOQDomainError(
            "QUOTATION_MEDIA_IN_USE",
            "Remove the image from visual pages before deleting it",
        )
    storage_key = item.storage_key
    await db.execute(
        delete(BOQV2QuotationMedia).where(BOQV2QuotationMedia.id == media_id)
    )
    revision.version += 1
    revision.updated_at = datetime.now(UTC)
    await db.flush()
    shared_reference = (
        await db.execute(
            select(BOQV2QuotationMedia.id)
            .where(BOQV2QuotationMedia.storage_key == storage_key)
            .limit(1)
        )
    ).scalar_one_or_none()
    if shared_reference is None:
        await delete_storage_key(storage_key)
    return {"id": str(media_id), "deleted": True, "version": revision.version}


async def validate_revision_media(
    db: AsyncSession,
    *,
    revision_id: UUID,
) -> None:
    media = list(
        (
            await db.execute(
                select(BOQV2QuotationMedia)
                .join(
                    BOQV2QuotationVisualEntry,
                    BOQV2QuotationVisualEntry.media_id == BOQV2QuotationMedia.id,
                )
                .where(BOQV2QuotationMedia.revision_id == revision_id)
                .distinct()
            )
        ).scalars()
    )
    for item in media:
        try:
            file_bytes = await download_storage_key_bytes(item.storage_key)
        except FileNotFoundError as error:
            raise BOQDomainError(
                "QUOTATION_MEDIA_MISSING",
                "A selected quotation image is missing from private storage",
            ) from error
        if hashlib.sha256(file_bytes).hexdigest() != item.sha256:
            raise BOQDomainError(
                "QUOTATION_MEDIA_HASH_MISMATCH",
                "A selected quotation image failed its integrity check",
            )
