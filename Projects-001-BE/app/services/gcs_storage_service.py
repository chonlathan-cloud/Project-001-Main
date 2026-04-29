"""
GCS helpers for receipt and KYC file storage.
"""

from __future__ import annotations

import asyncio
import os
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from uuid import UUID, uuid4

try:
    from google.cloud import storage
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    storage = None  # type: ignore[assignment]
    _STORAGE_IMPORT_ERROR = exc
else:
    _STORAGE_IMPORT_ERROR = None

from app.core.config import get_settings

_settings = get_settings()
_DEFAULT_BUCKET = _settings.gcs_bucket_name
_KYC_PREFIX = _settings.gcs_kyc_prefix.strip().strip("/")
_TEMP_BILLS_PREFIX = _settings.gcs_temp_bills_prefix.strip().strip("/")
_PERM_BILLS_PREFIX = _settings.gcs_perm_bills_prefix.strip().strip("/")

_storage_client = None


def _require_storage_client():
    if storage is None:
        raise RuntimeError(
            "google-cloud-storage is not installed. Install backend dependencies first."
        ) from _STORAGE_IMPORT_ERROR

    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def _require_bucket_name(bucket_name: str | None, env_name: str) -> str:
    if not bucket_name:
        raise RuntimeError(f"Missing required environment variable: {env_name}")
    return bucket_name


def get_default_bucket_name() -> str:
    return _require_bucket_name(_DEFAULT_BUCKET, "GCS_BUCKET_NAME")


def _sanitize_filename(file_name: str | None) -> str:
    original_name = PurePosixPath(file_name or "receipt").name
    stem, ext = os.path.splitext(original_name)
    normalized_stem = (
        unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    )
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", normalized_stem).strip("-._") or "receipt"
    safe_ext = re.sub(r"[^A-Za-z0-9.]+", "", ext.lower())[:10]
    return f"{safe_stem}{safe_ext}"


def _parse_gs_storage_key(storage_key: str) -> tuple[str, str]:
    if not storage_key.startswith("gs://"):
        raise ValueError("Storage key must start with gs://")

    remainder = storage_key[5:]
    if "/" not in remainder:
        raise ValueError("Storage key must contain both bucket and object path.")

    bucket_name, object_name = remainder.split("/", 1)
    if not bucket_name or not object_name:
        raise ValueError("Storage key must contain both bucket and object path.")

    return bucket_name, object_name


def _build_temp_receipt_object_name(file_name: str | None) -> str:
    now = datetime.now(UTC)
    safe_name = _sanitize_filename(file_name)
    return f"{_TEMP_BILLS_PREFIX}/{now:%Y/%m/%d}/{uuid4()}-{safe_name}"


def _build_perm_receipt_object_name(request_id: UUID, source_object_name: str) -> str:
    now = datetime.now(UTC)
    safe_name = _sanitize_filename(PurePosixPath(source_object_name).name)
    return f"{_PERM_BILLS_PREFIX}/{now:%Y/%m/%d}/{request_id}-{safe_name}"


def _build_kyc_object_name(file_name: str | None, entity_key: str) -> str:
    safe_name = _sanitize_filename(file_name or f"{entity_key}.jpg")
    return f"{_KYC_PREFIX}/{entity_key}/{uuid4()}-{safe_name}"


def _upload_bytes_to_bucket_sync(
    *,
    bucket_name: str,
    object_name: str,
    file_bytes: bytes,
    content_type: str | None,
) -> str:
    client = _require_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(
        file_bytes,
        content_type=content_type or "application/octet-stream",
    )
    return f"gs://{bucket_name}/{object_name}"


async def upload_input_receipt_to_temp_storage(
    *,
    file_bytes: bytes,
    file_name: str | None,
    content_type: str | None,
) -> str:
    bucket_name = get_default_bucket_name()
    object_name = _build_temp_receipt_object_name(file_name)
    return await asyncio.to_thread(
        _upload_bytes_to_bucket_sync,
        bucket_name=bucket_name,
        object_name=object_name,
        file_bytes=file_bytes,
        content_type=content_type,
    )


