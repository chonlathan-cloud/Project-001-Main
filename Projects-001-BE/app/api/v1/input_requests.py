"""
Router for the Input page submission flow.

Provides:
  - project options for dropdowns
  - receipt extraction for upload/autofill
  - request submission to Postgres
  - request listing for review/debugging
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.database import get_db
from app.models.boq import Project
from app.models.input_request import InputRequest
from app.schemas.input_schema import (
    BankAccountPayload,
    InputRequestAdminUpdate,
    InputRequestApproveAction,
    InputRequestCreate,
    InputRequestItem,
    InputRequestMarkPaidAction,
    InputRequestRejectAction,
    ProjectOptionItem,
    ReceiptAccessResponse,
    ReceiptExtractResponse,
    ReceiptUploadResponse,
    TempReceiptCleanupResponse,
)
from app.schemas.responses import StandardResponse
from app.services.gcs_storage_service import (
    generate_signed_url_for_storage_key,
    move_input_receipt_to_perm_storage,
    upload_input_receipt_to_temp_storage,
)
from app.services.ai_service import extract_receipt_data_with_gemini
from app.services.input_receipt_cleanup_service import cleanup_orphan_temp_receipts

router = APIRouter(prefix="/input", tags=["Input Requests"])


def _clean_optional_text(value: str | None) -> str | None:
    return (value or "").strip() or None


def _normalize_receipt_no(value: str | None) -> str | None:
    cleaned = _clean_optional_text(value)
    return cleaned.upper() if cleaned else None


def _duplicate_flag_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _validate_request_business_rules(*, entry_type: str, request_type: str | None) -> None:
    if request_type == "ค่าเบิกล่วงหน้า" and entry_type != "EXPENSE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ค่าเบิกล่วงหน้า ใช้ได้เฉพาะรายการรายจ่ายเท่านั้น.",
        )


def _serialize_input_request(item: InputRequest, project_name: str) -> InputRequestItem:
    return InputRequestItem(
        request_id=item.id,
        project_id=item.project_id,
        project_name=project_name,
        subcontractor_id=item.subcontractor_id,
        entry_type=item.entry_type,
        requester_name=item.requester_name,
        phone=item.phone,
        request_date=item.request_date,
        work_type=item.work_type,
        request_type=item.request_type,
        note=item.note,
        vendor_name=item.vendor_name,
        receipt_no=item.receipt_no,
        document_date=item.document_date,
        bank_account=BankAccountPayload(
            bank_name=item.bank_name,
            account_no=item.account_no,
            account_name=item.account_name,
        ),
        amount=float(item.amount or 0),
        approved_amount=float(item.approved_amount) if item.approved_amount is not None else None,
        receipt_file_name=item.receipt_file_name,
        receipt_content_type=item.receipt_content_type,
        receipt_storage_key=item.receipt_storage_key,
        ocr_raw_json=item.ocr_raw_json,
        ocr_low_confidence_fields=item.ocr_low_confidence_fields or [],
        is_duplicate_flag=_duplicate_flag_value(item.is_duplicate_flag),
        duplicate_reason=item.duplicate_reason,
        duplicate_of_request_id=item.duplicate_of_request_id,
        status=item.status,
        review_note=item.review_note,
        reviewed_at=item.reviewed_at,
        approved_at=item.approved_at,
        paid_at=item.paid_at,
        payment_reference=item.payment_reference,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _reviewable_status(status_value: str) -> bool:
    return status_value in {"DRAFT", "PENDING_ADMIN", "REJECTED"}


async def _apply_duplicate_detection(
    db: AsyncSession,
    input_request: InputRequest,
    *,
    exclude_request_id: UUID | None = None,
) -> None:
    receipt_no = _normalize_receipt_no(input_request.receipt_no)
    document_date = input_request.document_date
    amount = input_request.amount

    input_request.receipt_no = receipt_no
    input_request.is_duplicate_flag = False
    input_request.duplicate_reason = None
    input_request.duplicate_of_request_id = None

    if not receipt_no or document_date is None or amount is None:
        return

    query = (
        select(InputRequest)
        .filter(InputRequest.receipt_no == receipt_no)
        .filter(InputRequest.document_date == document_date)
        .filter(InputRequest.amount == amount)
        .order_by(InputRequest.created_at.asc())
    )

    if exclude_request_id is not None:
        query = query.filter(InputRequest.id != exclude_request_id)

    duplicate_match = (await db.execute(query)).scalars().first()
    if duplicate_match is None:
        return

    input_request.is_duplicate_flag = True
    input_request.duplicate_of_request_id = duplicate_match.id
    input_request.duplicate_reason = (
        "Duplicate candidate detected from Receipt No. + Date + Amount "
        f"against request {duplicate_match.id}."
    )


async def _get_input_request_with_project(
    db: AsyncSession,
    request_id: UUID,
) -> tuple[InputRequest, str]:
    row = (
        await db.execute(
            select(InputRequest, Project.name)
            .join(Project, Project.id == InputRequest.project_id)
            .filter(InputRequest.id == request_id)
        )
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Input request {request_id} not found.",
        )

    return row


async def _build_receipt_access_response(
    *,
    input_request: InputRequest,
    expires_in_minutes: int,
) -> ReceiptAccessResponse:
    if not input_request.receipt_storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Input request {input_request.id} does not have a stored receipt file.",
        )

    signed_url = await generate_signed_url_for_storage_key(
        storage_key=input_request.receipt_storage_key,
        expires_in_minutes=expires_in_minutes,
    )

    return ReceiptAccessResponse(
        request_id=input_request.id,
        file_name=input_request.receipt_file_name,
        content_type=input_request.receipt_content_type,
        storage_key=input_request.receipt_storage_key,
        signed_url=signed_url,
        expires_in_minutes=expires_in_minutes,
        message="Signed URL generated successfully.",
    )


@router.get("/projects", response_model=StandardResponse[list[ProjectOptionItem]])
async def list_input_projects(db: AsyncSession = Depends(get_db)):
    """Return project options for the Input page dropdown."""
    try:
        result = await db.execute(select(Project).options(noload("*")).order_by(Project.name))
        projects = result.scalars().all()
        items = [
            ProjectOptionItem(
                id=project.id,
                name=project.name,
                project_type=project.project_type,
                status=project.status,
            )
            for project in projects
        ]
        return StandardResponse(data=items)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load input projects: {exc}",
        ) from exc


@router.post("/receipt-extract", response_model=StandardResponse[ReceiptExtractResponse])
async def extract_input_receipt(file: UploadFile = File(...)):
    """
    Receipt extraction endpoint for the Input page using Gemini OCR.
    """
    try:
        file_bytes = await file.read()
        file_size_bytes = len(file_bytes)
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded receipt file is empty.",
            )
        content_type = file.content_type or "application/octet-stream"
        is_supported_image = content_type.startswith("image/")
        is_supported_pdf = content_type == "application/pdf"
        if not (is_supported_image or is_supported_pdf):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receipt OCR currently supports image files and PDF only.",
            )

        extracted = await extract_receipt_data_with_gemini(
            file_bytes=file_bytes,
            mime_type=content_type,
            file_name=file.filename,
        )

        response = ReceiptExtractResponse(
            file_name=extracted["file_name"],
            content_type=extracted["content_type"],
            file_size_bytes=file_size_bytes,
            suggested_entry_type=extracted["suggested_entry_type"],
            vendor_name=extracted["vendor_name"],
            receipt_no=extracted["receipt_no"],
            document_date=extracted["document_date"],
            suggested_request_type=extracted["suggested_request_type"],
            total_amount=extracted["total_amount"],
            items=extracted["items"],
            ocr_raw_json=extracted["ocr_raw_json"],
            low_confidence_fields=extracted["low_confidence_fields"],
            message=extracted["message"],
        )
        return StandardResponse(data=response)

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract receipt: {exc}",
        ) from exc


@router.post("/receipt-upload", response_model=StandardResponse[ReceiptUploadResponse])
async def upload_input_receipt(file: UploadFile = File(...)):
    """Upload a receipt file to the temporary GCS bucket before submission."""
    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded receipt file is empty.",
            )

        storage_key = await upload_input_receipt_to_temp_storage(
            file_bytes=file_bytes,
            file_name=file.filename,
            content_type=file.content_type,
        )

        return StandardResponse(
            data=ReceiptUploadResponse(
                file_name=file.filename or "uploaded-receipt",
                content_type=file.content_type,
                file_size_bytes=len(file_bytes),
                storage_key=storage_key,
                message="Receipt uploaded to temporary storage.",
            )
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload receipt to storage: {exc}",
        ) from exc


@router.get(
    "/requests/{request_id}/receipt-url",
    response_model=StandardResponse[ReceiptAccessResponse],
)
async def get_input_request_receipt_url(
    request_id: UUID,
    expires_in_minutes: int = Query(default=15, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
):
    """Generate a short-lived signed URL for an input request receipt."""
    try:
        input_request, _project_name = await _get_input_request_with_project(db, request_id)
        return StandardResponse(
            data=await _build_receipt_access_response(
                input_request=input_request,
                expires_in_minutes=expires_in_minutes,
            )
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate receipt signed URL: {exc}",
        ) from exc


@router.get(
    "/admin/requests/{request_id}/receipt-url",
    response_model=StandardResponse[ReceiptAccessResponse],
)
async def get_admin_input_request_receipt_url(
    request_id: UUID,
    expires_in_minutes: int = Query(default=15, ge=1, le=60),
    db: AsyncSession = Depends(get_db),
):
    """Generate a short-lived signed URL for the selected input request receipt."""
    try:
        input_request, _project_name = await _get_input_request_with_project(db, request_id)
        return StandardResponse(
            data=await _build_receipt_access_response(
                input_request=input_request,
                expires_in_minutes=expires_in_minutes,
            )
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate receipt signed URL: {exc}",
        ) from exc


@router.post(
    "/admin/cleanup-temp-receipts",
    response_model=StandardResponse[TempReceiptCleanupResponse],
)
async def cleanup_admin_temp_receipts(
    older_than_hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Delete old temp receipt objects that are no longer referenced in the database."""
    try:
        result = await cleanup_orphan_temp_receipts(
            db=db,
            older_than_hours=older_than_hours,
        )
        return StandardResponse(data=result)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup temp receipts: {exc}",
        ) from exc


