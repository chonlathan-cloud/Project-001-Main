"""
Cleanup helpers for abandoned temporary input receipts in GCS.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.input_request import InputRequest
from app.schemas.input_schema import TempReceiptCleanupResponse
from app.services.gcs_storage_service import (
    delete_storage_key,
    get_default_bucket_name,
    list_temp_receipt_objects,
    temp_receipt_storage_prefix,
)


async def cleanup_orphan_temp_receipts(
    *,
    db: AsyncSession,
    older_than_hours: int = 24,
) -> TempReceiptCleanupResponse:
    cutoff = datetime.now(UTC) - timedelta(hours=older_than_hours)

    referenced_rows = (
        await db.execute(
            select(InputRequest.receipt_storage_key).where(
                InputRequest.receipt_storage_key.is_not(None)
            )
        )
    ).scalars().all()

    referenced_temp_keys = {
        str(value)
        for value in referenced_rows
        if value and str(value).startswith(
            f"gs://{get_default_bucket_name()}/{temp_receipt_storage_prefix()}/"
        )
    }

    temp_objects = await list_temp_receipt_objects()

    deleted_storage_keys: list[str] = []
    kept_referenced_storage_keys: list[str] = []
    skipped_recent_storage_keys: list[str] = []

    for item in temp_objects:
        storage_key = str(item["storage_key"])
        updated_at = item["updated_at"]
        if not isinstance(updated_at, datetime):
            continue
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)

        if storage_key in referenced_temp_keys:
            kept_referenced_storage_keys.append(storage_key)
            continue

        if updated_at > cutoff:
            skipped_recent_storage_keys.append(storage_key)
            continue

        await delete_storage_key(storage_key)
        deleted_storage_keys.append(storage_key)

    return TempReceiptCleanupResponse(
        bucket_name=get_default_bucket_name(),
        checked_object_count=len(temp_objects),
        deleted_object_count=len(deleted_storage_keys),
        kept_referenced_count=len(kept_referenced_storage_keys),
        skipped_recent_count=len(skipped_recent_storage_keys),
        deleted_storage_keys=deleted_storage_keys,
        kept_referenced_storage_keys=kept_referenced_storage_keys,
        skipped_recent_storage_keys=skipped_recent_storage_keys,
        older_than_hours=older_than_hours,
        message="Temp receipt cleanup completed.",
    )
