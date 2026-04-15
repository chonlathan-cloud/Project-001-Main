"""
Authentication Router — LINE Login + Sign Up / KYC Flow.

Endpoints:
  POST /api/v1/auth/line-login   → Verify LINE token, return JWT or REQUIRE_SIGNUP
  POST /api/v1/auth/sign-up      → Register new user with KYC image upload
"""

from fastapi import APIRouter, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.schemas.responses import StandardResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------
class LineLoginRequest(BaseModel):
    """Request body for LINE Login verification."""
    line_access_token: str


# ---------------------------------------------------------------------------
# POST /api/v1/auth/line-login
# ---------------------------------------------------------------------------
@router.post("/line-login", response_model=StandardResponse[dict])
async def line_login(request: LineLoginRequest):
    """
    Verify the LINE access token and check if the user exists.

    Flow (BRD §1.1):
      1. Call LINE API to verify token and retrieve LINE UID.
      2. Look up line_uid in Firestore users collection.
      3a. If user exists → generate Custom JWT Token → return it.
      3b. If new user → return REQUIRE_SIGNUP with line_uid so the
          frontend can redirect to the registration form.
    """
    try:
        # TODO: Call LINE API  →  https://api.line.me/v2/profile
        #       Headers: { "Authorization": f"Bearer {request.line_access_token}" }
        mock_line_uid = "U1234567890abcdef"

        # TODO: Query Firestore → users collection where line_uid == mock_line_uid
        user_exists = False  # Simulate new user for demo

        if user_exists:
            # Existing user → return JWT
            return StandardResponse(
                data={
                    "status": "SUCCESS",
                    "line_uid": mock_line_uid,
                    "token": "mock_jwt_token_for_existing_user",
                    "user": {
                        "id": "sub_001",
                        "name": "ABC Construction Co., Ltd.",
                    },
                }
            )
        else:
            # New user → frontend must redirect to sign-up form
            return StandardResponse(
                data={
                    "status": "REQUIRE_SIGNUP",
                    "line_uid": mock_line_uid,
                    "message": "User not found. Please complete registration.",
                }
            )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LINE login failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# POST /api/v1/auth/sign-up  (First-time registration + KYC)
# ---------------------------------------------------------------------------
@router.post("/sign-up", response_model=StandardResponse[dict])
async def sign_up(
    line_uid: str = Form(..., description="LINE UID from the login step"),
    name: str = Form(..., description="Company or subcontractor name"),
    tax_id: str = Form(..., description="Tax Identification Number"),
    kyc_image: UploadFile = None,
):
    """
    Register a new subcontractor with KYC compliance (BRD §1.2).

    Flow:
      1. Upload ID card image to GCS Private Bucket (/kyc_id_cards).
      2. Save subcontractor profile to Firestore users collection
         (including line_uid, name, tax_id, gcs path, default rates).
      3. Generate and return a Custom JWT Token via Firebase Auth.

    Security:
      - KYC images stored in Private Bucket (no public access).
      - Admin views via Signed URL only (15 min expiry, PDPA compliant).
    """
    try:
        # 1. Upload KYC image to GCS
        gcs_path = None
        if kyc_image is not None:
            # TODO: Upload to GCS Private Bucket
            # file_bytes = await kyc_image.read()
            # blob = bucket.blob(f"kyc_id_cards/{line_uid}.jpg")
            # blob.upload_from_string(file_bytes, content_type=kyc_image.content_type)
            gcs_path = f"gs://PLACEHOLDER_BUCKET/kyc_id_cards/{line_uid}.jpg"

        # 2. Save profile to Firestore
        # TODO: Write to Firestore users collection
        user_profile = {
            "doc_id": line_uid,
            "line_uid": line_uid,
            "name": name,
            "tax_id": tax_id,
            "vat_rate": 0.07,
            "wht_rate": 0.03,
            "retention_rate": 0.05,
            "bank_account": None,
            "kyc_gcs_path": gcs_path,
        }

        # 3. Generate Firebase Custom Token
        # TODO: firebase_admin.auth.create_custom_token(line_uid)
        mock_token = f"mock_jwt_token_for_{line_uid}"

        return StandardResponse(
            data={
                "status": "SUCCESS",
                "message": "Registration completed successfully.",
                "token": mock_token,
                "user": user_profile,
            }
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sign-up failed: {exc}",
        ) from exc
