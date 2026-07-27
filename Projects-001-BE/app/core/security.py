"""
Small HMAC-signed session token helpers.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings


ACCESS_REQUEST_TOKEN_PURPOSE = "access_request"
ACCESS_REQUEST_TOKEN_EXPIRE_MINUTES = 15
CUSTOMER_REPORT_SHARE_TOKEN_PURPOSE = "customer_report_share"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sign(message: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url_encode(digest)


def issue_session_token(
    *,
    subject: str,
    role: str,
    roles: list[str] | None = None,
    email: str | None = None,
    display_name: str | None = None,
    subcontractor_id: str | None = None,
    customer_id: str | None = None,
    line_uid: str | None = None,
    auth_provider: str | None = None,
    access_request_id: str | None = None,
    access_status: str | None = None,
    rejection_reason: str | None = None,
    tenant_id: str | None = None,
    app_env: str | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_expire_minutes)
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    token_tenant_id = tenant_id if tenant_id is not None else settings.identity_platform_tenant_id
    token_app_env = app_env if app_env is not None else settings.app_env
    payload = {
        "sub": subject,
        "role": role,
        "roles": roles or [role],
        "email": email,
        "display_name": display_name,
        "subcontractor_id": subcontractor_id,
        "customer_id": customer_id,
        "line_uid": line_uid,
        "auth_provider": auth_provider,
        "access_request_id": access_request_id,
        "access_status": access_status,
        "rejection_reason": rejection_reason,
        "tenant_id": token_tenant_id,
        "app_env": token_app_env,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded_header = _b64url_encode(_json_bytes(header))
    encoded_payload = _b64url_encode(_json_bytes(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = _sign(signing_input, settings.jwt_secret_key)
    return f"{encoded_header}.{encoded_payload}.{signature}"


def verify_session_token(token: str) -> dict[str, Any]:
    settings = get_settings()

    try:
        encoded_header, encoded_payload, signature = token.split(".", 2)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed session token.",
        ) from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = _sign(signing_input, settings.jwt_secret_key)

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token signature.",
        )

    try:
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token payload.",
        ) from exc

    expires_at = int(payload.get("exp") or 0)
    if expires_at <= int(datetime.now(UTC).timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired.",
        )

    expected_tenant_id = settings.identity_platform_tenant_id
    if expected_tenant_id:
        actual_tenant_id = str(payload.get("tenant_id") or "").strip()
        if actual_tenant_id != expected_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session token was issued for a different tenant.",
            )

        actual_app_env = str(payload.get("app_env") or "").strip()
        if actual_app_env != settings.app_env:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session token was issued for a different environment.",
            )

    return payload


def issue_access_request_token(
    *,
    provider: str,
    email: str | None = None,
    line_uid: str | None = None,
    portal: str | None = None,
    expires_minutes: int = ACCESS_REQUEST_TOKEN_EXPIRE_MINUTES,
) -> str:
    """Issue a short-lived proof that an identity provider login succeeded."""
    settings = get_settings()
    normalized_provider = str(provider or "").strip().lower()
    normalized_email = str(email or "").strip().lower() or None
    normalized_line_uid = str(line_uid or "").strip() or None

    if normalized_provider == "google" and not normalized_email:
        raise ValueError("Google access request tokens require an email.")
    if normalized_provider == "line" and not normalized_line_uid:
        raise ValueError("LINE access request tokens require a LINE UID.")
    if normalized_provider not in {"google", "line"}:
        raise ValueError("Unsupported access request token provider.")

    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=expires_minutes)
    header = {"alg": settings.jwt_algorithm, "typ": "RAYADEE-ACCESS-REQUEST"}
    payload = {
        "purpose": ACCESS_REQUEST_TOKEN_PURPOSE,
        "provider": normalized_provider,
        "email": normalized_email,
        "line_uid": normalized_line_uid,
        "portal": str(portal or "").strip().lower() or None,
        "tenant_id": settings.identity_platform_tenant_id,
        "app_env": settings.app_env,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    encoded_header = _b64url_encode(_json_bytes(header))
    encoded_payload = _b64url_encode(_json_bytes(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = _sign(signing_input, settings.jwt_secret_key)
    return f"{encoded_header}.{encoded_payload}.{signature}"


def verify_access_request_token(token: str) -> dict[str, Any]:
    """Verify an access-request proof and return its trusted identity claims."""
    settings = get_settings()

    try:
        encoded_header, encoded_payload, signature = token.split(".", 2)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed access request token.",
        ) from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = _sign(signing_input, settings.jwt_secret_key)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access request token signature.",
        )

    try:
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access request token payload.",
        ) from exc

    now_timestamp = int(datetime.now(UTC).timestamp())
    if int(payload.get("exp") or 0) <= now_timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access request token has expired. Please sign in again.",
        )
    if payload.get("purpose") != ACCESS_REQUEST_TOKEN_PURPOSE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access request token purpose.",
        )

    actual_tenant_id = str(payload.get("tenant_id") or "").strip()
    expected_tenant_id = str(settings.identity_platform_tenant_id or "").strip()
    if actual_tenant_id != expected_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access request token was issued for a different tenant.",
        )
    actual_app_env = str(payload.get("app_env") or "").strip()
    if actual_app_env != settings.app_env:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access request token was issued for a different environment.",
        )

    provider = str(payload.get("provider") or "").strip().lower()
    email = str(payload.get("email") or "").strip().lower() or None
    line_uid = str(payload.get("line_uid") or "").strip() or None
    if provider == "google" and not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access request token is missing its verified Google identity.",
        )
    if provider == "line" and not line_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access request token is missing its verified LINE identity.",
        )
    if provider not in {"google", "line"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access request token has an unsupported provider.",
        )

    return payload


def issue_customer_report_share_token(*, project_id: str, token_version: int) -> str:
    """Create a stable, revocable capability token for one project's public reports."""
    settings = get_settings()
    normalized_project_id = str(project_id or "").strip()
    normalized_version = int(token_version)
    if not normalized_project_id:
        raise ValueError("Customer report share tokens require a project ID.")
    if normalized_version < 1:
        raise ValueError("Customer report share token versions must be positive.")

    header = {"alg": "HS256", "typ": "RAYADEE-CUSTOMER-SHARE"}
    payload = {
        "purpose": CUSTOMER_REPORT_SHARE_TOKEN_PURPOSE,
        "project_id": normalized_project_id,
        "token_version": normalized_version,
        "tenant_id": settings.identity_platform_tenant_id,
        "app_env": settings.app_env,
    }
    encoded_header = _b64url_encode(_json_bytes(header))
    encoded_payload = _b64url_encode(_json_bytes(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = _sign(
        signing_input,
        settings.effective_customer_report_share_secret,
    )
    return f"{encoded_header}.{encoded_payload}.{signature}"


def verify_customer_report_share_token(token: str) -> dict[str, Any]:
    """Verify a customer report capability without creating a customer session."""
    settings = get_settings()
    try:
        encoded_header, encoded_payload, signature = str(token or "").split(".", 2)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared report link not found.",
        ) from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = _sign(
        signing_input,
        settings.effective_customer_report_share_secret,
    )
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared report link not found.",
        )

    try:
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared report link not found.",
        ) from exc

    try:
        token_version = int(payload.get("token_version") or 0)
    except (TypeError, ValueError):
        token_version = 0
    valid = (
        payload.get("purpose") == CUSTOMER_REPORT_SHARE_TOKEN_PURPOSE
        and bool(str(payload.get("project_id") or "").strip())
        and token_version >= 1
        and str(payload.get("tenant_id") or "").strip()
        == str(settings.identity_platform_tenant_id or "").strip()
        and str(payload.get("app_env") or "").strip() == settings.app_env
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shared report link not found.",
        )
    return payload
