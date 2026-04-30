"""
Admin settings router for subcontractor profiles and admin directory management.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.api.deps.auth import AuthenticatedUser, require_admin_user
from app.core.config import get_settings
from app.schemas.profile_schema import (
    AdminDirectoryItem,
    SubcontractorProfileItem,
    UpdateAdminRequest,
    UpdateSubcontractorProfileRequest,
    UpsertAdminRequest,
)
from app.schemas.responses import StandardResponse
from app.services.gcs_storage_service import generate_signed_url_for_storage_key
from app.services.identity_service import (
    list_admins as list_admin_directory_entries,
    list_subcontractors as list_subcontractor_profiles,
    get_kyc_storage_key,
    reset_subcontractor_line_binding,
    update_admin,
    update_subcontractor_profile,
    upsert_admin,
)

router = APIRouter(prefix="/settings", tags=["Admin Settings"])


async def _profile_item(profile) -> SubcontractorProfileItem:
    payload = asdict(profile)
    if profile.profile_image_storage_key:
        payload["profile_image_url"] = await generate_signed_url_for_storage_key(
            storage_key=profile.profile_image_storage_key,
            expires_in_minutes=get_settings().signed_url_expires_minutes,
        )
    else:
        payload["profile_image_url"] = None
    return SubcontractorProfileItem(**payload)


def _admin_item(entry) -> AdminDirectoryItem:
    return AdminDirectoryItem(**asdict(entry))


@router.get("/subcontractors", response_model=StandardResponse[list[SubcontractorProfileItem]])
async def list_subcontractors(_user: AuthenticatedUser = Depends(require_admin_user)):
    profiles = list_subcontractor_profiles()
    return StandardResponse(
        data=[await _profile_item(profile) for profile in profiles]
    )


@router.put("/subcontractors/{sub_id}", response_model=StandardResponse[SubcontractorProfileItem])
async def update_subcontractor(
    sub_id: str,
    request: UpdateSubcontractorProfileRequest,
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    profile = update_subcontractor_profile(
        sub_id,
        updates=request.model_dump(exclude_none=True),
    )
    return StandardResponse(data=await _profile_item(profile))


@router.post("/subcontractors/{sub_id}/reset-line", response_model=StandardResponse[SubcontractorProfileItem])
async def reset_line_binding(
    sub_id: str,
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    profile = reset_subcontractor_line_binding(sub_id)
    return StandardResponse(data=await _profile_item(profile))


@router.get("/users/{user_id}/kyc-image", response_model=StandardResponse[dict])
async def get_kyc_image(
    user_id: str,
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    expires_in_minutes = get_settings().signed_url_expires_minutes
    storage_key = get_kyc_storage_key(user_id)
    signed_url = await generate_signed_url_for_storage_key(
        storage_key=storage_key,
        expires_in_minutes=expires_in_minutes,
    )
    return StandardResponse(
        data={
            "user_id": user_id,
            "signed_url": signed_url,
            "storage_key": storage_key,
            "expires_in_minutes": expires_in_minutes,
            "message": "Signed URL generated. Valid for a limited time.",
        }
    )


@router.get("/admins", response_model=StandardResponse[list[AdminDirectoryItem]])
async def list_admins(_user: AuthenticatedUser = Depends(require_admin_user)):
    return StandardResponse(
        data=[_admin_item(entry) for entry in list_admin_directory_entries()]
    )


@router.post("/admins", response_model=StandardResponse[AdminDirectoryItem])
async def create_admin(
    request: UpsertAdminRequest,
    user: AuthenticatedUser = Depends(require_admin_user),
):
    entry = upsert_admin(
        email=str(request.email),
        display_name=request.display_name,
        is_active=request.is_active,
        granted_by=user.email or user.subject,
    )
    return StandardResponse(data=_admin_item(entry))


@router.put("/admins/{admin_id}", response_model=StandardResponse[AdminDirectoryItem])
async def edit_admin(
    admin_id: str,
    request: UpdateAdminRequest,
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    entry = update_admin(admin_id, updates=request.model_dump(exclude_none=True))
    return StandardResponse(data=_admin_item(entry))