@router.post("/requests", response_model=StandardResponse[InputRequestItem])
async def create_input_request(
    request: InputRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create an input request from the frontend form and persist it to Postgres."""
    try:
        project = (
            await db.execute(
                select(Project).options(noload("*")).filter_by(id=request.project_id)
            )
        ).scalar_one_or_none()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {request.project_id} not found.",
            )

        _validate_request_business_rules(
            entry_type=request.entry_type,
            request_type=request.request_type,
        )

        record = InputRequest(
            project_id=request.project_id,
            subcontractor_id=_clean_optional_text(request.subcontractor_id),
            entry_type=request.entry_type,
            requester_name=request.requester_name.strip(),
            phone=_clean_optional_text(request.phone),
            request_date=request.request_date,
            work_type=_clean_optional_text(request.work_type),
            request_type=_clean_optional_text(request.request_type),
            note=_clean_optional_text(request.note),
            vendor_name=_clean_optional_text(request.vendor_name),
            receipt_no=_normalize_receipt_no(request.receipt_no),
            document_date=request.document_date,
            bank_name=_clean_optional_text(request.bank_account.bank_name),
            account_no=_clean_optional_text(request.bank_account.account_no),
            account_name=_clean_optional_text(request.bank_account.account_name),
            amount=Decimal(str(request.amount)),
            receipt_file_name=_clean_optional_text(request.receipt_file_name),
            receipt_content_type=_clean_optional_text(request.receipt_content_type),
            receipt_storage_key=_clean_optional_text(request.receipt_storage_key),
            ocr_raw_json=request.ocr_raw_json,
            ocr_low_confidence_fields=request.ocr_low_confidence_fields,
            status="PENDING_ADMIN",
        )
        db.add(record)
        await db.flush()
        await _apply_duplicate_detection(db, record, exclude_request_id=record.id)
        await db.commit()
        await db.refresh(record)

        return StandardResponse(data=_serialize_input_request(record, project.name))

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create input request: {exc}",
        ) from exc


@router.get("/requests", response_model=StandardResponse[list[InputRequestItem]])
async def list_input_requests(
    entry_type: str | None = Query(default=None, pattern="^(EXPENSE|INCOME)$"),
    status_filter: str | None = Query(default=None, alias="status"),
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List submitted input requests for review or debugging."""
    try:
        query = (
            select(InputRequest, Project.name)
            .join(Project, Project.id == InputRequest.project_id)
            .options(noload("*"))
            .order_by(InputRequest.created_at.desc())
        )

        if entry_type:
            query = query.filter(InputRequest.entry_type == entry_type)
        if status_filter:
            query = query.filter(InputRequest.status == status_filter)
        if project_id:
            query = query.filter(InputRequest.project_id == project_id)

        rows = (await db.execute(query)).all()
        items = [
            _serialize_input_request(item=input_request, project_name=project_name)
            for input_request, project_name in rows
        ]
        return StandardResponse(data=items)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load input requests: {exc}",
        ) from exc


