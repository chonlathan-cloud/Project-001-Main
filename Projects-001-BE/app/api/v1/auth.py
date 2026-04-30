"""
Authentication router for admin and subcontractor flows.
"""

from __future__ import annotations

import hashlib
import logging

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps.auth import AuthenticatedUser, get_current_user
from app.core.google_clients import get_firebase_auth
from app.core.security import issue_session_token
from app.schemas.profile_schema import (
    AdminLoginRequest,
    AuthSessionResponse,
    SessionUserPayload,
)
from app.schemas.responses import StandardResponse
from app.services.gcs_storage_service import upload_kyc_image_to_storage
from app.services.identity_service import (
    create_subcontractor_profile,
    ensure_bootstrap_admin,
    get_subcontractor_by_line_uid,
    is_email_authorized_admin,
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


def _subcontractor_session_response(*, line_uid: str, subcontractor_id: str, name: str) -> AuthSessionResponse:
    session_token = issue_session_token(
        subject=line_uid,
        role="subcontractor",
        display_name=name,
        subcontractor_id=subcontractor_id,
    )
    firebase_custom_token = _create_firebase_custom_token(
        line_uid,
        claims={"role": "subcontractor", "subcontractor_id": subcontractor_id},
    )
    return AuthSessionResponse(
        status="SUCCESS",
        session_token=session_token,
        firebase_custom_token=firebase_custom_token,
        user=SessionUserPayload(
            role="subcontractor",
            display_name=name,
            subcontractor_id=subcontractor_id,
            line_uid=line_uid,
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
            return StandardResponse(
                data={
                    "status": "REQUIRE_SIGNUP",
                    "line_uid": line_uid,
                    "display_name": display_name,
                    "line_picture_url": line_picture_url,
                    "message": "User not found. Please complete registration.",
                }
            )

        if line_picture_url and profile.line_picture_url != line_picture_url:
            profile = update_subcontractor_profile(
                profile.id,
                updates={"line_picture_url": line_picture_url},
            )

        return StandardResponse(
            data=_subcontractor_session_response(
                line_uid=line_uid,
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
    kyc_image: UploadFile | None = None,
):
    try:
        existing_profile = get_subcontractor_by_line_uid(line_uid.strip())
        if existing_profile is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This LINE account is already bound to an existing subcontractor profile.",
            )

        subcontractor_id = f"sub_{hashlib.sha1(line_uid.strip().encode('utf-8')).hexdigest()[:10]}"
        gcs_path = None
        if kyc_image is not None:
            file_bytes = await kyc_image.read()
            gcs_path = await upload_kyc_image_to_storage(
                file_bytes=file_bytes,
                file_name=kyc_image.filename,
                content_type=kyc_image.content_type,
                entity_key=subcontractor_id,
            )

        profile = create_subcontractor_profile(
            subcontractor_id=subcontractor_id,
            line_uid=line_uid.strip(),
            line_picture_url=(line_picture_url or "").strip() or None,
            name=name.strip(),
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

        return StandardResponse(
            data=_subcontractor_session_response(
                line_uid=profile.line_uid or line_uid.strip(),
                subcontractor_id=profile.id,
                name=profile.name,
            )
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign-up failed: {exc}",
        ) from exc


@router.post("/admin-login", response_model=StandardResponse[AuthSessionResponse])
async def admin_login(request: AdminLoginRequest):
    try:
        email = (request.email or "").strip().lower()
        display_name = (request.display_name or "").strip() or None

        if request.firebase_id_token:
            firebase_auth = get_firebase_auth()
            decoded = firebase_auth.verify_id_token(request.firebase_id_token)
            email = str(decoded.get("email") or email).strip().lower()
            display_name = str(decoded.get("name") or display_name or "").strip() or None

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin email is required.",
            )

        if not is_email_authorized_admin(email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This email is not authorized as an admin.",
            )

        ensure_bootstrap_admin(email, display_name)

        session_token = issue_session_token(
            subject=email,
            role="admin",
            email=email,
            display_name=display_name,
        )
        firebase_custom_token = _create_firebase_custom_token(
            email,
            claims={"role": "admin", "email": email},
        )
        return StandardResponse(
            data=AuthSessionResponse(
                status="SUCCESS",
                session_token=session_token,
                firebase_custom_token=firebase_custom_token,
                user=SessionUserPayload(
                    role="admin",
                    email=email,
                    display_name=display_name,
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
async def get_current_session_user(user: AuthenticatedUser = Depends(get_current_user)):
    return StandardResponse(
        data=SessionUserPayload(
            role=user.role,
            email=user.email,
            display_name=user.display_name,
            subcontractor_id=user.subcontractor_id,
        )
    )
