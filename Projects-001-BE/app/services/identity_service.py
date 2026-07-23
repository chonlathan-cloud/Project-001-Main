"""
Firestore-backed identity and directory operations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import re
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.google_clients import get_firestore_client

USERS_COLLECTION = "users"
ADMINS_COLLECTION = "admins"
ACCESS_REQUESTS_COLLECTION = "access_requests"
CUSTOMERS_COLLECTION = "customers"
OWNER_ROLE = "owner"
ADMIN_ROLE = "admin"
INSPECTOR_ROLE = "inspector"
SUBCONTRACTOR_ROLE = "subcontractor"
CUSTOMER_ROLE = "customer"
PENDING_ROLE = "pending"
ADMIN_ROLES = {OWNER_ROLE, ADMIN_ROLE, INSPECTOR_ROLE}
ADMIN_ACCESS_ROLES = {OWNER_ROLE, ADMIN_ROLE}
ACCESS_REQUEST_STATUSES = {"pending", "approved", "rejected"}
ACCESS_REQUEST_PROVIDERS = {"google", "line"}


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


def _normalize_provider(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    return cleaned if cleaned in ACCESS_REQUEST_PROVIDERS else "google"


def _normalize_access_status(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    return cleaned if cleaned in ACCESS_REQUEST_STATUSES else "pending"


def _normalize_admin_role(value: object, *, default: str = ADMIN_ROLE) -> str:
    cleaned = str(value or "").strip().lower()
    if not cleaned:
        return default
    if cleaned not in ADMIN_ROLES:
        return default
    return cleaned


def _normalize_admin_roles(value: object, *, default_role: str = ADMIN_ROLE) -> list[str]:
    raw_values = value if isinstance(value, list) else []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_values:
        cleaned = str(item or "").strip().lower()
        if cleaned in ADMIN_ROLES and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)

    if normalized:
        return normalized

    fallback = _normalize_admin_role(default_role)
    return [fallback]


def _primary_role_for_roles(roles: list[str]) -> str:
    if OWNER_ROLE in roles:
        return OWNER_ROLE
    if ADMIN_ROLE in roles:
        return ADMIN_ROLE
    if INSPECTOR_ROLE in roles:
        return INSPECTOR_ROLE
    return ADMIN_ROLE


def _email_doc_id(email: str) -> str:
    normalized = _normalize_email(email)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "admin"


def _stable_doc_id(prefix: str, value: str) -> str:
    cleaned_prefix = re.sub(r"[^a-z0-9]+", "-", str(prefix or "item").lower()).strip("-") or "item"
    digest = hashlib.sha1(str(value or cleaned_prefix).strip().lower().encode("utf-8")).hexdigest()[:16]
    return f"{cleaned_prefix}-{digest}"


def access_request_doc_id(
    *,
    provider: str,
    email: str | None = None,
    line_uid: str | None = None,
    account_type: str | None = None,
) -> str:
    normalized_provider = _normalize_provider(provider)
    if normalized_provider == "google":
        return f"google-{_email_doc_id(email or '')}"
    scope = str(account_type or "").strip().lower()
    prefix = f"line-{scope}" if scope == CUSTOMER_ROLE else "line"
    return _stable_doc_id(prefix, line_uid or email or normalized_provider)


def subcontractor_doc_id_for_identity(*, email: str | None = None, line_uid: str | None = None) -> str:
    identity = _normalize_email(email or "") or str(line_uid or "").strip()
    return _stable_doc_id("sub", identity or "subcontractor")


def admin_doc_id_for_email(email: str) -> str:
    return _email_doc_id(email)


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
    email: str | None
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
    contact_name: str | None
    phone: str | None
    bank_account: dict[str, str | None]
    company: str | None
    department: str | None
    time: str | None
    profile_image_storage_key: str | None
    role: str
    roles: list[str]
    is_active: bool
    granted_by: str | None
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(slots=True)
class CustomerProfile:
    id: str
    email: str | None
    line_uid: str | None
    line_picture_url: str | None
    name: str
    first_name: str | None
    nickname: str | None
    contact_name: str | None
    phone: str | None
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(slots=True)
class AccessRequest:
    id: str
    provider: str
    email: str | None
    line_uid: str | None
    display_name: str | None
    picture_url: str | None
    status: str
    requested_account_type: str | None
    company_name: str | None
    first_name: str | None
    nickname: str | None
    contact_name: str | None
    phone: str | None
    tax_id: str | None
    bank_account: dict[str, str | None]
    kyc_gcs_path: str | None
    decided_account_type: str | None
    decided_role: str | None
    decided_roles: list[str]
    target_admin_id: str | None
    target_subcontractor_id: str | None
    target_customer_id: str | None
    rejection_reason: str | None
    decided_by: str | None
    created_at: datetime | None
    updated_at: datetime | None
    decided_at: datetime | None
    review_history: list[dict[str, Any]]


def _subcontractor_from_dict(doc_id: str, payload: dict[str, Any]) -> SubcontractorProfile:
    return SubcontractorProfile(
        id=doc_id,
        email=_normalize_email(str(payload.get("email") or "")) or None,
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
    primary_role = _normalize_admin_role(payload.get("role"), default=OWNER_ROLE)
    roles = _normalize_admin_roles(payload.get("roles"), default_role=primary_role)
    primary_role = _primary_role_for_roles(roles)
    return AdminDirectoryEntry(
        id=doc_id,
        email=_normalize_email(str(payload.get("email") or "")),
        display_name=_normalize_optional_text(payload.get("display_name")),
        contact_name=_normalize_optional_text(payload.get("contact_name")),
        phone=_normalize_optional_text(payload.get("phone")),
        bank_account={
            "bank_name": _normalize_optional_text((payload.get("bank_account") or {}).get("bank_name")),
            "account_no": _normalize_optional_text((payload.get("bank_account") or {}).get("account_no")),
            "account_name": _normalize_optional_text((payload.get("bank_account") or {}).get("account_name")),
        },
        company=_normalize_optional_text(payload.get("company")),
        department=_normalize_optional_text(payload.get("department")),
        time=_normalize_optional_text(payload.get("time")),
        profile_image_storage_key=_normalize_optional_text(payload.get("profile_image_storage_key")),
        # Existing managed admin records predate role support. Treat them as
        # owners so old full-access admins do not silently lose permissions.
        role=primary_role,
        roles=roles,
        is_active=bool(payload.get("is_active", True)),
        granted_by=_normalize_optional_text(payload.get("granted_by")),
        created_at=_datetime_value(payload.get("created_at")),
        updated_at=_datetime_value(payload.get("updated_at")),
    )


def _access_request_from_dict(doc_id: str, payload: dict[str, Any]) -> AccessRequest:
    bank_account = payload.get("bank_account") if isinstance(payload.get("bank_account"), dict) else {}
    decided_account_type = _normalize_optional_text(payload.get("decided_account_type"))
    return AccessRequest(
        id=doc_id,
        provider=_normalize_provider(payload.get("provider")),
        email=_normalize_email(str(payload.get("email") or "")) or None,
        line_uid=_normalize_optional_text(payload.get("line_uid")),
        display_name=_normalize_optional_text(payload.get("display_name")),
        picture_url=_normalize_optional_text(payload.get("picture_url")),
        status=_normalize_access_status(payload.get("status")),
        requested_account_type=_normalize_optional_text(payload.get("requested_account_type")),
        company_name=_normalize_optional_text(payload.get("company_name")),
        first_name=_normalize_optional_text(payload.get("first_name")),
        nickname=_normalize_optional_text(payload.get("nickname")),
        contact_name=_normalize_optional_text(payload.get("contact_name")),
        phone=_normalize_optional_text(payload.get("phone")),
        tax_id=_normalize_optional_text(payload.get("tax_id")),
        bank_account={
            "bank_name": _normalize_optional_text(bank_account.get("bank_name")),
            "account_no": _normalize_optional_text(bank_account.get("account_no")),
            "account_name": _normalize_optional_text(bank_account.get("account_name")),
        },
        kyc_gcs_path=_normalize_optional_text(payload.get("kyc_gcs_path")),
        decided_account_type=decided_account_type,
        decided_role=_normalize_optional_text(payload.get("decided_role")),
        decided_roles=_normalize_admin_roles(payload.get("decided_roles"), default_role=payload.get("decided_role"))
        if decided_account_type == "admin" and (payload.get("decided_roles") or payload.get("decided_role"))
        else [],
        target_admin_id=_normalize_optional_text(payload.get("target_admin_id")),
        target_subcontractor_id=_normalize_optional_text(payload.get("target_subcontractor_id")),
        target_customer_id=_normalize_optional_text(payload.get("target_customer_id")),
        rejection_reason=_normalize_optional_text(payload.get("rejection_reason")),
        decided_by=_normalize_optional_text(payload.get("decided_by")),
        created_at=_datetime_value(payload.get("created_at")),
        updated_at=_datetime_value(payload.get("updated_at")),
        decided_at=_datetime_value(payload.get("decided_at")),
        review_history=[
            dict(item)
            for item in (payload.get("review_history") or [])
            if isinstance(item, dict)
        ],
    )


def _customer_from_dict(doc_id: str, payload: dict[str, Any]) -> CustomerProfile:
    return CustomerProfile(
        id=doc_id,
        email=_normalize_email(str(payload.get("email") or "")) or None,
        line_uid=_normalize_optional_text(payload.get("line_uid")),
        line_picture_url=_normalize_optional_text(payload.get("line_picture_url")),
        name=str(payload.get("name") or doc_id),
        first_name=(
            _normalize_optional_text(payload.get("first_name"))
            or _normalize_optional_text(payload.get("contact_name"))
            or _normalize_optional_text(payload.get("name"))
        ),
        nickname=_normalize_optional_text(payload.get("nickname")),
        contact_name=_normalize_optional_text(payload.get("contact_name")),
        phone=_normalize_optional_text(payload.get("phone")),
        is_active=bool(payload.get("is_active", True)),
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


def get_subcontractor_by_email(email: str) -> SubcontractorProfile | None:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None
    client = _ensure_firestore()
    docs = (
        client.collection(USERS_COLLECTION)
        .where("email", "==", normalized_email)
        .limit(1)
        .stream()
    )
    snapshot = next(iter(docs), None)
    if snapshot is None:
        return None
    return _subcontractor_from_dict(snapshot.id, snapshot.to_dict() or {})


def customer_doc_id_for_identity(*, email: str | None = None, line_uid: str | None = None) -> str:
    identity = _normalize_email(email or "") or str(line_uid or "").strip()
    return _stable_doc_id("customer", identity or "customer")


def get_customer(customer_id: str) -> CustomerProfile:
    snapshot = _ensure_firestore().collection(CUSTOMERS_COLLECTION).document(customer_id).get()
    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer profile {customer_id} not found.",
        )
    return _customer_from_dict(snapshot.id, snapshot.to_dict() or {})


def list_customers() -> list[CustomerProfile]:
    docs = _ensure_firestore().collection(CUSTOMERS_COLLECTION).stream()
    items = [
        _customer_from_dict(doc.id, doc.to_dict() or {})
        for doc in docs
    ]
    return sorted(items, key=lambda item: (item.contact_name or item.name).lower())


def get_customer_by_line_uid(line_uid: str) -> CustomerProfile | None:
    docs = (
        _ensure_firestore()
        .collection(CUSTOMERS_COLLECTION)
        .where("line_uid", "==", line_uid)
        .limit(1)
        .stream()
    )
    snapshot = next(iter(docs), None)
    return _customer_from_dict(snapshot.id, snapshot.to_dict() or {}) if snapshot else None


def create_customer_profile(
    *,
    customer_id: str,
    email: str | None,
    line_uid: str | None,
    line_picture_url: str | None,
    name: str,
    contact_name: str | None,
    phone: str | None,
    first_name: str | None = None,
    nickname: str | None = None,
) -> CustomerProfile:
    now = _now_utc()
    normalized_first_name = (
        _normalize_optional_text(first_name)
        or _normalize_optional_text(contact_name)
        or name.strip()
    )
    payload = {
        "email": _normalize_email(email or "") or None,
        "line_uid": _normalize_optional_text(line_uid),
        "line_picture_url": _normalize_optional_text(line_picture_url),
        "name": name.strip(),
        "first_name": normalized_first_name,
        "nickname": _normalize_optional_text(nickname),
        "contact_name": _normalize_optional_text(contact_name) or normalized_first_name,
        "phone": _normalize_optional_text(phone),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    _ensure_firestore().collection(CUSTOMERS_COLLECTION).document(customer_id).set(payload)
    return _customer_from_dict(customer_id, payload)


def update_customer_profile(
    customer_id: str,
    *,
    updates: dict[str, Any],
) -> CustomerProfile:
    current = get_customer(customer_id)
    payload: dict[str, Any] = {"updated_at": _now_utc()}
    if "name" in updates:
        cleaned_name = str(updates["name"] or "").strip()
        payload["name"] = cleaned_name or current.name
    if "first_name" in updates:
        payload["first_name"] = _normalize_optional_text(updates["first_name"])
    if "nickname" in updates:
        payload["nickname"] = _normalize_optional_text(updates["nickname"])
    if "contact_name" in updates:
        payload["contact_name"] = _normalize_optional_text(updates["contact_name"])
    if "phone" in updates:
        payload["phone"] = _normalize_optional_text(updates["phone"])
    if "is_active" in updates:
        payload["is_active"] = bool(updates["is_active"])

    _ensure_firestore().collection(CUSTOMERS_COLLECTION).document(customer_id).set(
        payload,
        merge=True,
    )
    merged = asdict(current)
    merged.update(payload)
    return _customer_from_dict(customer_id, merged)


def reset_customer_line_binding(customer_id: str) -> CustomerProfile:
    current = get_customer(customer_id)
    payload = {
        "line_uid": None,
        "updated_at": _now_utc(),
    }
    _ensure_firestore().collection(CUSTOMERS_COLLECTION).document(customer_id).set(
        payload,
        merge=True,
    )
    merged = asdict(current)
    merged.update(payload)
    return _customer_from_dict(customer_id, merged)


def create_subcontractor_profile(
    *,
    subcontractor_id: str,
    line_uid: str | None,
    line_picture_url: str | None,
    name: str,
    contact_name: str | None,
    phone: str | None,
    tax_id: str | None,
    kyc_gcs_path: str | None,
    bank_account: dict[str, str | None] | None = None,
    email: str | None = None,
) -> SubcontractorProfile:
    client = _ensure_firestore()
    now = _now_utc()
    normalized_bank_account = bank_account or {}
    payload = {
        "email": _normalize_email(email or "") or None,
        "line_uid": _normalize_optional_text(line_uid),
        "line_picture_url": _normalize_optional_text(line_picture_url),
        "profile_image_storage_key": None,
        "name": name.strip(),
        "contact_name": _normalize_optional_text(contact_name) or name.strip(),
        "phone": _normalize_optional_text(phone),
        "tax_id": _normalize_optional_text(tax_id),
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
    if "email" in updates:
        payload["email"] = _normalize_email(str(updates["email"] or "")) or None
    if "line_uid" in updates:
        payload["line_uid"] = _normalize_optional_text(updates["line_uid"])
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
    if "kyc_gcs_path" in updates:
        payload["kyc_gcs_path"] = _normalize_optional_text(updates["kyc_gcs_path"])
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


def _normalized_bank_account_payload(value: dict[str, Any] | None) -> dict[str, str | None]:
    value = value or {}
    return {
        "bank_name": _normalize_optional_text(value.get("bank_name")),
        "account_no": _normalize_optional_text(value.get("account_no")),
        "account_name": _normalize_optional_text(value.get("account_name")),
    }


def get_access_request(request_id: str) -> AccessRequest:
    client = _ensure_firestore()
    snapshot = client.collection(ACCESS_REQUESTS_COLLECTION).document(request_id).get()
    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Access request {request_id} not found.",
        )
    return _access_request_from_dict(snapshot.id, snapshot.to_dict() or {})


def get_access_request_by_identity(
    *,
    provider: str,
    email: str | None = None,
    line_uid: str | None = None,
    account_type: str | None = None,
) -> AccessRequest | None:
    doc_id = access_request_doc_id(
        provider=provider,
        email=email,
        line_uid=line_uid,
        account_type=account_type,
    )
    client = _ensure_firestore()
    snapshot = client.collection(ACCESS_REQUESTS_COLLECTION).document(doc_id).get()
    if not snapshot.exists:
        return None
    return _access_request_from_dict(snapshot.id, snapshot.to_dict() or {})


def list_access_requests(status_filter: str | None = None) -> list[AccessRequest]:
    client = _ensure_firestore()
    query = client.collection(ACCESS_REQUESTS_COLLECTION)
    normalized_status = _normalize_optional_text(status_filter)
    if normalized_status and normalized_status.lower() != "all":
        query = query.where("status", "==", _normalize_access_status(normalized_status))
    items = [
        _access_request_from_dict(doc.id, doc.to_dict() or {})
        for doc in query.stream()
    ]
    return sorted(
        items,
        key=lambda item: item.updated_at or item.created_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )


def upsert_access_request(
    *,
    provider: str,
    email: str | None = None,
    line_uid: str | None = None,
    display_name: str | None = None,
    picture_url: str | None = None,
    requested_account_type: str | None = None,
    company_name: str | None = None,
    first_name: str | None = None,
    nickname: str | None = None,
    contact_name: str | None = None,
    phone: str | None = None,
    tax_id: str | None = None,
    bank_account: dict[str, Any] | None = None,
    kyc_gcs_path: str | None = None,
) -> AccessRequest:
    normalized_provider = _normalize_provider(provider)
    normalized_email = _normalize_email(email or "") or None
    normalized_line_uid = _normalize_optional_text(line_uid)
    doc_id = access_request_doc_id(
        provider=normalized_provider,
        email=normalized_email,
        line_uid=normalized_line_uid,
        account_type=requested_account_type,
    )
    client = _ensure_firestore()
    ref = client.collection(ACCESS_REQUESTS_COLLECTION).document(doc_id)
    snapshot = ref.get()
    now = _now_utc()
    existing_payload = snapshot.to_dict() or {} if snapshot.exists else {}
    existing_status = _normalize_access_status(existing_payload.get("status"))
    is_resubmission = snapshot.exists and existing_status == "rejected"
    review_history = [
        dict(item)
        for item in (existing_payload.get("review_history") or [])
        if isinstance(item, dict)
    ][-48:]
    payload = {
        "provider": normalized_provider,
        "email": normalized_email,
        "line_uid": normalized_line_uid,
        "display_name": _normalize_optional_text(display_name),
        "picture_url": _normalize_optional_text(picture_url),
        "requested_account_type": _normalize_optional_text(requested_account_type),
        "company_name": _normalize_optional_text(company_name),
        "first_name": _normalize_optional_text(first_name),
        "nickname": _normalize_optional_text(nickname),
        "contact_name": _normalize_optional_text(contact_name),
        "phone": _normalize_optional_text(phone),
        "tax_id": _normalize_optional_text(tax_id),
        "bank_account": _normalized_bank_account_payload(bank_account),
        "kyc_gcs_path": (
            _normalize_optional_text(kyc_gcs_path)
            or _normalize_optional_text(existing_payload.get("kyc_gcs_path"))
        ),
        "status": "pending" if is_resubmission else existing_status if snapshot.exists else "pending",
        "updated_at": now,
    }
    if is_resubmission:
        if not any(item.get("action") == "rejected" for item in review_history):
            review_history.append(
                {
                    "action": "rejected",
                    "reason": _normalize_optional_text(existing_payload.get("rejection_reason")),
                    "actor": _normalize_optional_text(existing_payload.get("decided_by")),
                    "at": (
                        _datetime_value(existing_payload.get("decided_at"))
                        or _datetime_value(existing_payload.get("updated_at"))
                        or now
                    ),
                }
            )
        review_history.append(
            {
                "action": "resubmitted",
                "actor_type": "applicant",
                "at": now,
            }
        )
        payload.update(
            {
                "decided_account_type": None,
                "decided_role": None,
                "decided_roles": [],
                "target_admin_id": None,
                "target_subcontractor_id": None,
                "target_customer_id": None,
                "rejection_reason": None,
                "decided_by": None,
                "decided_at": None,
                "review_history": review_history,
            }
        )
    if not snapshot.exists:
        payload["created_at"] = now
    ref.set(payload, merge=True)
    merged = dict(existing_payload)
    merged.update(payload)
    return _access_request_from_dict(doc_id, merged)


def update_access_request(request_id: str, *, updates: dict[str, Any]) -> AccessRequest:
    current = get_access_request(request_id)
    payload = dict(updates)
    payload["updated_at"] = _now_utc()
    client = _ensure_firestore()
    client.collection(ACCESS_REQUESTS_COLLECTION).document(request_id).set(payload, merge=True)
    merged = asdict(current)
    merged.update(payload)
    return _access_request_from_dict(request_id, merged)


def approve_access_request(
    request_id: str,
    *,
    account_type: str,
    target_admin_id: str | None = None,
    target_subcontractor_id: str | None = None,
    target_customer_id: str | None = None,
    role: str | None = None,
    roles: list[str] | None = None,
    decided_by: str | None = None,
) -> AccessRequest:
    normalized_account_type = str(account_type or "").strip().lower()
    normalized_roles = _normalize_admin_roles(roles, default_role=role or ADMIN_ROLE) if normalized_account_type == "admin" else []
    decided_role = (
        _primary_role_for_roles(normalized_roles)
        if normalized_roles
        else CUSTOMER_ROLE
        if normalized_account_type == "customer"
        else SUBCONTRACTOR_ROLE
    )
    return update_access_request(
        request_id,
        updates={
            "status": "approved",
            "decided_account_type": normalized_account_type,
            "decided_role": decided_role,
            "decided_roles": normalized_roles,
            "target_admin_id": _normalize_optional_text(target_admin_id),
            "target_subcontractor_id": _normalize_optional_text(target_subcontractor_id),
            "target_customer_id": _normalize_optional_text(target_customer_id),
            "rejection_reason": None,
            "decided_by": _normalize_optional_text(decided_by),
            "decided_at": _now_utc(),
        },
    )


def reject_access_request(
    request_id: str,
    *,
    reason: str | None,
    decided_by: str | None,
) -> AccessRequest:
    current = get_access_request(request_id)
    rejected_at = _now_utc()
    history = list(current.review_history[-49:])
    history.append(
        {
            "action": "rejected",
            "reason": _normalize_optional_text(reason),
            "actor": _normalize_optional_text(decided_by),
            "at": rejected_at,
        }
    )
    return update_access_request(
        request_id,
        updates={
            "status": "rejected",
            "rejection_reason": _normalize_optional_text(reason),
            "decided_by": _normalize_optional_text(decided_by),
            "decided_at": rejected_at,
            "review_history": history,
        },
    )


def reopen_access_request(
    request_id: str,
    *,
    reopened_by: str | None,
) -> AccessRequest:
    current = get_access_request(request_id)
    if current.status != "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only rejected access requests can be reopened.",
        )

    reopened_at = _now_utc()
    history = list(current.review_history[-48:])
    if not any(item.get("action") == "rejected" for item in history):
        history.append(
            {
                "action": "rejected",
                "reason": current.rejection_reason,
                "actor": current.decided_by,
                "at": current.decided_at or current.updated_at or reopened_at,
            }
        )
    history.append(
        {
            "action": "reopened",
            "actor": _normalize_optional_text(reopened_by),
            "at": reopened_at,
        }
    )
    return update_access_request(
        request_id,
        updates={
            "status": "pending",
            "rejection_reason": None,
            "decided_by": None,
            "decided_at": None,
            "review_history": history,
        },
    )


def list_admins() -> list[AdminDirectoryEntry]:
    client = _ensure_firestore()
    docs = client.collection(ADMINS_COLLECTION).stream()
    items = [
        _admin_from_dict(doc.id, doc.to_dict() or {})
        for doc in docs
    ]
    return sorted(items, key=lambda item: item.email)


def get_admin_by_email(email: str) -> AdminDirectoryEntry | None:
    client = _ensure_firestore()
    snapshot = client.collection(ADMINS_COLLECTION).document(_email_doc_id(email)).get()
    if not snapshot.exists:
        return None
    return _admin_from_dict(snapshot.id, snapshot.to_dict() or {})


def get_admin(doc_id: str) -> AdminDirectoryEntry:
    client = _ensure_firestore()
    snapshot = client.collection(ADMINS_COLLECTION).document(doc_id).get()
    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin record {doc_id} not found.",
        )
    return _admin_from_dict(snapshot.id, snapshot.to_dict() or {})


def _active_owner_count() -> int:
    return sum(
        1
        for entry in list_admins()
        if entry.is_active and OWNER_ROLE in entry.roles
    )


def _ensure_can_remove_owner(current: AdminDirectoryEntry, payload: dict[str, Any]) -> None:
    next_roles = _normalize_admin_roles(
        payload.get("roles"),
        default_role=_normalize_admin_role(payload.get("role"), default=current.role),
    )
    next_is_active = bool(payload.get("is_active", current.is_active))

    removes_owner_access = (
        OWNER_ROLE in current.roles
        and current.is_active
        and (OWNER_ROLE not in next_roles or not next_is_active)
    )
    if removes_owner_access and _active_owner_count() <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one active Owner account is required.",
        )


def upsert_admin(
    *,
    email: str,
    display_name: str | None,
    contact_name: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    department: str | None = None,
    time: str | None = None,
    bank_account: dict[str, str | None] | None = None,
    role: str = ADMIN_ROLE,
    roles: list[str] | None = None,
    is_active: bool,
    granted_by: str | None,
) -> AdminDirectoryEntry:
    client = _ensure_firestore()
    normalized_email = _normalize_email(email)
    doc_id = _email_doc_id(normalized_email)
    existing = get_admin_by_email(normalized_email)
    now = _now_utc()
    normalized_roles = _normalize_admin_roles(roles, default_role=role)
    normalized_role = _primary_role_for_roles(normalized_roles)
    payload = {
        "email": normalized_email,
        "display_name": _normalize_optional_text(display_name),
        "role": normalized_role,
        "roles": normalized_roles,
        "is_active": bool(is_active),
        "granted_by": _normalize_optional_text(granted_by),
        "updated_at": now,
    }
    if contact_name is not None:
        payload["contact_name"] = _normalize_optional_text(contact_name)
    if phone is not None:
        payload["phone"] = _normalize_optional_text(phone)
    if company is not None:
        payload["company"] = _normalize_optional_text(company)
    if department is not None:
        payload["department"] = _normalize_optional_text(department)
    if time is not None:
        payload["time"] = _normalize_optional_text(time)
    if bank_account is not None:
        payload["bank_account"] = {
            "bank_name": _normalize_optional_text(bank_account.get("bank_name")),
            "account_no": _normalize_optional_text(bank_account.get("account_no")),
            "account_name": _normalize_optional_text(bank_account.get("account_name")),
        }
    if existing is not None:
        _ensure_can_remove_owner(existing, payload)
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
    if "contact_name" in updates:
        payload["contact_name"] = _normalize_optional_text(updates["contact_name"])
    if "phone" in updates:
        payload["phone"] = _normalize_optional_text(updates["phone"])
    if "company" in updates:
        payload["company"] = _normalize_optional_text(updates["company"])
    if "department" in updates:
        payload["department"] = _normalize_optional_text(updates["department"])
    if "time" in updates:
        payload["time"] = _normalize_optional_text(updates["time"])
    if "timezone" in updates:
        payload["time"] = _normalize_optional_text(updates["timezone"])
    if "bank_account" in updates and isinstance(updates["bank_account"], dict):
        payload["bank_account"] = {
            "bank_name": _normalize_optional_text(updates["bank_account"].get("bank_name")),
            "account_no": _normalize_optional_text(updates["bank_account"].get("account_no")),
            "account_name": _normalize_optional_text(updates["bank_account"].get("account_name")),
        }
    if "role" in updates:
        payload["roles"] = _normalize_admin_roles(
            updates.get("roles"),
            default_role=_normalize_admin_role(updates["role"]),
        )
        payload["role"] = _primary_role_for_roles(payload["roles"])
    elif "roles" in updates:
        payload["roles"] = _normalize_admin_roles(updates["roles"], default_role=current.role)
        payload["role"] = _primary_role_for_roles(payload["roles"])
    if "is_active" in updates:
        payload["is_active"] = bool(updates["is_active"])

    _ensure_can_remove_owner(current, payload)
    client.collection(ADMINS_COLLECTION).document(doc_id).set(payload, merge=True)
    merged = asdict(current)
    merged.update(payload)
    return _admin_from_dict(doc_id, merged)


def update_admin_profile(
    email: str,
    *,
    updates: dict[str, Any],
    role: str = ADMIN_ROLE,
) -> AdminDirectoryEntry:
    client = _ensure_firestore()
    normalized_email = _normalize_email(email)
    doc_id = _email_doc_id(normalized_email)
    existing = get_admin_by_email(normalized_email)
    now = _now_utc()
    payload: dict[str, Any] = {"email": normalized_email, "updated_at": now}

    if existing is None:
        payload["roles"] = _normalize_admin_roles(None, default_role=role)
        payload["role"] = _primary_role_for_roles(payload["roles"])
        payload["is_active"] = True
        payload["created_at"] = now

    if "display_name" in updates:
        payload["display_name"] = _normalize_optional_text(updates["display_name"])
    if "contact_name" in updates:
        payload["contact_name"] = _normalize_optional_text(updates["contact_name"])
    if "phone" in updates:
        payload["phone"] = _normalize_optional_text(updates["phone"])
    if "bank_account" in updates and isinstance(updates["bank_account"], dict):
        payload["bank_account"] = {
            "bank_name": _normalize_optional_text(updates["bank_account"].get("bank_name")),
            "account_no": _normalize_optional_text(updates["bank_account"].get("account_no")),
            "account_name": _normalize_optional_text(updates["bank_account"].get("account_name")),
        }
    if "company" in updates:
        payload["company"] = _normalize_optional_text(updates["company"])
    if "department" in updates:
        payload["department"] = _normalize_optional_text(updates["department"])
    if "time" in updates:
        payload["time"] = _normalize_optional_text(updates["time"])
    if "timezone" in updates:
        payload["time"] = _normalize_optional_text(updates["timezone"])
    if "profile_image_storage_key" in updates:
        payload["profile_image_storage_key"] = _normalize_optional_text(
            updates["profile_image_storage_key"]
        )

    client.collection(ADMINS_COLLECTION).document(doc_id).set(payload, merge=True)
    if existing is None:
        return _admin_from_dict(doc_id, payload)

    merged = asdict(existing)
    merged.update(payload)
    return _admin_from_dict(doc_id, merged)


def get_authorized_admin_roles(email: str) -> list[str]:
    normalized_email = _normalize_email(email)
    managed_admin = get_admin_by_email(normalized_email)
    if managed_admin is not None:
        return managed_admin.roles if managed_admin.is_active else []

    settings = get_settings()
    if settings.is_development and normalized_email in settings.admin_emails:
        return [ADMIN_ROLE]

    domain = settings.admin_email_domain
    if settings.is_development and domain and normalized_email.endswith(f"@{domain}"):
        return [ADMIN_ROLE]
    return []


def get_authorized_admin_role(email: str) -> str | None:
    roles = get_authorized_admin_roles(email)
    if not roles:
        return None
    return _primary_role_for_roles(roles)


def is_email_authorized_admin(email: str) -> bool:
    return get_authorized_admin_role(email) is not None


def ensure_bootstrap_admin(email: str, display_name: str | None) -> AdminDirectoryEntry | None:
    existing = get_admin_by_email(email)
    if existing is not None:
        return existing

    settings = get_settings()
    normalized_email = _normalize_email(email)
    can_bootstrap = normalized_email in settings.admin_emails or (
        settings.is_development
        and settings.admin_email_domain
        and normalized_email.endswith(f"@{settings.admin_email_domain}")
    )
    if can_bootstrap and not list_admins():
        return upsert_admin(
            email=normalized_email,
            display_name=display_name,
            role=OWNER_ROLE,
            roles=[OWNER_ROLE],
            is_active=True,
            granted_by="auto-admin-login",
        )
    return None