async def upload_kyc_image_to_storage(
    *,
    file_bytes: bytes,
    file_name: str | None,
    content_type: str | None,
    entity_key: str,
) -> str:
    bucket_name = get_default_bucket_name()
    object_name = _build_kyc_object_name(file_name, entity_key)
    return await asyncio.to_thread(
        _upload_bytes_to_bucket_sync,
        bucket_name=bucket_name,
        object_name=object_name,
        file_bytes=file_bytes,
        content_type=content_type,
    )


def _move_input_receipt_to_perm_storage_sync(
    *,
    storage_key: str,
    request_id: UUID,
) -> str:
    bucket_name = get_default_bucket_name()
    source_bucket_name, source_object_name = _parse_gs_storage_key(storage_key)

    if source_bucket_name != bucket_name:
        raise ValueError(
            f"Unexpected receipt bucket '{source_bucket_name}'. Expected '{bucket_name}'."
        )

    if source_object_name.startswith(f"{_PERM_BILLS_PREFIX}/"):
        return storage_key

    if not source_object_name.startswith(f"{_TEMP_BILLS_PREFIX}/"):
        raise ValueError(
            f"Unexpected receipt prefix '{source_object_name}'. Expected '{_TEMP_BILLS_PREFIX}/...'."
        )

    client = _require_storage_client()
    source_bucket = client.bucket(source_bucket_name)
    source_blob = source_bucket.blob(source_object_name)
    if not source_blob.exists(client):
        raise FileNotFoundError(f"Receipt object not found in GCS: {storage_key}")

    target_object_name = _build_perm_receipt_object_name(request_id, source_object_name)
    target_bucket = client.bucket(bucket_name)

    source_bucket.copy_blob(source_blob, target_bucket, target_object_name)
    source_blob.delete()

    return f"gs://{bucket_name}/{target_object_name}"


async def move_input_receipt_to_perm_storage(
    *,
    storage_key: str | None,
    request_id: UUID,
) -> str | None:
    if not storage_key:
        return None

    return await asyncio.to_thread(
        _move_input_receipt_to_perm_storage_sync,
        storage_key=storage_key,
        request_id=request_id,
    )


def _generate_signed_url_for_storage_key_sync(
    *,
    storage_key: str,
    expires_in_minutes: int,
) -> str:
    bucket_name, object_name = _parse_gs_storage_key(storage_key)
    client = _require_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expires_in_minutes),
        method="GET",
    )


async def generate_signed_url_for_storage_key(
    *,
    storage_key: str,
    expires_in_minutes: int = 15,
) -> str:
    return await asyncio.to_thread(
        _generate_signed_url_for_storage_key_sync,
        storage_key=storage_key,
        expires_in_minutes=expires_in_minutes,
    )


def _list_temp_receipt_objects_sync() -> list[dict[str, object]]:
    bucket_name = get_default_bucket_name()
    client = _require_storage_client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=f"{_TEMP_BILLS_PREFIX}/")

    items: list[dict[str, object]] = []
    for blob in blobs:
        updated_at = blob.updated
        if updated_at is None:
            updated_at = datetime.now(UTC)
        elif updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)

        items.append(
            {
                "storage_key": f"gs://{bucket_name}/{blob.name}",
                "updated_at": updated_at,
            }
        )
    return items


def temp_receipt_storage_prefix() -> str:
    return _TEMP_BILLS_PREFIX


async def list_temp_receipt_objects() -> list[dict[str, object]]:
    return await asyncio.to_thread(_list_temp_receipt_objects_sync)


def _delete_storage_key_sync(storage_key: str) -> None:
    bucket_name, object_name = _parse_gs_storage_key(storage_key)
    client = _require_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    if blob.exists(client):
        blob.delete()


async def delete_storage_key(storage_key: str) -> None:
    await asyncio.to_thread(_delete_storage_key_sync, storage_key)
