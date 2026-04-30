"""
Firestore-backed identity and directory operations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
import re
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.google_clients import get_firestore_client

USERS_COLLECTION = "users"
ADMINS_COLLECTION = "admins"


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _normalize_optional_text(value: object) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _normalize_project_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = _normalize_optional_text(item)
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    return normalized


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _email_doc_id(email: str) -> str:
    normalized = _normalize_email(email)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "admin"


def _to_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _datetime_value(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


@dataclass(slots=True)
class SubcontractorProfile:
    id: str
    line_uid: str | None
    line_picture_url: str | None
    profile_image_storage_key: str | None
    name: str
    contact_name: str | None
    phone: str | None
    tax_id: str | None
    assigned_project_ids: list[str]
    vat_rate: float
    wht_rate: float
    retention_rate: float
    bank_account: dict[str, str | None]
    kyc_gcs_path: str | None
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(slots=True)
class AdminDirectoryEntry:
    id: str
    email: str
    display_name: str | None
    is_active: bool
    granted_by: str | None
    created_at: datetime | None
    updated_at: datetime | None


def _subcontractor_from_dict(doc_id: str, payload: dict[str, Any]) -> SubcontractorProfile:
    return SubcontractorProfile(
        id=doc_id,
        line_uid=_normalize_optional_text(payload.get("line_uid")),
        line_picture_url=_normalize_optional_text(payload.get("line_picture_url")),
        profile_image_storage_key=_normalize_optional_text(payload.get("profile_image_storage_key")),
        name=str(payload.get("name") or doc_id),
        contact_name=_normalize_optional_text(payload.get("contact_name")),
        phone=_normalize_optional_text(payload.get("phone")),
        tax_id=_normalize_optional_text(payload.get("tax_id")),
        assigned_project_ids=_normalize_project_ids(payload.get("assigned_project_ids")),
        vat_rate=_to_float(payload.get("vat_rate"), 0.0),
        wht_rate=_to_float(payload.get("wht_rate"), 0.0),
        retention_rate=_to_float(payload.get("retention_rate"), 0.0),
        bank_account={
            "bank_name": _normalize_optional_text((payload.get("bank_account") or {}).get("bank_name")),
            "account_no": _normalize_optional_text((payload.get("bank_account") or {}).get("account_no")),
            "account_name": _normalize_optional_text((payload.get("bank_account") or {}).get("account_name")),
        },
        kyc_gcs_path=_normalize_optional_text(payload.get("kyc_gcs_path")),
        is_active=bool(payload.get("is_active", True)),
        created_at=_datetime_value(payload.get("created_at")),
        updated_at=_datetime_value(payload.get("updated_at")),
    )


def _admin_from_dict(doc_id: str, payload: dict[str, Any]) -> AdminDirectoryEntry:
    return AdminDirectoryEntry(
        id=doc_id,
        email=_normalize_email(str(payload.get("email") or "")),
        display_name=_normalize_optional_text(payload.get("display_name")),
        is_active=bool(payload.get("is_active", True)),
        granted_by=_normalize_optional_text(payload.get("granted_by")),
        created_at=_datetime_value(payload.get("created_at")),
        updated_at=_datetime_value(payload.get("updated_at")),
    )


def _ensure_firestore():
    return get_firestore_client()


def list_subcontractors() -> list[SubcontractorProfile]:
    client = _ensure_firestore()
    docs = client.collection(USERS_COLLECTION).stream()
    items = [
        _subcontractor_from_dict(doc.id, doc.to_dict() or {})
        for doc in docs
    ]
    return sorted(items, key=lambda item: item.name.lower())


def get_subcontractor(subcontractor_id: str) -> SubcontractorProfile:
    client = _ensure_firestore()
    snapshot = client.collection(USERS_COLLECTION).document(subcontractor_id).get()
    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontractor profile {subcontractor_id} not found.",
        )
    return _subcontractor_from_dict(snapshot.id, snapshot.to_dict() or {})


def get_subcontractor_by_line_uid(line_uid: str) -> SubcontractorProfile | None:
    client = _ensure_firestore()
    docs = (
        client.collection(USERS_COLLECTION)
        .where("line_uid", "==", line_uid)
        .limit(1)
        .stream()
    )
    snapshot = next(iter(docs), None)
    if snapshot is None:
        return None
    return _subcontractor_from_dict(snapshot.id, snapshot.to_dict() or {})


def create_subcontractor_profile(
    *,
    subcontractor_id: str,
    line_uid: str,
    line_picture_url: str | None,
    name: str,
    contact_name: str | None,
    phone: str | None,
    tax_id: str,
    kyc_gcs_path: str | None,
    bank_account: dict[str, str | None] | None = None,
) -> SubcontractorProfile:
    client = _ensure_firestore()
    now = _now_utc()
    normalized_bank_account = bank_account or {}
    payload = {
        "line_uid": line_uid,
        "line_picture_url": _normalize_optional_text(line_picture_url),
        "profile_image_storage_key": None,
        "name": name.strip(),
        "contact_name": _normalize_optional_text(contact_name) or name.strip(),
        "phone": _normalize_optional_text(phone),
        "tax_id": tax_id.strip(),
        "assigned_project_ids": [],
        "vat_rate": 0.07,
        "wht_rate": 0.03,
        "retention_rate": 0.05,
        "bank_account": {
            "bank_name": _normalize_optional_text(normalized_bank_account.get("bank_name")),
            "account_no": _normalize_optional_text(normalized_bank_account.get("account_no")),
            "account_name": _normalize_optional_text(normalized_bank_account.get("account_name")),
        },
        "kyc_gcs_path": kyc_gcs_path,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    client.collection(USERS_COLLECTION).document(subcontractor_id).set(payload)
    return _subcontractor_from_dict(subcontractor_id, payload)


def update_subcontractor_profile(
    subcontractor_id: str,
    *,
    updates: dict[str, Any],
) -> SubcontractorProfile:
    current = get_subcontractor(subcontractor_id)
    client = _ensure_firestore()

    payload: dict[str, Any] = {"updated_at": _now_utc()}
    if "name" in updates:
        payload["name"] = str(updates["name"]).strip()
    if "contact_name" in updates:
        payload["contact_name"] = _normalize_optional_text(updates["contact_name"])
    if "phone" in updates:
        payload["phone"] = _normalize_optional_text(updates["phone"])
    if "line_picture_url" in updates:
        payload["line_picture_url"] = _normalize_optional_text(updates["line_picture_url"])
    if "profile_image_storage_key" in updates:
        payload["profile_image_storage_key"] = _normalize_optional_text(updates["profile_image_storage_key"])
    if "tax_id" in updates:
        payload["tax_id"] = _normalize_optional_text(updates["tax_id"])
    if "assigned_project_ids" in updates:
        payload["assigned_project_ids"] = _normalize_project_ids(updates["assigned_project_ids"])
    if "vat_rate" in updates:
        payload["vat_rate"] = float(updates["vat_rate"])
    if "wht_rate" in updates:
        payload["wht_rate"] = float(updates["wht_rate"])
    if "retention_rate" in updates:
        payload["retention_rate"] = float(updates["retention_rate"])
    if "bank_account" in updates and isinstance(updates["bank_account"], dict):
        payload["bank_account"] = {
            "bank_name": _normalize_optional_text(updates["bank_account"].get("bank_name")),
            "account_no": _normalize_optional_text(updates["bank_account"].get("account_no")),
            "account_name": _normalize_optional_text(updates["bank_account"].get("account_name")),
        }
    if "is_active" in updates:
        payload["is_active"] = bool(updates["is_active"])

    client.collection(USERS_COLLECTION).document(subcontractor_id).set(payload, merge=True)
    merged = asdict(current)
    merged.update(payload)
    return _subcontractor_from_dict(subcontractor_id, merged)


def reset_subcontractor_line_binding(subcontractor_id: str) -> SubcontractorProfile:
    current = get_subcontractor(subcontractor_id)
    client = _ensure_firestore()
    payload = {
        "line_uid": None,
        "updated_at": _now_utc(),
    }
    client.collection(USERS_COLLECTION).document(subcontractor_id).set(payload, merge=True)
    merged = asdict(current)
    merged.update(payload)
    return _subcontractor_from_dict(subcontractor_id, merged)


def get_subcontractor_financial_rates(subcontractor_id: str) -> dict[str, Decimal]:
    profile = get_subcontractor(subcontractor_id)
    return {
        "vat_rate": Decimal(str(profile.vat_rate)),
        "wht_rate": Decimal(str(profile.wht_rate)),
        "retention_rate": Decimal(str(profile.retention_rate)),
    }


def get_kyc_storage_key(subcontractor_id: str) -> str:
    profile = get_subcontractor(subcontractor_id)
    if not profile.kyc_gcs_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subcontractor {subcontractor_id} does not have a KYC file.",
        )
    return profile.kyc_gcs_path


def list_admins() -> list[AdminDirectoryEntry]:
    client = _ensure_firestore()
    docs = client.collection(ADMINS_COLLECTION).stream()
    items = [
        _admin_from_dict(doc.id, doc.to_dict() or {})
        for doc in docs
    ]
    return sorted(items, key=lambda item: item.email)


def has_any_managed_admins() -> bool:
    client = _ensure_firestore()
    docs = client.collection(ADMINS_COLLECTION).limit(1).stream()
    return next(iter(docs), None) is not None


def get_admin_by_email(email: str) -> AdminDirectoryEntry | None:
    client = _ensure_firestore()
    snapshot = client.collection(ADMINS_COLLECTION).document(_email_doc_id(email)).get()
    if not snapshot.exists:
        return None
    return _admin_from_dict(snapshot.id, snapshot.to_dict() or {})


def upsert_admin(
    *,
    email: str,
    display_name: str | None,
    is_active: bool,
    granted_by: str | None,
) -> AdminDirectoryEntry:
    client = _ensure_firestore()
    normalized_email = _normalize_email(email)
    doc_id = _email_doc_id(normalized_email)
    existing = get_admin_by_email(normalized_email)
    now = _now_utc()
    payload = {
        "email": normalized_email,
        "display_name": _normalize_optional_text(display_name),
        "is_active": bool(is_active),
        "granted_by": _normalize_optional_text(granted_by),
        "updated_at": now,
    }
    if existing is None:
        payload["created_at"] = now
    client.collection(ADMINS_COLLECTION).document(doc_id).set(payload, merge=True)
    if existing is not None:
        merged = asdict(existing)
        merged.update(payload)
        return _admin_from_dict(doc_id, merged)
    return _admin_from_dict(doc_id, payload)


def update_admin(doc_id: str, *, updates: dict[str, Any]) -> AdminDirectoryEntry:
    client = _ensure_firestore()
    snapshot = client.collection(ADMINS_COLLECTION).document(doc_id).get()
    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin record {doc_id} not found.",
        )

    current = _admin_from_dict(snapshot.id, snapshot.to_dict() or {})
    payload: dict[str, Any] = {"updated_at": _now_utc()}
    if "display_name" in updates:
        payload["display_name"] = _normalize_optional_text(updates["display_name"])
    if "is_active" in updates:
        payload["is_active"] = bool(updates["is_active"])

    client.collection(ADMINS_COLLECTION).document(doc_id).set(payload, merge=True)
    merged = asdict(current)
    merged.update(payload)
    return _admin_from_dict(doc_id, merged)


def is_email_authorized_admin(email: str) -> bool:
    normalized_email = _normalize_email(email)
    managed_admin = get_admin_by_email(normalized_email)
    if managed_admin is not None:
        return managed_admin.is_active

    settings = get_settings()
    if normalized_email in settings.admin_emails:
        return True

    if has_any_managed_admins():
        return False

    domain = settings.admin_email_domain
    return bool(domain and normalized_email.endswith(f"@{domain}"))


def ensure_bootstrap_admin(email: str, display_name: str | None) -> AdminDirectoryEntry | None:
    if not is_email_authorized_admin(email):
        return None

    existing = get_admin_by_email(email)
    if existing is not None:
        return existing

    settings = get_settings()
    normalized_email = _normalize_email(email)
    if normalized_email in settings.admin_emails or (
        settings.admin_email_domain and normalized_email.endswith(f"@{settings.admin_email_domain}")
    ):
        return upsert_admin(
            email=normalized_email,
            display_name=display_name,
            is_active=True,
            granted_by="bootstrap",
        )
    return None