@router.get("/admin/requests", response_model=StandardResponse[list[InputRequestItem]])
async def list_admin_input_requests(
    status_filter: str | None = Query(default="PENDING_ADMIN", alias="status"),
    entry_type: str | None = Query(default=None, pattern="^(EXPENSE|INCOME)$"),
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Admin review queue for input requests."""
    try:
        query = (
            select(InputRequest, Project.name)
            .join(Project, Project.id == InputRequest.project_id)
            .order_by(InputRequest.created_at.desc())
        )

        if status_filter:
            query = query.filter(InputRequest.status == status_filter)
        if entry_type:
            query = query.filter(InputRequest.entry_type == entry_type)
        if project_id:
            query = query.filter(InputRequest.project_id == project_id)

        rows = (await db.execute(query)).all()
        items = [
            _serialize_input_request(item=input_request, project_name=project_name)
            for input_request, project_name in rows
        ]
        return StandardResponse(data=items)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load admin input review queue: {exc}",
        ) from exc


@router.put("/admin/requests/{request_id}", response_model=StandardResponse[InputRequestItem])
async def update_admin_input_request(
    request_id: UUID,
    request: InputRequestAdminUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Admin direct edit before approval, matching the project docs review flow."""
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)

        if not _reviewable_status(input_request.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input request in status '{input_request.status}' can no longer be edited.",
            )

        updates = request.model_dump(exclude_none=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field is required for admin review update.",
            )

        for field, value in updates.items():
            if field == "bank_account":
                input_request.bank_name = _clean_optional_text(value.get("bank_name"))
                input_request.account_no = _clean_optional_text(value.get("account_no"))
                input_request.account_name = _clean_optional_text(value.get("account_name"))
            elif field == "subcontractor_id":
                input_request.subcontractor_id = _clean_optional_text(value)
            elif field == "amount":
                input_request.amount = Decimal(str(value))
            elif field == "receipt_no":
                input_request.receipt_no = _normalize_receipt_no(value)
            elif isinstance(value, str):
                setattr(input_request, field, _clean_optional_text(value))
            else:
                setattr(input_request, field, value)

        _validate_request_business_rules(
            entry_type=input_request.entry_type,
            request_type=input_request.request_type,
        )
        input_request.reviewed_at = datetime.now(timezone.utc)
        await _apply_duplicate_detection(db, input_request, exclude_request_id=input_request.id)
        await db.commit()
        await db.refresh(input_request)

        return StandardResponse(data=_serialize_input_request(input_request, project_name))

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update input request: {exc}",
        ) from exc


