from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

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


if __name__ == "__main__":
    unittest.main()
