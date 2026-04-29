"""
Lazy Google/Firebase client helpers.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    from firebase_admin import credentials
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    firebase_admin = None  # type: ignore[assignment]
    firebase_auth = None  # type: ignore[assignment]
    credentials = None  # type: ignore[assignment]
    _FIREBASE_IMPORT_ERROR = exc
else:
    _FIREBASE_IMPORT_ERROR = None

try:
    from google.cloud import firestore
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    firestore = None  # type: ignore[assignment]
    _FIRESTORE_IMPORT_ERROR = exc
else:
    _FIRESTORE_IMPORT_ERROR = None


def _maybe_build_firebase_credential():
    settings = get_settings()
    credentials_path = (settings.google_application_credentials or "").strip()
    if credentials_path:
        resolved_path = Path(credentials_path).expanduser()
        if resolved_path.exists():
            return credentials.Certificate(str(resolved_path))
    return credentials.ApplicationDefault()


@lru_cache(maxsize=1)
def get_firebase_app():
    if firebase_admin is None or firebase_auth is None or credentials is None:
        raise RuntimeError(
            "firebase-admin is not installed. Install backend dependencies first."
        ) from _FIREBASE_IMPORT_ERROR

    if firebase_admin._apps:  # type: ignore[attr-defined]
        return firebase_admin.get_app()

    settings = get_settings()
    options = {}
    if settings.firebase_storage_bucket:
        options["storageBucket"] = settings.firebase_storage_bucket
    if settings.firebase_project_id:
        options["projectId"] = settings.firebase_project_id

    credential = _maybe_build_firebase_credential()
    return firebase_admin.initialize_app(credential=credential, options=options)


def get_firebase_auth():
    _ = get_firebase_app()
    if firebase_auth is None:
        raise RuntimeError("firebase-admin auth is unavailable.") from _FIREBASE_IMPORT_ERROR
    return firebase_auth


@lru_cache(maxsize=1)
def get_firestore_client():
    if firestore is None:
        raise RuntimeError(
            "google-cloud-firestore is not installed. Install backend dependencies first."
        ) from _FIRESTORE_IMPORT_ERROR

    settings = get_settings()
    client_kwargs = {}
    if settings.firebase_project_id:
        client_kwargs["project"] = settings.firebase_project_id
    return firestore.Client(**client_kwargs)
