"""
Authentication router for admin and subcontractor flows.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps.auth import AuthenticatedUser, get_current_user_allow_pending, role_permissions
from app.core.config import get_settings
from app.core.google_clients import get_firebase_auth
from app.core.security import issue_session_token
from app.schemas.profile_schema import (
    AdminLoginRequest,
    AuthSessionResponse,
    SessionUserPayload,
    AccessRequestItem,
)
from app.schemas.responses import StandardResponse
from app.services.gcs_storage_service import upload_kyc_image_to_storage
from app.services.identity_service import (
    ensure_bootstrap_admin,
    get_access_request,
    get_access_request_by_identity,
    get_authorized_admin_roles,
    get_subcontractor_by_email,
    get_subcontractor_by_line_uid,
    upsert_access_request,
    update_subcontractor_profile,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


class LineLoginRequest(BaseModel):
    line_access_token: str


async def _fetch_line_profile(line_access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://api.line.me/v2/profile",
            headers={"Authorization": f"Bearer {line_access_token}"},
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LINE access token is invalid or expired.",
        )

    payload = response.json()
    line_uid = str(payload.get("userId") or "").strip()
    if not line_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="LINE profile response did not include a user id.",
        )
    return payload


def _create_firebase_custom_token(uid: str, claims: dict | None = None) -> str | None:
    try:
        firebase_auth = get_firebase_auth()
        token = firebase_auth.create_custom_token(uid, developer_claims=claims or {})
        return token.decode("utf-8") if isinstance(token, bytes) else str(token)
    except Exception as exc:
        # Local ADC user credentials can verify ID tokens but cannot always sign
        # Firebase custom tokens. Keep the app login flow working with the
        # backend session token and surface a warning for production hardening.
        logger.warning(
            "firebase custom token generation skipped for uid=%s: %s",
            uid,
            exc,
        )
        return None


def _access_request_item(request) -> AccessRequestItem:
    return AccessRequestItem(**asdict(request))


def _pending_session_response(request) -> AuthSessionResponse:
    roles = ["pending"]
    subject = request.email or request.line_uid or request.id
    session_token = issue_session_token(
        subject=subject,
        role="pending",
        roles=roles,
        email=request.email,
        display_name=request.display_name or request.company_name or request.contact_name,
        line_uid=request.line_uid,
        auth_provider=request.provider,
        access_request_id=request.id,
        access_status=request.status,
        rejection_reason=request.rejection_reason,
    )
    return AuthSessionResponse(
        status="PENDING_APPROVAL" if request.status != "rejected" else "ACCESS_REJECTED",
        session_token=session_token,
        firebase_custom_token=None,
        user=SessionUserPayload(
            role="pending",
            roles=roles,
            email=request.email,
            display_name=request.display_name or request.company_name or request.contact_name,
            line_uid=request.line_uid,
            auth_provider=request.provider,
            access_request_id=request.id,
            access_status=request.status,
            rejection_reason=request.rejection_reason,
            permissions=role_permissions("pending", roles),
        ),
    )


def _subcontractor_session_response(
    *,
    subcontractor_id: str,
    name: str,
    line_uid: str | None = None,
    email: str | None = None,
) -> AuthSessionResponse:
    roles = ["subcontractor"]
    subject = email or line_uid or subcontractor_id
    session_token = issue_session_token(
        subject=subject,
        role="subcontractor",
        roles=roles,
        email=email,
        display_name=name,
        subcontractor_id=subcontractor_id,
        line_uid=line_uid,
    )
    firebase_custom_token = _create_firebase_custom_token(
        subject,
        claims={"role": "subcontractor", "roles": roles, "subcontractor_id": subcontractor_id},
    )
    return AuthSessionResponse(
        status="SUCCESS",
        session_token=session_token,
        firebase_custom_token=firebase_custom_token,
        user=SessionUserPayload(
            role="subcontractor",
            roles=roles,
            email=email,
            display_name=name,
            subcontractor_id=subcontractor_id,
            line_uid=line_uid,
            permissions=role_permissions("subcontractor", roles),
        ),
    )


@router.post("/line-login", response_model=StandardResponse[dict | AuthSessionResponse])
async def line_login(request: LineLoginRequest):
    try:
        line_profile = await _fetch_line_profile(request.line_access_token)
        line_uid = str(line_profile.get("userId") or "").strip()
        display_name = str(line_profile.get("displayName") or "Subcontractor").strip()
        line_picture_url = str(line_profile.get("pictureUrl") or "").strip() or None
        profile = get_subcontractor_by_line_uid(line_uid)

        if profile is None:
            existing_request = get_access_request_by_identity(provider="line", line_uid=line_uid)
            if existing_request is not None and existing_request.status != "approved":
                return StandardResponse(data=_pending_session_response(existing_request))
            return StandardResponse(
                data={
                    "status": "REQUIRE_SIGNUP",
                    "provider": "line",
                    "line_uid": line_uid,
                    "display_name": display_name,
                    "line_picture_url": line_picture_url,
                    "message": "User not found. Please complete registration.",
                }
            )

        if not profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This subcontractor account is inactive. Please contact an admin.",
            )

        if line_picture_url and profile.line_picture_url != line_picture_url:
            profile = update_subcontractor_profile(
                profile.id,
                updates={"line_picture_url": line_picture_url},
            )

        return StandardResponse(
            data=_subcontractor_session_response(
                line_uid=line_uid,
                email=profile.email,
                subcontractor_id=profile.id,
                name=profile.name,
            )
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LINE login failed: {exc}",
        ) from exc


@router.post("/sign-up", response_model=StandardResponse[AuthSessionResponse])
async def sign_up(
    line_uid: str = Form(..., description="LINE UID from the login step"),
    line_picture_url: str | None = Form(default=None, description="LINE avatar URL"),
    name: str = Form(..., description="Company or subcontractor name"),
    contact_name: str | None = Form(default=None, description="Default requester/contact name"),
    phone: str | None = Form(default=None, description="Default contact phone number"),
    tax_id: str = Form(..., description="Tax Identification Number"),
    bank_name: str | None = Form(default=None, description="Default bank name"),
    account_no: str | None = Form(default=None, description="Default bank account number"),
    account_name: str | None = Form(default=None, description="Default bank account name"),
    kyc_image: UploadFile | None = File(default=None),
):
    try:
        existing_profile = get_subcontractor_by_line_uid(line_uid.strip())
        if existing_profile is not None:
            if not existing_profile.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This subcontractor account is inactive. Please contact an admin.",
                )
            return StandardResponse(
                data=_subcontractor_session_response(
                    line_uid=existing_profile.line_uid or line_uid.strip(),
                    email=existing_profile.email,
                    subcontractor_id=existing_profile.id,
                    name=existing_profile.name,
                )
            )

        request_id = f"line-{hashlib.sha1(line_uid.strip().encode('utf-8')).hexdigest()[:16]}"
        gcs_path = None
        if kyc_image is not None:
            file_bytes = await kyc_image.read()
            gcs_path = await upload_kyc_image_to_storage(
                file_bytes=file_bytes,
                file_name=kyc_image.filename,
                content_type=kyc_image.content_type,
                entity_key=request_id,
            )

        request = upsert_access_request(
            provider="line",
            line_uid=line_uid.strip(),
            picture_url=(line_picture_url or "").strip() or None,
            display_name=name.strip(),
            requested_account_type="subcontractor",
            company_name=name.strip(),
            contact_name=(contact_name or "").strip() or None,
            phone=(phone or "").strip() or None,
            tax_id=tax_id.strip(),
            kyc_gcs_path=gcs_path,
            bank_account={
                "bank_name": (bank_name or "").strip() or None,
                "account_no": (account_no or "").strip() or None,
                "account_name": (account_name or "").strip() or None,
            },
        )

        return StandardResponse(data=_pending_session_response(request))

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign-up failed: {exc}",
        ) from exc


@router.post("/access-request", response_model=StandardResponse[AuthSessionResponse])
async def submit_access_request(
    provider: str = Form(..., description="Identity provider: google or line"),
    email: str | None = Form(default=None, description="Google email when provider is google"),
    line_uid: str | None = Form(default=None, description="LINE UID when provider is line"),
    picture_url: str | None = Form(default=None, description="Provider avatar URL"),
    display_name: str | None = Form(default=None, description="Provider display name"),
    requested_account_type: str | None = Form(default=None, description="Optional requested account type"),
    company_name: str | None = Form(default=None, description="Company or subcontractor name"),
    contact_name: str | None = Form(default=None, description="Contact person"),
    phone: str | None = Form(default=None, description="Contact phone"),
    tax_id: str | None = Form(default=None, description="Tax Identification Number"),
    bank_name: str | None = Form(default=None, description="Default bank name"),
    account_no: str | None = Form(default=None, description="Default bank account number"),
    account_name: str | None = Form(default=None, description="Default bank account name"),
    kyc_image: UploadFile | None = File(default=None),
):
    try:
        normalized_provider = str(provider or "").strip().lower()
        normalized_email = str(email or "").strip().lower() or None
        normalized_line_uid = str(line_uid or "").strip() or None
        if normalized_provider not in {"google", "line"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access requests require provider 'google' or 'line'.",
            )
        if normalized_provider == "google" and not normalized_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google access requests require an email.",
            )
        if normalized_provider == "line" and not normalized_line_uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LINE access requests require a LINE UID.",
            )

        request_key = normalized_email or normalized_line_uid or normalized_provider
        request_id = f"{normalized_provider}-{hashlib.sha1(request_key.encode('utf-8')).hexdigest()[:16]}"
        gcs_path = None
        if kyc_image is not None:
            file_bytes = await kyc_image.read()
            gcs_path = await upload_kyc_image_to_storage(
                file_bytes=file_bytes,
                file_name=kyc_image.filename,
                content_type=kyc_image.content_type,
                entity_key=request_id,
            )

        request = upsert_access_request(
            provider=normalized_provider,
            email=normalized_email,
            line_uid=normalized_line_uid,
            picture_url=(picture_url or "").strip() or None,
            display_name=(display_name or company_name or contact_name or "").strip() or None,
            requested_account_type=(requested_account_type or "").strip() or None,
            company_name=(company_name or display_name or "").strip() or None,
            contact_name=(contact_name or display_name or "").strip() or None,
            phone=(phone or "").strip() or None,
            tax_id=(tax_id or "").strip() or None,
            kyc_gcs_path=gcs_path,
            bank_account={
                "bank_name": (bank_name or "").strip() or None,
                "account_no": (account_no or "").strip() or None,
                "account_name": (account_name or "").strip() or None,
            },
        )
        return StandardResponse(data=_pending_session_response(request))

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Access request failed: {exc}",
        ) from exc


@router.post("/admin-login", response_model=StandardResponse[dict | AuthSessionResponse])
async def admin_login(request: AdminLoginRequest):
    try:
        email = (request.email or "").strip().lower()
        display_name = (request.display_name or "").strip() or None
        picture_url = None

        if request.firebase_id_token:
            firebase_auth = get_firebase_auth()
            decoded = firebase_auth.verify_id_token(request.firebase_id_token)
            email = str(decoded.get("email") or email).strip().lower()
            display_name = str(decoded.get("name") or display_name or "").strip() or None
            picture_url = str(decoded.get("picture") or "").strip() or None
        elif not get_settings().is_development:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google sign-in token is required.",
            )

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin email is required.",
            )

        authorized_roles = get_authorized_admin_roles(email)
        if not authorized_roles:
            bootstrap_entry = ensure_bootstrap_admin(email, display_name)
            if bootstrap_entry is not None:
                authorized_roles = bootstrap_entry.roles

        if not authorized_roles:
            subcontractor_profile = get_subcontractor_by_email(email)
            if subcontractor_profile is not None:
                if not subcontractor_profile.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="This subcontractor account is inactive. Please contact an admin.",
                    )
                return StandardResponse(
                    data=_subcontractor_session_response(
                        line_uid=subcontractor_profile.line_uid,
                        email=email,
                        subcontractor_id=subcontractor_profile.id,
                        name=subcontractor_profile.name,
                    )
                )

            existing_request = get_access_request_by_identity(provider="google", email=email)
            if existing_request is not None:
                if (
                    display_name
                    and existing_request.status == "pending"
                    and display_name != existing_request.display_name
                ):
                    existing_request = upsert_access_request(
                        provider="google",
                        email=email,
                        display_name=display_name,
                        picture_url=picture_url or existing_request.picture_url,
                        company_name=existing_request.company_name,
                        contact_name=existing_request.contact_name,
                        phone=existing_request.phone,
                        tax_id=existing_request.tax_id,
                        bank_account=existing_request.bank_account,
                        requested_account_type=existing_request.requested_account_type,
                        kyc_gcs_path=existing_request.kyc_gcs_path,
                    )
                return StandardResponse(data=_pending_session_response(existing_request))

            return StandardResponse(
                data={
                    "status": "REQUIRE_SIGNUP",
                    "provider": "google",
                    "email": email,
                    "display_name": display_name,
                    "picture_url": picture_url,
                    "message": "Please complete an access request for admin review.",
                }
            )
        authorized_role = (
            "owner"
            if "owner" in authorized_roles
            else "admin"
            if "admin" in authorized_roles
            else authorized_roles[0]
        )

        session_token = issue_session_token(
            subject=email,
            role=authorized_role,
            roles=authorized_roles,
            email=email,
            display_name=display_name,
        )
        firebase_custom_token = _create_firebase_custom_token(
            email,
            claims={"role": authorized_role, "roles": authorized_roles, "email": email},
        )
        return StandardResponse(
            data=AuthSessionResponse(
                status="SUCCESS",
                session_token=session_token,
                firebase_custom_token=firebase_custom_token,
                user=SessionUserPayload(
                    role=authorized_role,
                    roles=authorized_roles,
                    email=email,
                    display_name=display_name,
                    permissions=role_permissions(authorized_role, authorized_roles),
                ),
            )
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Admin login failed: {exc}",
        ) from exc


@router.get("/me", response_model=StandardResponse[SessionUserPayload])
async def get_current_session_user(user: AuthenticatedUser = Depends(get_current_user_allow_pending)):
    return StandardResponse(
        data=SessionUserPayload(
            role=user.role,
            roles=list(user.roles),
            email=user.email,
            display_name=user.display_name,
            subcontractor_id=user.subcontractor_id,
            line_uid=user.line_uid,
            auth_provider=user.auth_provider,
            access_request_id=user.access_request_id,
            access_status=user.access_status,
            rejection_reason=user.rejection_reason,
            permissions=role_permissions(user.role, user.roles),
        )
    )


@router.get("/access-request/status", response_model=StandardResponse[AccessRequestItem])
async def get_access_request_status(user: AuthenticatedUser = Depends(get_current_user_allow_pending)):
    if not user.access_request_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This session is not linked to an access request.",
        )
    return StandardResponse(data=_access_request_item(get_access_request(user.access_request_id)))
