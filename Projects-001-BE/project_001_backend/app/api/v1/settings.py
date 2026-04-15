"""
Router 7: Admin Settings — Subcontractor Profile Management.
Uses Firestore for profile data (users collection).
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.schemas.responses import StandardResponse

router = APIRouter(prefix="/settings", tags=["Admin Settings"])


# ---------------------------------------------------------------------------
# Request schema for profile update
# ---------------------------------------------------------------------------
class UpdateSubcontractorRequest(BaseModel):
    """Request body for updating subcontractor financial rates."""
    name: str | None = None
    vat_rate: float | None = None
    wht_rate: float | None = None
    retention_rate: float | None = None


# ---------------------------------------------------------------------------
# GET /api/v1/settings/subcontractors  (list all)
# ---------------------------------------------------------------------------
@router.get("/subcontractors", response_model=StandardResponse[list[dict]])
async def list_subcontractors():
    """
    Return all subcontractor profiles from Firestore.
    Currently returns placeholder data; will integrate Firestore SDK.
    """
    # TODO: Fetch from Firestore users collection
    mock_data = [
        {
            "id": "sub_001",
            "name": "ABC Construction Co., Ltd.",
            "tax_id": "1234567890123",
            "vat_rate": 0.07,
            "wht_rate": 0.03,
            "retention_rate": 0.05,
        },
        {
            "id": "sub_002",
            "name": "Thai Electrical Services",
            "tax_id": "9876543210987",
            "vat_rate": 0.07,
            "wht_rate": 0.03,
            "retention_rate": 0.05,
        },
    ]
    return StandardResponse(data=mock_data)


# ---------------------------------------------------------------------------
# PUT /api/v1/settings/subcontractors/{id}  (update profile)
# ---------------------------------------------------------------------------
@router.put(
    "/subcontractors/{sub_id}",
    response_model=StandardResponse[dict],
)
async def update_subcontractor(
    sub_id: str,
    request: UpdateSubcontractorRequest,
):
    """
    Update subcontractor profile (VAT, WHT, retention rates) in Firestore.
    """
    # TODO: Update Firestore document in users collection
    return StandardResponse(
        data={
            "id": sub_id,
            "message": "Subcontractor profile updated.",
            "updated_fields": request.model_dump(exclude_none=True),
        }
    )


# ---------------------------------------------------------------------------
# POST /api/v1/settings/subcontractors/{id}/reset-line
# ---------------------------------------------------------------------------
@router.post(
    "/subcontractors/{sub_id}/reset-line",
    response_model=StandardResponse[dict],
)
async def reset_line_binding(sub_id: str):
    """
    Delete the existing line_uid to allow the subcontractor to bind
    a new LINE account (BRD §1.3 Account Recovery).
    """
    # TODO: Set line_uid to null in Firestore users/{sub_id}
    return StandardResponse(
        data={
            "id": sub_id,
            "message": "LINE binding has been reset. Subcontractor can now link a new account.",
        }
    )


# ---------------------------------------------------------------------------
# GET /api/v1/users/{id}/kyc-image  (Signed URL)
# ---------------------------------------------------------------------------
@router.get(
    "/users/{user_id}/kyc-image",
    response_model=StandardResponse[dict],
)
async def get_kyc_image(user_id: str):
    """
    Generate a GCS Signed URL (15 min) for viewing the KYC ID card photo.
    PDPA compliant — link expires automatically (BRD §1.2).
    """
    # TODO: Use GCS service account to generate signed URL
    return StandardResponse(
        data={
            "user_id": user_id,
            "signed_url": f"https://storage.googleapis.com/PLACEHOLDER_BUCKET/kyc_id_cards/{user_id}.jpg?signed=true",
            "expires_in_minutes": 15,
            "message": "Signed URL generated. Valid for 15 minutes.",
        }
    )
