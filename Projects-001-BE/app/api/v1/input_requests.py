"""
Router for the Input page submission flow.

Provides:
  - project options for dropdowns
  - receipt extraction mock for upload/autofill
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
    ReceiptExtractResponse,
)
from app.schemas.responses import StandardResponse

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


def _serialize_input_request(item: InputRequest, project_name: str) -> InputRequestItem:
    return InputRequestItem(
        request_id=item.id,
        project_id=item.project_id,
        project_name=project_name,
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
    Temporary receipt extraction endpoint for the Input page.

    The response is intentionally deterministic so the frontend can wire up the
    upload/autofill flow before OCR integration is implemented.
    """
    try:
        file_bytes = await file.read()
        file_size_bytes = len(file_bytes)

        response = ReceiptExtractResponse(
            file_name=file.filename or "uploaded-receipt",
            content_type=file.content_type,
            file_size_bytes=file_size_bytes,
            suggested_entry_type="EXPENSE",
            vendor_name="Temporary OCR Vendor",
            receipt_no="INV-2026-001",
            document_date="2026-04-12",
            suggested_request_type="วัสดุ",
            total_amount=15500.00,
            items=[
                {"description": "Cement", "qty": 100, "price": 155.00},
            ],
            message="Receipt extracted with mock OCR response.",
        )
        return StandardResponse(data=response)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract receipt: {exc}",
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

        record = InputRequest(
            project_id=request.project_id,
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
            elif field == "amount":
                input_request.amount = Decimal(str(value))
            elif field == "receipt_no":
                input_request.receipt_no = _normalize_receipt_no(value)
            elif isinstance(value, str):
                setattr(input_request, field, _clean_optional_text(value))
            else:
                setattr(input_request, field, value)

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
