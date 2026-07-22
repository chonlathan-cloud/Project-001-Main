from __future__ import annotations

import unittest
from io import BytesIO

from PIL import Image

from app.services.daily_report_thumbnail_service import (
    THUMBNAIL_MAX_DIMENSION,
    create_daily_report_thumbnail,
    daily_report_thumbnail_object_name,
    daily_report_thumbnail_storage_key,
)


class DailyReportThumbnailServiceTests(unittest.TestCase):
    def test_thumbnail_key_is_stored_beside_original_in_thumbnail_folder(self):
        object_name = "daily_reports/project/date/submission/media-site-photo.jpeg"

        self.assertEqual(
            daily_report_thumbnail_object_name(object_name),
            "daily_reports/project/date/submission/thumbnails/media-site-photo.webp",
        )
        self.assertEqual(
            daily_report_thumbnail_storage_key(f"gs://private-bucket/{object_name}"),
            "gs://private-bucket/daily_reports/project/date/submission/thumbnails/media-site-photo.webp",
        )

    def test_thumbnail_rejects_an_existing_thumbnail_as_source(self):
        with self.assertRaises(ValueError):
            daily_report_thumbnail_object_name(
                "daily_reports/project/date/submission/thumbnails/photo.webp"
            )

    def test_thumbnail_is_webp_and_respects_maximum_dimension(self):
        source = BytesIO()
        Image.new("RGB", (2400, 1600), color=(82, 112, 101)).save(
            source,
            format="JPEG",
            quality=90,
        )

        thumbnail_bytes = create_daily_report_thumbnail(source.getvalue())

        with Image.open(BytesIO(thumbnail_bytes)) as thumbnail:
            self.assertEqual(thumbnail.format, "WEBP")
            self.assertLessEqual(max(thumbnail.size), THUMBNAIL_MAX_DIMENSION)
            self.assertEqual(thumbnail.size, (1280, 853))


if __name__ == "__main__":
    unittest.main()
