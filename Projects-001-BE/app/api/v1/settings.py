"""
Admin settings router for subcontractor profiles and admin directory management.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps.auth import AuthenticatedUser, require_admin_user, require_owner_user
from app.core.config import get_settings
from app.schemas.profile_schema import (
    AccessRequestItem,
    ApproveAccessRequestRequest,
    AdminDirectoryItem,
    RejectAccessRequestRequest,
    SubcontractorProfileItem,
    UpdateAdminRequest,
    UpdateSubcontractorProfileRequest,
    UpsertAdminRequest,
)
from app.schemas.responses import StandardResponse
from app.schemas.settings_schema import (
    SettingsIntegrationGroup,
    SettingsIntegrationItem,
    SettingsIntegrationsResponse,
)
from app.services.gcs_storage_service import generate_signed_url_for_storage_key
from app.services.identity_service import (
    approve_access_request,
    admin_doc_id_for_email,
    create_subcontractor_profile,
    get_access_request,
    get_admin,
    get_subcontractor_by_email,
    get_subcontractor_by_line_uid,
    list_admins as list_admin_directory_entries,
    list_access_requests as list_access_request_entries,
    list_subcontractors as list_subcontractor_profiles,
    get_subcontractor,
    get_kyc_storage_key,
    reject_access_request,
    reset_subcontractor_line_binding,
    subcontractor_doc_id_for_identity,
    update_admin,
    update_access_request,
    update_subcontractor_profile,
    upsert_admin,
)

router = APIRouter(prefix="/settings", tags=["Admin Settings"])
ADMIN_SUBCONTRACTOR_UPDATE_FIELDS = {
    "name",
    "contact_name",
    "phone",
    "tax_id",
    "bank_account",
}


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
    payload = asdict(entry)
    payload["timezone"] = entry.time
    return AdminDirectoryItem(**payload)


def _access_request_item(entry) -> AccessRequestItem:
    return AccessRequestItem(**asdict(entry))


def _is_self_admin_record(user: AuthenticatedUser, admin_id: str) -> bool:
    return bool(user.email and admin_doc_id_for_email(user.email) == admin_id)


def _reject_self_role_or_status_update(user: AuthenticatedUser, admin_id: str, updates: dict) -> None:
    if not _is_self_admin_record(user, admin_id):
        return
    if "role" not in updates and "roles" not in updates and "is_active" not in updates:
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="You cannot change your own role or active status.",
    )


def _scope_subcontractor_updates(user: AuthenticatedUser, updates: dict) -> dict:
    if user.has_role("owner"):
        return updates

    blocked_fields = sorted(set(updates) - ADMIN_SUBCONTRACTOR_UPDATE_FIELDS)
    if blocked_fields:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Owner access is required to update these subcontractor fields: "
                f"{', '.join(blocked_fields)}."
            ),
        )
    return updates


def _require_owner_for_internal_approval(user: AuthenticatedUser, account_type: str) -> None:
    if account_type == "admin" and not user.has_role("owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner access is required to approve admin or staff accounts.",
        )


def _decision_bank_account(request_bank_account, decision_bank_account) -> dict[str, str | None]:
    bank = decision_bank_account.model_dump() if decision_bank_account is not None else {}
    fallback = request_bank_account or {}
    return {
        "bank_name": bank.get("bank_name") or fallback.get("bank_name"),
        "account_no": bank.get("account_no") or fallback.get("account_no"),
        "account_name": bank.get("account_name") or fallback.get("account_name"),
    }


def _integration_item(
    *,
    key: str,
    label: str,
    category: str,
    description: str,
    configured: bool,
    display_value: str | None = None,
    required_envs: list[str] | None = None,
) -> SettingsIntegrationItem:
    return SettingsIntegrationItem(
        key=key,
        label=label,
        category=category,
        status="configured" if configured else "missing",
        status_label="Configured" if configured else "Missing",
        description=description,
        display_value=display_value if configured else None,
        is_configured=configured,
        read_only=True,
        required_envs=required_envs or [],
    )


def _configured(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        cleaned = value.strip()
        return bool(cleaned and cleaned not in {"change-me", "your-storage-bucket"})
    if isinstance(value, list):
        return bool(value)
    return True


@router.get("/subcontractors", response_model=StandardResponse[list[SubcontractorProfileItem]])
async def list_subcontractors(_user: AuthenticatedUser = Depends(require_admin_user)):
    profiles = list_subcontractor_profiles()
    return StandardResponse(
        data=[await _profile_item(profile) for profile in profiles]
    )


@router.get("/subcontractors/{sub_id}", response_model=StandardResponse[SubcontractorProfileItem])
async def get_subcontractor_detail(
    sub_id: str,
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    profile = get_subcontractor(sub_id)
    return StandardResponse(data=await _profile_item(profile))


@router.put("/subcontractors/{sub_id}", response_model=StandardResponse[SubcontractorProfileItem])
async def update_subcontractor(
    sub_id: str,
    request: UpdateSubcontractorProfileRequest,
    user: AuthenticatedUser = Depends(require_admin_user),
):
    updates = _scope_subcontractor_updates(user, request.model_dump(exclude_none=True))
    profile = update_subcontractor_profile(
        sub_id,
        updates=updates,
    )
    return StandardResponse(data=await _profile_item(profile))


@router.post("/subcontractors/{sub_id}/reset-line", response_model=StandardResponse[SubcontractorProfileItem])
async def reset_line_binding(
    sub_id: str,
    _user: AuthenticatedUser = Depends(require_owner_user),
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


@router.get("/admins/{admin_id}", response_model=StandardResponse[AdminDirectoryItem])
async def get_admin_detail(
    admin_id: str,
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    return StandardResponse(data=_admin_item(get_admin(admin_id)))


@router.post("/admins", response_model=StandardResponse[AdminDirectoryItem])
async def create_admin(
    request: UpsertAdminRequest,
    user: AuthenticatedUser = Depends(require_owner_user),
):
    doc_id = admin_doc_id_for_email(str(request.email))
    _reject_self_role_or_status_update(
        user,
        doc_id,
        {"role": request.role, "roles": request.roles, "is_active": request.is_active},
    )
    entry = upsert_admin(
        email=str(request.email),
        display_name=request.display_name,
        contact_name=request.contact_name,
        phone=request.phone,
        company=request.company,
        department=request.department,
        time=request.time or request.timezone,
        bank_account=(
            request.bank_account.model_dump()
            if request.bank_account is not None
            else None
        ),
        role=request.role,
        roles=request.roles,
        is_active=request.is_active,
        granted_by=user.email or user.subject,
    )
    return StandardResponse(data=_admin_item(entry))


@router.put("/admins/{admin_id}", response_model=StandardResponse[AdminDirectoryItem])
async def edit_admin(
    admin_id: str,
    request: UpdateAdminRequest,
    user: AuthenticatedUser = Depends(require_owner_user),
):
    updates = request.model_dump(exclude_none=True)
    _reject_self_role_or_status_update(user, admin_id, updates)
    entry = update_admin(admin_id, updates=updates)
    return StandardResponse(data=_admin_item(entry))


@router.get("/access-requests", response_model=StandardResponse[list[AccessRequestItem]])
async def list_access_requests(
    status_filter: str = Query(default="pending", alias="status"),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    return StandardResponse(
        data=[_access_request_item(entry) for entry in list_access_request_entries(status_filter)]
    )


@router.post("/access-requests/{request_id}/approve", response_model=StandardResponse[AccessRequestItem])
async def approve_pending_access_request(
    request_id: str,
    request: ApproveAccessRequestRequest,
    user: AuthenticatedUser = Depends(require_admin_user),
):
    _require_owner_for_internal_approval(user, request.account_type)
    access_request = get_access_request(request_id)
    if access_request.status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejected access requests cannot be approved. Ask the user to submit a new request.",
        )

    if request.account_type == "admin":
        if not access_request.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin and staff approvals require a Gmail identity.",
            )
        roles = request.roles or [request.role]
        display_name = request.display_name or access_request.display_name or access_request.contact_name
        entry = upsert_admin(
            email=access_request.email,
            display_name=display_name,
            contact_name=request.contact_name or access_request.contact_name,
            phone=request.phone or access_request.phone,
            company=request.company or access_request.company_name,
            department=request.department,
            time=request.time or request.timezone,
            bank_account=_decision_bank_account(access_request.bank_account, request.bank_account),
            role=request.role,
            roles=roles,
            is_active=True,
            granted_by=user.email or user.subject,
        )
        approved = approve_access_request(
            request_id,
            account_type="admin",
            target_admin_id=entry.id,
            role=entry.role,
            roles=entry.roles,
            decided_by=user.email or user.subject,
        )
        return StandardResponse(data=_access_request_item(approved))

    existing_profile = None
    if request.existing_subcontractor_id:
        existing_profile = get_subcontractor(request.existing_subcontractor_id)
    elif access_request.email:
        existing_profile = get_subcontractor_by_email(access_request.email)
    if existing_profile is None and access_request.line_uid:
        existing_profile = get_subcontractor_by_line_uid(access_request.line_uid)

    name = (
        request.display_name
        or access_request.company_name
        or access_request.display_name
        or access_request.contact_name
        or access_request.email
        or access_request.line_uid
        or "Subcontractor"
    )
    bank_account = _decision_bank_account(access_request.bank_account, request.bank_account)
    subcontractor_updates = {
        "email": access_request.email,
        "line_uid": access_request.line_uid,
        "line_picture_url": access_request.picture_url,
        "name": name,
        "contact_name": request.contact_name or access_request.contact_name or name,
        "phone": request.phone or access_request.phone,
        "tax_id": request.tax_id or access_request.tax_id,
        "kyc_gcs_path": access_request.kyc_gcs_path,
        "bank_account": bank_account,
        "is_active": True,
    }
    if existing_profile is not None:
        profile = update_subcontractor_profile(
            existing_profile.id,
            updates={key: value for key, value in subcontractor_updates.items() if value is not None},
        )
    else:
        profile = create_subcontractor_profile(
            subcontractor_id=subcontractor_doc_id_for_identity(
                email=access_request.email,
                line_uid=access_request.line_uid,
            ),
            email=access_request.email,
            line_uid=access_request.line_uid,
            line_picture_url=access_request.picture_url,
            name=name,
            contact_name=request.contact_name or access_request.contact_name,
            phone=request.phone or access_request.phone,
            tax_id=request.tax_id or access_request.tax_id,
            kyc_gcs_path=access_request.kyc_gcs_path,
            bank_account=bank_account,
        )

    approved = approve_access_request(
        request_id,
        account_type="subcontractor",
        target_subcontractor_id=profile.id,
        decided_by=user.email or user.subject,
    )
    return StandardResponse(data=_access_request_item(approved))


@router.post("/access-requests/{request_id}/reject", response_model=StandardResponse[AccessRequestItem])
async def reject_pending_access_request(
    request_id: str,
    request: RejectAccessRequestRequest,
    user: AuthenticatedUser = Depends(require_admin_user),
):
    rejected = reject_access_request(
        request_id,
        reason=request.reason or "Access request rejected by admin.",
        decided_by=user.email or user.subject,
    )
    return StandardResponse(data=_access_request_item(rejected))


@router.get("/integrations", response_model=StandardResponse[SettingsIntegrationsResponse])
async def get_integrations(_user: AuthenticatedUser = Depends(require_admin_user)):
    settings = get_settings()

    groups = [
        SettingsIntegrationGroup(
            key="google_cloud",
            label="Google Cloud",
            items=[
                _integration_item(
                    key="gcp_project",
                    label="GCP Project",
                    category="google_cloud",
                    description="Project used by Cloud Run, Vertex AI, Firestore, and Cloud Storage.",
                    configured=_configured(settings.gcp_project_id),
                    display_value=settings.gcp_project_id,
                    required_envs=["GCP_PROJECT_ID"],
                ),
                _integration_item(
                    key="application_credentials",
                    label="Application Credentials",
                    category="google_cloud",
                    description="Service account or ADC credentials used for Google APIs.",
                    configured=_configured(settings.google_application_credentials),
                    display_value="Configured",
                    required_envs=["GOOGLE_APPLICATION_CREDENTIALS"],
                ),
                _integration_item(
                    key="gcp_location",
                    label="GCP Location",
                    category="google_cloud",
                    description="Primary region for Vertex AI and regional Google Cloud services.",
                    configured=_configured(settings.gcp_location),
                    display_value=settings.gcp_location,
                    required_envs=["GCP_LOCATION"],
                ),
            ],
        ),
        SettingsIntegrationGroup(
            key="backend",
            label="Backend / API",
            items=[
                _integration_item(
                    key="database",
                    label="Cloud SQL / Database URL",
                    category="backend",
                    description="Primary relational database connection for projects, BOQ, finance, input requests, and chat history.",
                    configured=_configured(settings.database_url),
                    display_value="Configured",
                    required_envs=["DATABASE_URL"],
                ),
                _integration_item(
                    key="session_signing",
                    label="Session Signing",
                    category="backend",
                    description="HMAC session-token signing configuration used by backend auth.",
                    configured=_configured(settings.jwt_secret_key),
                    display_value=f"{settings.jwt_algorithm}, {settings.jwt_expire_minutes} min",
                    required_envs=["JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_EXPIRE_MINUTES"],
                ),
                _integration_item(
                    key="cors",
                    label="CORS Origins",
                    category="backend",
                    description="Allowed frontend origins for browser API access.",
                    configured=True,
                    display_value=(
                        ", ".join(settings.cors_origins)
                        if settings.cors_origins
                        else "Wildcard (*)"
                    ),
                    required_envs=["CORS_ORIGINS"],
                ),
            ],
        ),
        SettingsIntegrationGroup(
            key="firebase",
            label="Firebase",
            items=[
                _integration_item(
                    key="firebase_project",
                    label="Firebase Project",
                    category="firebase",
                    description="Firebase project used for Google admin login token verification.",
                    configured=_configured(settings.firebase_project_id),
                    display_value=settings.firebase_project_id,
                    required_envs=["FIREBASE_PROJECT_ID"],
                ),
                _integration_item(
                    key="firebase_web_api_key",
                    label="Firebase Web API Key",
                    category="firebase",
                    description="Frontend Firebase web API key presence for auth initialization.",
                    configured=_configured(settings.firebase_web_api_key),
                    display_value="Configured",
                    required_envs=["FIREBASE_WEB_API_KEY"],
                ),
                _integration_item(
                    key="firebase_storage_bucket",
                    label="Firebase Storage Bucket",
                    category="firebase",
                    description="Optional Firebase storage bucket reference.",
                    configured=_configured(settings.firebase_storage_bucket),
                    display_value=settings.firebase_storage_bucket,
                    required_envs=["FIREBASE_STORAGE_BUCKET"],
                ),
            ],
        ),
        SettingsIntegrationGroup(
            key="line",
            label="LINE / LIFF",
            items=[
                _integration_item(
                    key="line_channel",
                    label="LINE Channel",
                    category="line",
                    description="LINE channel used for subcontractor LIFF login.",
                    configured=_configured(settings.line_channel_id),
                    display_value=settings.line_channel_id,
                    required_envs=["LINE_CHANNEL_ID", "LINE_CHANNEL_SECRET"],
                ),
                _integration_item(
                    key="line_liff",
                    label="LIFF App",
                    category="line",
                    description="LIFF app ID and callback route for subcontractor login.",
                    configured=_configured(settings.line_liff_id),
                    display_value=settings.line_liff_id,
                    required_envs=["LINE_LIFF_ID", "LINE_REDIRECT_URI"],
                ),
            ],
        ),
        SettingsIntegrationGroup(
            key="storage",
            label="Private Storage",
            items=[
                _integration_item(
                    key="gcs_bucket",
                    label="GCS Bucket",
                    category="storage",
                    description="Private bucket for KYC, profile images, and receipts.",
                    configured=_configured(settings.gcs_bucket_name),
                    display_value=settings.gcs_bucket_name,
                    required_envs=["GCS_BUCKET_NAME"],
                ),
                _integration_item(
                    key="gcs_prefixes",
                    label="Storage Prefixes",
                    category="storage",
                    description="Configured private object prefixes for each storage domain.",
                    configured=True,
                    display_value=", ".join(
                        [
                            settings.gcs_kyc_prefix,
                            settings.gcs_profile_prefix,
                            settings.gcs_temp_bills_prefix,
                            settings.gcs_perm_bills_prefix,
                        ]
                    ),
                    required_envs=[
                        "GCS_KYC_PREFIX",
                        "GCS_PROFILE_PREFIX",
                        "GCS_TEMP_BILLS_PREFIX",
                        "GCS_PERM_BILLS_PREFIX",
                    ],
                ),
            ],
        ),
        SettingsIntegrationGroup(
            key="ai",
            label="AI Services",
            items=[
                _integration_item(
                    key="gemini_model",
                    label="Gemini Model",
                    category="ai",
                    description="Model used for OCR, BOQ parsing, and answer polishing.",
                    configured=_configured(settings.gemini_model),
                    display_value=settings.gemini_model,
                    required_envs=["GEMINI_MODEL"],
                ),
                _integration_item(
                    key="embedding_model",
                    label="Embedding Model",
                    category="ai",
                    description="Model reserved for semantic search and future vector backfill.",
                    configured=_configured(settings.embedding_model),
                    display_value=settings.embedding_model,
                    required_envs=["EMBEDDING_MODEL"],
                ),
            ],
        ),
        SettingsIntegrationGroup(
            key="admin_access",
            label="Admin Access",
            items=[
                _integration_item(
                    key="admin_domain",
                    label="Admin Email Domain",
                    category="admin_access",
                    description="Domain allowlist for first-time admin-side login. Users default to Admin.",
                    configured=_configured(settings.admin_email_domain),
                    display_value=settings.admin_email_domain,
                    required_envs=["ADMIN_EMAIL_DOMAIN"],
                ),
                _integration_item(
                    key="admin_allowlist",
                    label="Admin Email Allowlist",
                    category="admin_access",
                    description="Explicit email allowlist for first-time admin-side login. Users default to Admin.",
                    configured=_configured(settings.admin_emails),
                    display_value=f"{len(settings.admin_emails)} emails",
                    required_envs=["ADMIN_EMAILS"],
                ),
                _integration_item(
                    key="boq_batch_limit",
                    label="BOQ Batch Sync Limit",
                    category="admin_access",
                    description="Maximum Google Sheet tabs queued per BOQ sync batch.",
                    configured=settings.boq_batch_sync_max_tabs > 0,
                    display_value=str(settings.boq_batch_sync_max_tabs),
                    required_envs=["BOQ_BATCH_SYNC_MAX_TABS"],
                ),
            ],
        ),
    ]

    return StandardResponse(
        data=SettingsIntegrationsResponse(
            groups=groups,
            generated_at=datetime.now(UTC),
            read_only=True,
        )
    )
