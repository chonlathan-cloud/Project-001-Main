"""Create missing WebP thumbnails for existing Daily Report images in GCS.

The script is dry-run by default. An execute run requires both ``--execute`` and
``--expected-count`` so an unexpected prefix cannot silently process more data.
It prints aggregate metadata only and never prints object contents or signed URLs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.daily_report_thumbnail_service import (  # noqa: E402
    THUMBNAIL_CACHE_CONTROL,
    create_daily_report_thumbnail,
    daily_report_thumbnail_object_name,
)

IMAGE_SUFFIXES = {".gif", ".heic", ".heif", ".jpeg", ".jpg", ".png", ".webp"}


def _is_source_image(blob) -> bool:
    path = Path(blob.name)
    if "thumbnails" in path.parts:
        return False
    return str(blob.content_type or "").startswith("image/") or path.suffix.lower() in IMAGE_SUFFIXES


def _format_mib(size_bytes: int) -> str:
    return f"{size_bytes / (1024 * 1024):.2f} MiB"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="project001-489710")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="daily_reports/")
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.execute and args.expected_count is None:
        raise SystemExit("--execute requires --expected-count")
    if args.expected_count is not None and args.expected_count < 0:
        raise SystemExit("--expected-count must be zero or greater")

    client = storage.Client(project=args.project)
    bucket = client.bucket(args.bucket)
    source_blobs = [
        blob
        for blob in client.list_blobs(bucket, prefix=args.prefix)
        if _is_source_image(blob)
    ]
    source_bytes = sum(int(blob.size or 0) for blob in source_blobs)

    if args.expected_count is not None and len(source_blobs) != args.expected_count:
        print(
            "Safety check failed: "
            f"expected {args.expected_count} source images, found {len(source_blobs)}."
        )
        return 2

    pending = []
    existing_count = 0
    for source_blob in source_blobs:
        thumbnail_name = daily_report_thumbnail_object_name(source_blob.name)
        thumbnail_blob = bucket.blob(thumbnail_name)
        if not args.force and thumbnail_blob.exists(client):
            existing_count += 1
            continue
        pending.append((source_blob, thumbnail_blob))

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(
        f"Mode: {mode}; source images: {len(source_blobs)}; "
        f"source size: {_format_mib(source_bytes)}; existing thumbnails: {existing_count}; "
        f"pending: {len(pending)}"
    )
    if not args.execute:
        print("No GCS objects were changed. Re-run with --execute --expected-count N to write thumbnails.")
        return 0

    created_count = 0
    skipped_race_count = 0
    failed_count = 0
    thumbnail_bytes_total = 0
    for index, (source_blob, thumbnail_blob) in enumerate(pending, start=1):
        try:
            original_bytes = source_blob.download_as_bytes(
                if_generation_match=source_blob.generation,
            )
            thumbnail_bytes = create_daily_report_thumbnail(original_bytes)
            thumbnail_blob.cache_control = THUMBNAIL_CACHE_CONTROL
            thumbnail_blob.metadata = {
                "derived_from_generation": str(source_blob.generation or ""),
                "variant": "daily-report-thumbnail",
            }
            upload_options = {}
            if not args.force:
                upload_options["if_generation_match"] = 0
            thumbnail_blob.upload_from_string(
                thumbnail_bytes,
                content_type="image/webp",
                **upload_options,
            )
            created_count += 1
            thumbnail_bytes_total += len(thumbnail_bytes)
        except PreconditionFailed:
            skipped_race_count += 1
        except Exception as exc:  # Continue so the summary exposes partial failures.
            failed_count += 1
            print(f"Item {index} failed: {type(exc).__name__}")

    print(
        f"Created: {created_count}; race-skipped: {skipped_race_count}; "
        f"failed: {failed_count}; thumbnail size: {_format_mib(thumbnail_bytes_total)}"
    )
    return 1 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