@router.post("/admin/requests/{request_id}/approve", response_model=StandardResponse[InputRequestItem])
async def approve_admin_input_request(
    request_id: UUID,
    request: InputRequestApproveAction,
    db: AsyncSession = Depends(get_db),
):
    """Approve an input request after review."""
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)

        if not _reviewable_status(input_request.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input request in status '{input_request.status}' cannot be approved.",
            )

        approved_amount = request.approved_amount or float(input_request.amount or 0)
        if approved_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved amount must be greater than 0.",
            )

        now = datetime.now(timezone.utc)
        input_request.approved_amount = Decimal(str(approved_amount))
        input_request.review_note = (request.review_note or "").strip() or None
        input_request.receipt_storage_key = await move_input_receipt_to_perm_storage(
            storage_key=input_request.receipt_storage_key,
            request_id=input_request.id,
        )
        input_request.status = "APPROVED"
        input_request.reviewed_at = now
        input_request.approved_at = now

        await db.commit()
        await db.refresh(input_request)

        return StandardResponse(data=_serialize_input_request(input_request, project_name))

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve input request: {exc}",
        ) from exc


@router.post("/admin/requests/{request_id}/reject", response_model=StandardResponse[InputRequestItem])
async def reject_admin_input_request(
    request_id: UUID,
    request: InputRequestRejectAction,
    db: AsyncSession = Depends(get_db),
):
    """Reject an input request and record the review note."""
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)

        if not _reviewable_status(input_request.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input request in status '{input_request.status}' cannot be rejected.",
            )

        input_request.status = "REJECTED"
        input_request.review_note = request.review_note.strip()
        input_request.reviewed_at = datetime.now(timezone.utc)
        input_request.approved_at = None
        input_request.approved_amount = None

        await db.commit()
        await db.refresh(input_request)

        return StandardResponse(data=_serialize_input_request(input_request, project_name))

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject input request: {exc}",
        ) from exc


@router.post("/admin/requests/{request_id}/mark-paid", response_model=StandardResponse[InputRequestItem])
async def mark_paid_admin_input_request(
    request_id: UUID,
    request: InputRequestMarkPaidAction,
    db: AsyncSession = Depends(get_db),
):
    """Move an approved input request into paid state after transfer is completed."""
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)

        if input_request.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only approved input requests can be marked paid. Current status: '{input_request.status}'.",
            )

        now = datetime.now(timezone.utc)
        input_request.status = "PAID"
        input_request.paid_at = now
        input_request.reviewed_at = now
        input_request.payment_reference = _clean_optional_text(request.payment_reference)
        if request.review_note is not None:
            input_request.review_note = _clean_optional_text(request.review_note)

        await db.commit()
        await db.refresh(input_request)

        return StandardResponse(data=_serialize_input_request(input_request, project_name))

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark input request as paid: {exc}",
        ) from exc
