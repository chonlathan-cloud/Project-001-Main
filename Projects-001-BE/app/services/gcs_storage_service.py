"""
GCS helpers for receipt and KYC file storage.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import threading
import unicodedata
from datetime import UTC, date, datetime, timedelta
from pathlib import PurePosixPath
from typing import BinaryIO
from uuid import UUID, uuid4

try:
    from google.auth import default as google_auth_default
    from google.auth import credentials as google_auth_credentials
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.cloud import storage
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    google_auth_default = None  # type: ignore[assignment]
    google_auth_credentials = None  # type: ignore[assignment]
    GoogleAuthRequest = None  # type: ignore[assignment,misc]
    storage = None  # type: ignore[assignment]
    _STORAGE_IMPORT_ERROR = exc
else:
    _STORAGE_IMPORT_ERROR = None

from app.core.config import get_settings
from app.services.daily_report_thumbnail_service import (
    THUMBNAIL_CACHE_CONTROL,
    create_daily_report_thumbnail,
    daily_report_thumbnail_storage_key,
)

_settings = get_settings()
_DEFAULT_BUCKET = _settings.gcs_bucket_name
_KYC_PREFIX = _settings.gcs_kyc_prefix.strip().strip("/")
_PROFILE_PREFIX = _settings.gcs_profile_prefix.strip().strip("/")
_TEMP_BILLS_PREFIX = _settings.gcs_temp_bills_prefix.strip().strip("/")
_PERM_BILLS_PREFIX = _settings.gcs_perm_bills_prefix.strip().strip("/")
_INSPECTION_BUCKET = _settings.inspection_gcs_bucket or _settings.gcs_bucket_name
_INSPECTION_PREFIX = _settings.inspection_gcs_prefix.strip().strip("/")
_DAILY_REPORT_BUCKET = _settings.daily_report_gcs_bucket or _settings.gcs_bucket_name
_DAILY_REPORT_PREFIX = _settings.daily_report_gcs_prefix.strip().strip("/")
_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

_storage_client = None
_iam_signing_credentials = None
_iam_signing_credentials_lock = threading.Lock()
logger = logging.getLogger(__name__)


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


def get_inspection_bucket_name() -> str:
    return _require_bucket_name(_INSPECTION_BUCKET, "INSPECTION_GCS_BUCKET")


def get_daily_report_bucket_name() -> str:
    return _require_bucket_name(_DAILY_REPORT_BUCKET, "DAILY_REPORT_GCS_BUCKET")


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


def _paid_document_prefix(payment_date: date, internal_reference: str) -> str:
    safe_reference = re.sub(r"[^A-Za-z0-9_-]+", "-", internal_reference).strip("-")
    if not safe_reference:
        raise ValueError("Payment reference is required for paid-document storage.")
    return (
        f"{_PERM_BILLS_PREFIX}/paid/{payment_date:%Y/%m/%d}/"
        f"{safe_reference}"
    )


def paid_document_storage_prefix(payment_date: date, internal_reference: str) -> str:
    """Return the private GCS prefix shared by accounting payment documents."""

    return f"gs://{get_default_bucket_name()}/{_paid_document_prefix(payment_date, internal_reference)}"


def _build_paid_original_object_name(
    *,
    request_id: UUID,
    source_object_name: str,
    payment_date: date,
    internal_reference: str,
) -> str:
    safe_name = _sanitize_filename(PurePosixPath(source_object_name).name)
    return (
        f"{_paid_document_prefix(payment_date, internal_reference)}/"
        f"original/{request_id}-{safe_name}"
    )


def _build_payment_confirmation_object_name(
    *,
    payment_date: date,
    internal_reference: str,
    confirmation_id: UUID,
    version: int,
    file_name: str | None,
) -> str:
    safe_name = _sanitize_filename(file_name or f"confirmation-{confirmation_id}")
    return (
        f"{_paid_document_prefix(payment_date, internal_reference)}/"
        f"payment_confirmation/v{version}-{confirmation_id}-{safe_name}"
    )


def _build_kyc_object_name(file_name: str | None, entity_key: str) -> str:
    safe_name = _sanitize_filename(file_name or f"{entity_key}.jpg")
    return f"{_KYC_PREFIX}/{entity_key}/{uuid4()}-{safe_name}"


def _build_profile_object_name(file_name: str | None, entity_key: str) -> str:
    safe_name = _sanitize_filename(file_name or f"{entity_key}.jpg")
    return f"{_PROFILE_PREFIX}/{entity_key}/{uuid4()}-{safe_name}"


def _build_inspection_object_name(
    *,
    project_id: str,
    round_id: str,
    file_id: str,
    file_name: str | None,
    kind: str,
    zone_id: str | None = None,
    defect_id: str | None = None,
) -> str:
    safe_name = _sanitize_filename(file_name or f"{file_id}")
    safe_kind = str(kind or "").strip().upper()
    if safe_kind == "PLAN_IMAGE":
        zone_part = _sanitize_filename(zone_id or "zone")
        return f"{_INSPECTION_PREFIX}/{project_id}/{round_id}/plans/{zone_part}/{file_id}-{safe_name}"
    if safe_kind == "BEFORE_PHOTO":
        defect_part = _sanitize_filename(defect_id or "defect")
        return f"{_INSPECTION_PREFIX}/{project_id}/{round_id}/defects/{defect_part}/before/{file_id}-{safe_name}"
    if safe_kind == "AFTER_PHOTO":
        defect_part = _sanitize_filename(defect_id or "defect")
        return f"{_INSPECTION_PREFIX}/{project_id}/{round_id}/defects/{defect_part}/after/{file_id}-{safe_name}"
    if safe_kind == "REPORT_PDF":
        return f"{_INSPECTION_PREFIX}/{project_id}/{round_id}/reports/{file_id}-{safe_name}"
    return f"{_INSPECTION_PREFIX}/{project_id}/{round_id}/files/{file_id}-{safe_name}"


def _build_daily_report_object_name(
    *,
    project_id: str,
    report_date: str,
    submission_id: str,
    media_id: str,
    file_name: str | None,
) -> str:
    safe_name = _sanitize_filename(file_name or media_id)
    safe_date = re.sub(r"[^0-9-]+", "", report_date) or "undated"
    return (
        f"{_DAILY_REPORT_PREFIX}/{project_id}/{safe_date}/"
        f"{submission_id}/{media_id}-{safe_name}"
    )


def _upload_bytes_to_bucket_sync(
    *,
    bucket_name: str,
    object_name: str,
    file_bytes: bytes,
    content_type: str | None,
    cache_control: str | None = None,
) -> str:
    client = _require_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    if cache_control:
        blob.cache_control = cache_control
    blob.upload_from_string(
        file_bytes,
        content_type=content_type or "application/octet-stream",
    )
    return f"gs://{bucket_name}/{object_name}"


def _upload_file_to_bucket_sync(
    *,
    bucket_name: str,
    object_name: str,
    file_obj: BinaryIO,
    size_bytes: int,
    content_type: str | None,
) -> str:
    client = _require_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    file_obj.seek(0)
    blob.upload_from_file(
        file_obj,
        size=size_bytes,
        content_type=content_type or "application/octet-stream",
        rewind=True,
    )
    return f"gs://{bucket_name}/{object_name}"


def _read_file_bytes_sync(file_obj: BinaryIO) -> bytes:
    file_obj.seek(0)
    file_bytes = file_obj.read()
    file_obj.seek(0)
    return file_bytes


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


async def upload_profile_image_to_storage(
    *,
    file_bytes: bytes,
    file_name: str | None,
    content_type: str | None,
    entity_key: str,
) -> str:
    bucket_name = get_default_bucket_name()
    object_name = _build_profile_object_name(file_name, entity_key)
    return await asyncio.to_thread(
        _upload_bytes_to_bucket_sync,
        bucket_name=bucket_name,
        object_name=object_name,
        file_bytes=file_bytes,
        content_type=content_type,
    )


async def upload_inspection_file_to_storage(
    *,
    project_id: str,
    round_id: str,
    file_id: str,
    kind: str,
    file_bytes: bytes,
    file_name: str | None,
    content_type: str | None,
    zone_id: str | None = None,
    defect_id: str | None = None,
) -> str:
    bucket_name = get_inspection_bucket_name()
    object_name = _build_inspection_object_name(
        project_id=project_id,
        round_id=round_id,
        file_id=file_id,
        file_name=file_name,
        kind=kind,
        zone_id=zone_id,
        defect_id=defect_id,
    )
    return await asyncio.to_thread(
        _upload_bytes_to_bucket_sync,
        bucket_name=bucket_name,
        object_name=object_name,
        file_bytes=file_bytes,
        content_type=content_type,
    )


async def upload_daily_report_media_to_storage(
    *,
    project_id: str,
    report_date: str,
    submission_id: str,
    media_id: str,
    file_obj: BinaryIO,
    size_bytes: int,
    file_name: str | None,
    content_type: str | None,
) -> str:
    bucket_name = get_daily_report_bucket_name()
    object_name = _build_daily_report_object_name(
        project_id=project_id,
        report_date=report_date,
        submission_id=submission_id,
        media_id=media_id,
        file_name=file_name,
    )
    storage_key = await asyncio.to_thread(
        _upload_file_to_bucket_sync,
        bucket_name=bucket_name,
        object_name=object_name,
        file_obj=file_obj,
        size_bytes=size_bytes,
        content_type=content_type,
    )
    if not str(content_type or "").startswith("image/"):
        return storage_key

    try:
        source_bytes = await asyncio.to_thread(_read_file_bytes_sync, file_obj)
        thumbnail_bytes = await asyncio.to_thread(
            create_daily_report_thumbnail,
            source_bytes,
        )
        thumbnail_key = daily_report_thumbnail_storage_key(storage_key)
        thumbnail_bucket, thumbnail_object = _parse_gs_storage_key(thumbnail_key)
        await asyncio.to_thread(
            _upload_bytes_to_bucket_sync,
            bucket_name=thumbnail_bucket,
            object_name=thumbnail_object,
            file_bytes=thumbnail_bytes,
            content_type="image/webp",
            cache_control=THUMBNAIL_CACHE_CONTROL,
        )
    except Exception as exc:  # Thumbnail failure must not discard the original upload.
        logger.warning(
            "daily_report_thumbnail_generation_failed",
            extra={
                "media_id": media_id,
                "error_category": type(exc).__name__,
            },
        )

    return storage_key


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


def _organize_input_receipt_in_paid_storage_sync(
    *,
    storage_key: str,
    request_id: UUID,
    payment_date: date,
    internal_reference: str,
) -> str:
    bucket_name = get_default_bucket_name()
    source_bucket_name, source_object_name = _parse_gs_storage_key(storage_key)
    if source_bucket_name != bucket_name:
        raise ValueError(
            f"Unexpected receipt bucket '{source_bucket_name}'. Expected '{bucket_name}'."
        )

    target_object_name = _build_paid_original_object_name(
        request_id=request_id,
        source_object_name=source_object_name,
        payment_date=payment_date,
        internal_reference=internal_reference,
    )
    if source_object_name == target_object_name:
        return storage_key
    if not source_object_name.startswith(f"{_PERM_BILLS_PREFIX}/"):
        raise ValueError(
            f"Unexpected approved receipt prefix '{source_object_name}'. "
            f"Expected '{_PERM_BILLS_PREFIX}/...'."
        )

    client = _require_storage_client()
    bucket = client.bucket(bucket_name)
    source_blob = bucket.blob(source_object_name)
    target_blob = bucket.blob(target_object_name)
    target_exists = target_blob.exists(client)
    source_exists = source_blob.exists(client)

    if target_exists:
        return f"gs://{bucket_name}/{target_object_name}"
    if not source_exists:
        raise FileNotFoundError(f"Approved receipt object not found in GCS: {storage_key}")

    bucket.copy_blob(source_blob, bucket, target_object_name)
    return f"gs://{bucket_name}/{target_object_name}"


async def organize_input_receipt_in_paid_storage(
    *,
    storage_key: str | None,
    request_id: UUID,
    payment_date: date,
    internal_reference: str,
) -> str | None:
    """Copy an approved receipt into its paid folder without deleting the source.

    The caller should commit the database payment record first, then remove the
    old object. Keeping the source until commit provides a recoverable boundary
    between GCS and the database transaction.
    """

    if not storage_key:
        return None
    return await asyncio.to_thread(
        _organize_input_receipt_in_paid_storage_sync,
        storage_key=storage_key,
        request_id=request_id,
        payment_date=payment_date,
        internal_reference=internal_reference,
    )


async def upload_payment_confirmation_to_storage(
    *,
    file_bytes: bytes,
    file_name: str | None,
    content_type: str | None,
    payment_date: date,
    internal_reference: str,
    confirmation_id: UUID,
    version: int,
) -> str:
    object_name = _build_payment_confirmation_object_name(
        payment_date=payment_date,
        internal_reference=internal_reference,
        confirmation_id=confirmation_id,
        version=version,
        file_name=file_name,
    )
    return await asyncio.to_thread(
        _upload_bytes_to_bucket_sync,
        bucket_name=get_default_bucket_name(),
        object_name=object_name,
        file_bytes=file_bytes,
        content_type=content_type,
    )


def _keyless_signed_url_credential_kwargs() -> dict[str, str]:
    """Return an IAM-capable access token for keyless Cloud Run signing."""
    global _iam_signing_credentials

    if google_auth_default is None or GoogleAuthRequest is None:
        raise RuntimeError(
            "Google authentication dependencies are unavailable for GCS signed URLs."
        ) from _STORAGE_IMPORT_ERROR

    with _iam_signing_credentials_lock:
        if _iam_signing_credentials is None:
            _iam_signing_credentials, _ = google_auth_default(
                scopes=[_CLOUD_PLATFORM_SCOPE]
            )

        credentials = _iam_signing_credentials
        service_account_email = str(
            getattr(credentials, "service_account_email", "") or ""
        ).strip()
        access_token = getattr(credentials, "token", None)
        needs_refresh = (
            not bool(getattr(credentials, "valid", False))
            or not access_token
            or not service_account_email
            or service_account_email == "default"
        )
        if needs_refresh:
            credentials.refresh(GoogleAuthRequest())
            service_account_email = str(
                getattr(credentials, "service_account_email", "") or ""
            ).strip()
            access_token = getattr(credentials, "token", None)

    if (
        not service_account_email
        or service_account_email == "default"
        or not access_token
    ):
        raise RuntimeError(
            "Application Default Credentials cannot sign GCS URLs. Attach a service "
            "account with iam.serviceAccounts.signBlob permission."
        )

    return {
        "service_account_email": service_account_email,
        "access_token": access_token,
    }


def _signed_url_credential_kwargs(client) -> dict[str, str]:
    """Use local signing keys when available, otherwise use keyless IAM signing."""
    credentials = client._credentials
    if google_auth_credentials is None:
        raise RuntimeError(
            "Google authentication dependencies are unavailable for GCS signed URLs."
        ) from _STORAGE_IMPORT_ERROR

    if isinstance(credentials, google_auth_credentials.Signing):
        return {}

    return _keyless_signed_url_credential_kwargs()


def _generate_signed_url_for_storage_key_sync(
    *,
    storage_key: str,
    expires_in_minutes: int,
) -> str:
    bucket_name, object_name = _parse_gs_storage_key(storage_key)
    client = _require_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    signing_kwargs = _signed_url_credential_kwargs(client)

    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expires_in_minutes),
        method="GET",
        **signing_kwargs,
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


def _download_storage_key_bytes_sync(storage_key: str) -> bytes:
    bucket_name, object_name = _parse_gs_storage_key(storage_key)
    client = _require_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    if not blob.exists(client):
        raise FileNotFoundError(f"Object not found in GCS: {storage_key}")
    return blob.download_as_bytes()


async def download_storage_key_bytes(storage_key: str) -> bytes:
    return await asyncio.to_thread(_download_storage_key_bytes_sync, storage_key)


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


async def delete_daily_report_media_storage(storage_key: str) -> None:
    """Delete an original Daily Report object and its derived thumbnail."""
    await delete_storage_key(storage_key)
    try:
        await delete_storage_key(daily_report_thumbnail_storage_key(storage_key))
    except Exception as exc:  # Original deletion remains the primary operation.
        logger.warning(
            "daily_report_thumbnail_delete_failed",
            extra={"error_category": type(exc).__name__},
        )
