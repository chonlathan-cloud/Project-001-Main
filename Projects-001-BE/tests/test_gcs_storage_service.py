from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import UUID

from google.auth import credentials as google_auth_credentials

from app.services import gcs_storage_service


class FakeSigningCredentials(google_auth_credentials.Signing):
    @property
    def signer(self):
        return None

    @property
    def signer_email(self):
        return "local-signer@example.iam.gserviceaccount.com"

    def sign_bytes(self, _message):
        return b"local-signature"


class FakeTokenCredentials:
    def __init__(
        self,
        *,
        service_account_email: str = "default",
        token: str | None = None,
        valid: bool = False,
    ):
        self.service_account_email = service_account_email
        self.token = token
        self.valid = valid
        self.refresh_count = 0

    def refresh(self, _request):
        self.refresh_count += 1
        self.service_account_email = "runtime@example.iam.gserviceaccount.com"
        self.token = "test-access-token"
        self.valid = True


def build_storage_client(credentials):
    blob = MagicMock()
    blob.generate_signed_url.return_value = "https://storage.example/signed"
    bucket = MagicMock()
    bucket.blob.return_value = blob
    client = MagicMock()
    client._credentials = credentials
    client.bucket.return_value = bucket
    return client, bucket, blob


class GcsStorageServiceTests(unittest.TestCase):
    def setUp(self):
        gcs_storage_service._iam_signing_credentials = None

    def tearDown(self):
        gcs_storage_service._iam_signing_credentials = None

    def test_signed_url_uses_existing_local_signer_without_iam_arguments(self):
        client, bucket, blob = build_storage_client(FakeSigningCredentials())

        with (
            patch.object(gcs_storage_service, "_require_storage_client", return_value=client),
            patch.object(gcs_storage_service, "google_auth_default") as auth_default,
        ):
            result = gcs_storage_service._generate_signed_url_for_storage_key_sync(
                storage_key="gs://private-bucket/receipts/example.pdf",
                expires_in_minutes=15,
            )

        self.assertEqual(result, "https://storage.example/signed")
        client.bucket.assert_called_once_with("private-bucket")
        bucket.blob.assert_called_once_with("receipts/example.pdf")
        signing_call = blob.generate_signed_url.call_args.kwargs
        self.assertNotIn("service_account_email", signing_call)
        self.assertNotIn("access_token", signing_call)
        auth_default.assert_not_called()

    def test_signed_url_uses_keyless_iam_signing_for_cloud_run_credentials(self):
        storage_credentials = FakeTokenCredentials()
        iam_credentials = FakeTokenCredentials()
        client, _bucket, blob = build_storage_client(storage_credentials)

        with (
            patch.object(gcs_storage_service, "_require_storage_client", return_value=client),
            patch.object(
                gcs_storage_service,
                "google_auth_default",
                return_value=(iam_credentials, "project001-489710"),
            ) as auth_default,
        ):
            result = gcs_storage_service._generate_signed_url_for_storage_key_sync(
                storage_key="gs://private-bucket/receipts/example.pdf",
                expires_in_minutes=20,
            )

        self.assertEqual(result, "https://storage.example/signed")
        auth_default.assert_called_once_with(
            scopes=[gcs_storage_service._CLOUD_PLATFORM_SCOPE]
        )
        self.assertEqual(storage_credentials.refresh_count, 0)
        self.assertEqual(iam_credentials.refresh_count, 1)
        blob.generate_signed_url.assert_called_once_with(
            version="v4",
            expiration=gcs_storage_service.timedelta(minutes=20),
            method="GET",
            service_account_email="runtime@example.iam.gserviceaccount.com",
            access_token="test-access-token",
        )

    def test_keyless_signing_fails_safely_when_identity_cannot_be_resolved(self):
        storage_credentials = FakeTokenCredentials()
        iam_credentials = FakeTokenCredentials()

        def incomplete_refresh(_request):
            iam_credentials.refresh_count += 1
            iam_credentials.token = "test-access-token"
            iam_credentials.valid = True

        iam_credentials.refresh = incomplete_refresh
        client, _bucket, blob = build_storage_client(storage_credentials)

        with (
            patch.object(gcs_storage_service, "_require_storage_client", return_value=client),
            patch.object(
                gcs_storage_service,
                "google_auth_default",
                return_value=(iam_credentials, "project001-489710"),
            ),
            self.assertRaisesRegex(RuntimeError, "cannot sign GCS URLs"),
        ):
            gcs_storage_service._generate_signed_url_for_storage_key_sync(
                storage_key="gs://private-bucket/receipts/example.pdf",
                expires_in_minutes=15,
            )

        blob.generate_signed_url.assert_not_called()

    def test_keyless_signing_reuses_valid_cached_iam_credentials(self):
        storage_credentials = FakeTokenCredentials()
        iam_credentials = FakeTokenCredentials(
            service_account_email="runtime@example.iam.gserviceaccount.com",
            token="cached-access-token",
            valid=True,
        )
        client, _bucket, blob = build_storage_client(storage_credentials)

        with (
            patch.object(gcs_storage_service, "_require_storage_client", return_value=client),
            patch.object(
                gcs_storage_service,
                "google_auth_default",
                return_value=(iam_credentials, "project001-489710"),
            ) as auth_default,
        ):
            for _ in range(2):
                gcs_storage_service._generate_signed_url_for_storage_key_sync(
                    storage_key="gs://private-bucket/receipts/example.pdf",
                    expires_in_minutes=15,
                )

        auth_default.assert_called_once_with(
            scopes=[gcs_storage_service._CLOUD_PLATFORM_SCOPE]
        )
        self.assertEqual(iam_credentials.refresh_count, 0)
        self.assertEqual(blob.generate_signed_url.call_count, 2)

    def test_paid_documents_share_reference_folder(self):
        prefix = gcs_storage_service._paid_document_prefix(
            date(2026, 6, 27),
            "E00127062026",
        )
        original = gcs_storage_service._build_paid_original_object_name(
            request_id=UUID("11111111-1111-1111-1111-111111111111"),
            source_object_name="perm_bills/old/source-invoice.pdf",
            payment_date=date(2026, 6, 27),
            internal_reference="E00127062026",
        )
        confirmation = gcs_storage_service._build_payment_confirmation_object_name(
            payment_date=date(2026, 6, 27),
            internal_reference="E00127062026",
            confirmation_id=UUID("22222222-2222-2222-2222-222222222222"),
            version=1,
            file_name="received.jpg",
        )

        self.assertEqual(prefix, "perm_bills/paid/2026/06/27/E00127062026")
        self.assertTrue(original.startswith(f"{prefix}/original/"))
        self.assertTrue(confirmation.startswith(f"{prefix}/payment_confirmation/"))

    def test_paid_receipt_copy_keeps_source_until_database_commit(self):
        source_blob = MagicMock()
        source_blob.exists.return_value = True
        target_blob = MagicMock()
        target_blob.exists.return_value = False
        bucket = MagicMock()
        bucket.blob.side_effect = [source_blob, target_blob]
        client = MagicMock()
        client.bucket.return_value = bucket

        with (
            patch.object(
                gcs_storage_service,
                "get_default_bucket_name",
                return_value="private-bucket",
            ),
            patch.object(
                gcs_storage_service,
                "_require_storage_client",
                return_value=client,
            ),
        ):
            result = gcs_storage_service._organize_input_receipt_in_paid_storage_sync(
                storage_key="gs://private-bucket/perm_bills/2026/07/22/source.jpg",
                request_id=UUID("11111111-1111-1111-1111-111111111111"),
                payment_date=date(2026, 7, 24),
                internal_reference="E00124072026",
            )

        self.assertTrue(
            result.startswith(
                "gs://private-bucket/perm_bills/paid/2026/07/24/"
                "E00124072026/original/"
            )
        )
        bucket.copy_blob.assert_called_once()
        source_blob.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
