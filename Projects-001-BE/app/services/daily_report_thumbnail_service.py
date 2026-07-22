"""Image thumbnail helpers for Daily Report media."""

from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath

from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener
except ImportError:  # pragma: no cover - guarded by runtime requirements
    register_heif_opener = None

if register_heif_opener is not None:
    register_heif_opener()

THUMBNAIL_MAX_DIMENSION = 1280
THUMBNAIL_QUALITY = 78
MAX_SOURCE_PIXELS = 60_000_000
THUMBNAIL_CACHE_CONTROL = "private, max-age=900"


def daily_report_thumbnail_object_name(object_name: str) -> str:
    """Return the deterministic WebP thumbnail path for a Daily Report object."""
    path = PurePosixPath(str(object_name or "").strip("/"))
    if not path.name or str(path) == ".":
        raise ValueError("Daily Report object name is required.")
    if "thumbnails" in path.parts:
        raise ValueError("A thumbnail cannot be used as a thumbnail source.")
    return str(path.parent / "thumbnails" / f"{path.stem}.webp")


def daily_report_thumbnail_storage_key(storage_key: str) -> str:
    """Return the deterministic gs:// key for a Daily Report thumbnail."""
    if not storage_key.startswith("gs://"):
        raise ValueError("Storage key must start with gs://")
    remainder = storage_key[5:]
    if "/" not in remainder:
        raise ValueError("Storage key must contain both bucket and object path.")
    bucket_name, object_name = remainder.split("/", 1)
    if not bucket_name or not object_name:
        raise ValueError("Storage key must contain both bucket and object path.")
    thumbnail_name = daily_report_thumbnail_object_name(object_name)
    return f"gs://{bucket_name}/{thumbnail_name}"


def create_daily_report_thumbnail(source_bytes: bytes) -> bytes:
    """Convert an image to a bounded, orientation-correct WebP thumbnail."""
    if not source_bytes:
        raise ValueError("Image bytes are required.")

    with Image.open(BytesIO(source_bytes)) as source:
        source.seek(0)
        width, height = source.size
        if width <= 0 or height <= 0 or width * height > MAX_SOURCE_PIXELS:
            raise ValueError("Image dimensions exceed the thumbnail safety limit.")

        image = ImageOps.exif_transpose(source).copy()

    image.thumbnail(
        (THUMBNAIL_MAX_DIMENSION, THUMBNAIL_MAX_DIMENSION),
        Image.Resampling.LANCZOS,
        reducing_gap=3.0,
    )
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")

    output = BytesIO()
    image.save(
        output,
        format="WEBP",
        quality=THUMBNAIL_QUALITY,
        method=6,
    )
    return output.getvalue()
