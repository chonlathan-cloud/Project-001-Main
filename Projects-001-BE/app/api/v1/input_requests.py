"""
Router for the Input page submission flow.

Provides:
  - project options for dropdowns
  - receipt extraction for upload/autofill
  - request submission to Postgres
  - request listing for review/debugging
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.api.deps.auth import (
    AuthenticatedUser,
    get_current_user,
    require_admin_user,
    require_owner_user,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.models.boq import Project
from app.models.input_request import (
    InputOptionSuggestion,
    InputPayment,
    InputPaymentConfirmation,
    InputPaymentReferenceCounter,
    InputRequest,
    InputRequestLineItem,
)
from app.schemas.input_schema import (
    BankAccountPayload,
    DEFAULT_WORK_TYPE_OPTIONS,
    FlowAccountLinkExistingAction,
    FlowAccountReadinessResponse,
    FlowAccountSyncAction,
    InputDefaultValuesResponse,
    InputPaymentAwaitingConfirmationItem,
    InputPaymentConfirmationAccessResponse,
    InputPaymentConfirmationItem,
    InputPaymentConfirmationReviewAction,
    InputPaymentConfirmationSummaryItem,
    InputRequestAdminSummaryResponse,
    InputRequestAdminUpdate,
    InputRequestApproveAction,
    InputRequestCreate,
    InputRequestItem,
    InputRequestLineItemItem,
    InputRequestLineItemPayload,
    InputRequestMarkPaidAction,
    InputRequestRejectAction,
    InputRequestStatusSummaryItem,
    ProjectOptionItem,
    ReceiptAccessResponse,
    ReceiptExtractResponse,
    ReceiptUploadResponse,
    TempReceiptCleanupResponse,
)
from app.schemas.responses import StandardResponse
from app.services.gcs_storage_service import (
    delete_storage_key,
    download_storage_key_bytes,
    generate_signed_url_for_storage_key,
    move_input_receipt_to_perm_storage,
    organize_input_receipt_in_paid_storage,
    paid_document_storage_prefix,
    upload_payment_confirmation_to_storage,
    upload_input_receipt_to_temp_storage,
)
from app.services.ai_service import extract_receipt_data_with_gemini
from app.services.flowaccount_service import (
    FlowAccountError,
    FlowAccountReadiness,
    FlowAccountService,
    apply_readiness_to_request,
    flowaccount_document_data,
    flowaccount_document_no,
    flowaccount_external_document_id,
    flowaccount_readiness,
    flowaccount_record_id,
)
from app.services.identity_service import get_subcontractor
from app.services.input_receipt_cleanup_service import cleanup_orphan_temp_receipts

router = APIRouter(prefix="/input", tags=["Input Requests"])
logger = logging.getLogger(__name__)

COMPANY_PROJECT_NAME = "โครงการบริษัท"
COMPANY_PROJECT_TYPE = "INTERNAL"
OPTION_TYPE_TAG = "TAG"
OPTION_TYPE_WORK_TYPE = "WORK_TYPE"
THAILAND_TIMEZONE = timezone(timedelta(hours=7))
PAYMENT_CONFIRMATION_CONTENT_TYPES = {
    "application/pdf",
    "image/heic",
    "image/heif",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


def _clean_optional_text(value: str | None) -> str | None:
    return (value or "").strip() or None


def _normalize_receipt_no(value: str | None) -> str | None:
    cleaned = _clean_optional_text(value)
    return cleaned.upper() if cleaned else None


def _normalize_vendor_tax_id(value: str | None) -> str | None:
    cleaned = "".join(character for character in str(value or "") if character.isdigit())
    return cleaned or None


def _duplicate_flag_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _money_value(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _decimal_money(value: object) -> Decimal:
    return Decimal(str(round(_money_value(value), 2)))


def _format_payment_reference(entry_type: str, sequence: int, payment_date: date) -> str:
    normalized_entry_type = str(entry_type or "").strip().upper()
    if normalized_entry_type not in {"EXPENSE", "INCOME"}:
        raise ValueError("Payment references support EXPENSE or INCOME entries only.")
    prefix = "E" if normalized_entry_type == "EXPENSE" else "IN"
    return f"{prefix}{sequence:03d}{payment_date:%d%m%Y}"


async def _next_payment_reference(
    db: AsyncSession,
    *,
    entry_type: str,
    payment_date: date,
) -> tuple[int, str]:
    normalized_entry_type = str(entry_type or "").strip().upper()
    counter_table = InputPaymentReferenceCounter.__table__
    statement = (
        postgresql_insert(counter_table)
        .values(
            reference_date=payment_date,
            entry_type=normalized_entry_type,
            last_sequence=1,
        )
        .on_conflict_do_update(
            index_elements=[
                counter_table.c.reference_date,
                counter_table.c.entry_type,
            ],
            set_={
                "last_sequence": counter_table.c.last_sequence + 1,
                "updated_at": func.now(),
            },
        )
        .returning(counter_table.c.last_sequence)
    )
    sequence = int((await db.execute(statement)).scalar_one())
    return sequence, _format_payment_reference(
        normalized_entry_type,
        sequence,
        payment_date,
    )


def _latest_payment_confirmation(
    payment: InputPayment | None,
) -> InputPaymentConfirmation | None:
    if not payment:
        return None
    confirmations = list(payment.confirmations or [])
    return confirmations[0] if confirmations else None


def _confirmation_status(payment: InputPayment | None) -> str | None:
    if not payment:
        return None
    latest = _latest_payment_confirmation(payment)
    return latest.status if latest else "AWAITING_SUBMISSION"


async def _read_payment_confirmation_upload(file: UploadFile) -> tuple[bytes, str]:
    content_type = str(file.content_type or "application/octet-stream").lower().split(";", 1)[0]
    if content_type not in PAYMENT_CONFIRMATION_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment confirmation supports JPG, PNG, WEBP, HEIC, HEIF, or PDF files.",
        )
    max_bytes = get_settings().payment_confirmation_max_bytes
    chunks: list[bytes] = []
    total_bytes = 0
    while chunk := await file.read(1024 * 1024):
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Payment confirmation exceeds the {max_bytes // (1024 * 1024)}MB limit.",
            )
        chunks.append(chunk)
    file_bytes = b"".join(chunks)
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded payment confirmation is empty.",
        )
    prefix = file_bytes[:32]
    signature_valid = True
    if content_type in {"image/jpeg", "image/jpg"}:
        signature_valid = prefix.startswith(b"\xff\xd8\xff")
    elif content_type == "image/png":
        signature_valid = prefix.startswith(b"\x89PNG\r\n\x1a\n")
    elif content_type == "image/webp":
        signature_valid = prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP"
    elif content_type in {"image/heic", "image/heif"}:
        signature_valid = prefix[4:8] == b"ftyp"
    elif content_type == "application/pdf":
        signature_valid = prefix.startswith(b"%PDF-")
    if not signature_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded payment confirmation does not match its declared file type.",
        )
    return file_bytes, content_type


def _clean_unique_text_values(values: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        cleaned = _clean_optional_text(value)
        if cleaned is None:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def _merge_option_values(*groups: list[str]) -> list[str]:
    return _clean_unique_text_values([item for group in groups for item in group])


def _request_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return _clean_unique_text_values([str(item) for item in value if item is not None])


def _validate_request_business_rules(*, entry_type: str, request_type: str | None) -> None:
    if request_type == "ค่าเบิกล่วงหน้า" and entry_type != "EXPENSE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ค่าเบิกล่วงหน้า ใช้ได้เฉพาะรายการรายจ่ายเท่านั้น.",
        )


def _validate_entry_type_for_user(
    *,
    user: AuthenticatedUser,
    entry_type: str,
) -> None:
    if user.role == "subcontractor" and entry_type != "EXPENSE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="บัญชีผู้รับเหมาส่งคำขอได้เฉพาะรายการรายจ่ายเท่านั้น.",
        )


def _line_item_total(line_items: list[InputRequestLineItemPayload]) -> Decimal:
    return sum((_decimal_money(item.amount) for item in line_items), Decimal("0"))


def _build_line_item_records(
    line_items: list[InputRequestLineItemPayload],
    *,
    entry_type: str,
    fallback_work_type: str | None = None,
    fallback_request_type: str | None = None,
) -> list[InputRequestLineItem]:
    records: list[InputRequestLineItem] = []
    is_income = entry_type == "INCOME"

    for index, item in enumerate(line_items, start=1):
        records.append(
            InputRequestLineItem(
                line_no=index,
                description=item.description.strip(),
                qty=Decimal(str(item.qty)),
                unit_price=_decimal_money(item.unit_price),
                amount=_decimal_money(item.amount),
                work_type=None if is_income else _clean_optional_text(item.work_type or fallback_work_type),
                request_type=None if is_income else _clean_optional_text(item.request_type or fallback_request_type),
            )
        )

    return records


def _serialize_line_item(item: InputRequestLineItem) -> InputRequestLineItemItem:
    return InputRequestLineItemItem(
        id=item.id,
        line_no=item.line_no,
        description=item.description,
        qty=float(item.qty or 0),
        unit_price=float(item.unit_price or 0),
        amount=float(item.amount or 0),
        work_type=item.work_type,
        request_type=item.request_type,
    )


def _serialize_input_request(item: InputRequest, project_name: str) -> InputRequestItem:
    payment = item.payment
    latest_confirmation = _latest_payment_confirmation(payment)
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
        tags=_request_tags(item.tags),
        note=item.note,
        vendor_name=item.vendor_name,
        vendor_tax_id=item.vendor_tax_id,
        vendor_branch=item.vendor_branch,
        vendor_address=item.vendor_address,
        receipt_no=item.receipt_no,
        document_date=item.document_date,
        accounting_vat_mode=item.accounting_vat_mode,
        accounting_wht_rate=float(item.accounting_wht_rate) if item.accounting_wht_rate is not None else None,
        bank_account=BankAccountPayload(
            bank_name=item.bank_name,
            account_no=item.account_no,
            account_name=item.account_name,
        ),
        amount=float(item.amount or 0),
        approved_amount=float(item.approved_amount) if item.approved_amount is not None else None,
        line_items=[
            _serialize_line_item(line_item)
            for line_item in sorted(
                item.line_items or [],
                key=lambda line_item: (line_item.line_no or 0, str(line_item.id or "")),
            )
        ],
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
        payment_id=payment.id if payment else None,
        internal_payment_reference=payment.internal_reference if payment else None,
        payment_date=payment.payment_date if payment else None,
        bank_transfer_reference=payment.bank_transfer_reference if payment else None,
        paid_storage_prefix=payment.paid_storage_prefix if payment else None,
        payment_confirmation_status=_confirmation_status(payment),
        latest_payment_confirmation_id=latest_confirmation.id if latest_confirmation else None,
        accounting_ready=bool(item.accounting_ready),
        accounting_readiness_errors=item.accounting_readiness_errors or [],
        flowaccount_sync_status=item.flowaccount_sync_status or "NOT_READY",
        flowaccount_expense_id=item.flowaccount_expense_id,
        flowaccount_document_no=item.flowaccount_document_no,
        flowaccount_external_document_id=item.flowaccount_external_document_id,
        flowaccount_synced_at=item.flowaccount_synced_at,
        flowaccount_sync_error=item.flowaccount_sync_error,
        flowaccount_attachment_status=item.flowaccount_attachment_status or "NOT_READY",
        flowaccount_attachment_error=item.flowaccount_attachment_error,
        flowaccount_attachment_synced_at=item.flowaccount_attachment_synced_at,
        flowaccount_supplier_invoice_status=item.flowaccount_supplier_invoice_status or "NOT_READY",
        flowaccount_supplier_invoice_error=item.flowaccount_supplier_invoice_error,
        flowaccount_supplier_invoice_id=item.flowaccount_supplier_invoice_id,
        flowaccount_supplier_invoice_synced_at=item.flowaccount_supplier_invoice_synced_at,
        flowaccount_payment_status=item.flowaccount_payment_status or "NOT_READY",
        flowaccount_payment_error=item.flowaccount_payment_error,
        flowaccount_payment_synced_at=item.flowaccount_payment_synced_at,
        flowaccount_linked_manually=bool(item.flowaccount_linked_manually),
        flowaccount_duplicate_override_reason=item.flowaccount_duplicate_override_reason,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _reviewable_status(status_value: str) -> bool:
    return status_value in {"DRAFT", "PENDING_ADMIN", "REJECTED"}


def _editable_status(status_value: str) -> bool:
    return status_value in {"DRAFT", "PENDING_ADMIN", "REJECTED", "APPROVED"}


def _readiness_response(readiness: FlowAccountReadiness) -> FlowAccountReadinessResponse:
    return FlowAccountReadinessResponse(
        enabled=readiness.enabled,
        ready=readiness.ready,
        can_sync_expense=readiness.can_sync_expense,
        can_sync_attachment=readiness.can_sync_attachment,
        can_sync_supplier_invoice=readiness.can_sync_supplier_invoice,
        can_mark_paid=readiness.can_mark_paid,
        missing_fields=readiness.missing_fields,
        errors=readiness.errors,
        external_document_id=readiness.external_document_id,
    )


def _expense_id_from_request(input_request: InputRequest) -> str:
    expense_id = _clean_optional_text(input_request.flowaccount_expense_id)
    if not expense_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FlowAccount expense id is required before this action.",
        )
    return expense_id


async def _refresh_accounting_readiness(
    db: AsyncSession,
    input_request: InputRequest,
    project_name: str | None,
) -> FlowAccountReadiness:
    readiness = flowaccount_readiness(input_request, project_name=project_name)
    apply_readiness_to_request(input_request, readiness)
    await db.flush()
    return readiness


async def _download_request_receipt(input_request: InputRequest) -> bytes:
    if not input_request.receipt_storage_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt file is required before syncing to FlowAccount.",
        )
    try:
        return await download_storage_key_bytes(input_request.receipt_storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt file was not found in storage.",
        ) from exc


def _apply_flowaccount_document_result(input_request: InputRequest, payload: dict) -> None:
    input_request.flowaccount_expense_id = flowaccount_record_id(payload) or input_request.flowaccount_expense_id
    input_request.flowaccount_document_no = flowaccount_document_no(payload) or input_request.flowaccount_document_no
    input_request.flowaccount_sync_error = None
    input_request.flowaccount_synced_at = datetime.now(timezone.utc)


def _resolve_subcontractor_id_for_create(
    request: InputRequestCreate,
    user: AuthenticatedUser,
) -> str | None:
    if user.role == "subcontractor":
        if not user.subcontractor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subcontractor session does not include subcontractor_id.",
            )
        return user.subcontractor_id

    return _clean_optional_text(request.subcontractor_id)


def _require_subcontractor_identity(user: AuthenticatedUser) -> str:
    if not user.has_role("subcontractor") or not user.subcontractor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A verified subcontractor session is required.",
        )
    return user.subcontractor_id


def _assigned_project_ids_for_subcontractor(user: AuthenticatedUser) -> set[UUID]:
    if user.role != "subcontractor":
        return set()
    if not user.subcontractor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subcontractor session does not include subcontractor_id.",
        )

    profile = get_subcontractor(user.subcontractor_id)
    assigned_project_ids: set[UUID] = set()
    for raw_value in profile.assigned_project_ids:
        try:
            assigned_project_ids.add(UUID(str(raw_value)))
        except (TypeError, ValueError):
            continue
    return assigned_project_ids


def _filter_input_requests_for_user(query, user: AuthenticatedUser):
    if user.role == "subcontractor":
        if not user.subcontractor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subcontractor session does not include subcontractor_id.",
            )
        return query.filter(InputRequest.subcontractor_id == user.subcontractor_id)

    return query


def _is_company_project(project: Project) -> bool:
    return (
        project.name == COMPANY_PROJECT_NAME
        and str(project.project_type or "").upper() == COMPANY_PROJECT_TYPE
    )


async def _load_suggestion_values(db: AsyncSession, option_type: str) -> list[str]:
    result = await db.execute(
        select(InputOptionSuggestion.value)
        .filter(InputOptionSuggestion.option_type == option_type)
        .order_by(InputOptionSuggestion.value.asc())
    )
    return _clean_unique_text_values(list(result.scalars().all()))


async def _load_work_type_options(db: AsyncSession) -> list[str]:
    custom_values = await _load_suggestion_values(db, OPTION_TYPE_WORK_TYPE)
    return _merge_option_values(DEFAULT_WORK_TYPE_OPTIONS, custom_values)


async def _load_tag_options(db: AsyncSession) -> list[str]:
    suggestion_values = await _load_suggestion_values(db, OPTION_TYPE_TAG)
    tag_rows = await db.execute(select(InputRequest.tags).where(InputRequest.tags.is_not(None)))
    stored_tags = [
        tag
        for tags in tag_rows.scalars().all()
        for tag in _request_tags(tags)
    ]
    return _merge_option_values(suggestion_values, stored_tags)


async def _upsert_option_suggestions(
    db: AsyncSession,
    option_type: str,
    values: list[str],
) -> None:
    normalized_values = _clean_unique_text_values(values)
    if not normalized_values:
        return

    existing_values = await _load_suggestion_values(db, option_type)
    existing_keys = {value.casefold() for value in existing_values}
    for value in normalized_values:
        key = value.casefold()
        if key in existing_keys:
            continue
        db.add(InputOptionSuggestion(option_type=option_type, value=value))
        existing_keys.add(key)


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
            .options(selectinload(InputRequest.line_items))
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
async def list_input_projects(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return project options for the Input page dropdown."""
    try:
        query = select(Project).options(noload("*")).order_by(Project.name)
        if user.role == "subcontractor":
            assigned_project_ids = _assigned_project_ids_for_subcontractor(user)
            if assigned_project_ids:
                query = query.filter(
                    or_(
                        Project.id.in_(assigned_project_ids),
                        Project.name == COMPANY_PROJECT_NAME,
                    )
                )
            else:
                query = query.filter(Project.name == COMPANY_PROJECT_NAME)

        result = await db.execute(query)
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


@router.get("/defaults", response_model=StandardResponse[InputDefaultValuesResponse])
async def get_input_defaults(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return default subcontractor values used to prefill the Input page."""
    try:
        work_types = await _load_work_type_options(db)
        tags = await _load_tag_options(db)

        if user.role != "subcontractor":
            return StandardResponse(
                data=InputDefaultValuesResponse(work_types=work_types, tags=tags)
            )

        if not user.subcontractor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subcontractor session does not include subcontractor_id.",
            )

        profile = get_subcontractor(user.subcontractor_id)
        return StandardResponse(
            data=InputDefaultValuesResponse(
                requester_name=profile.contact_name or profile.name,
                phone=profile.phone,
                bank_account=BankAccountPayload(
                    bank_name=profile.bank_account.get("bank_name"),
                    account_no=profile.bank_account.get("account_no"),
                    account_name=profile.bank_account.get("account_name"),
                ),
                work_types=work_types,
                tags=tags,
            )
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load input defaults: {exc}",
        ) from exc


@router.post("/receipt-extract", response_model=StandardResponse[ReceiptExtractResponse])
async def extract_input_receipt(
    file: UploadFile = File(...),
    _user: AuthenticatedUser = Depends(get_current_user),
):
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
            vendor_tax_id=extracted["vendor_tax_id"],
            vendor_branch=extracted["vendor_branch"],
            vendor_address=extracted["vendor_address"],
            receipt_no=extracted["receipt_no"],
            document_date=extracted["document_date"],
            suggested_request_type=extracted["suggested_request_type"],
            suggested_accounting_vat_mode=extracted["suggested_accounting_vat_mode"],
            total_amount=extracted["total_amount"],
            subtotal_amount=extracted["subtotal_amount"],
            vat_amount=extracted["vat_amount"],
            vat_rate=extracted["vat_rate"],
            line_items_total=extracted["line_items_total"],
            line_items_complete=extracted["line_items_complete"],
            page_count=extracted["page_count"],
            warnings=extracted["warnings"],
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
async def upload_input_receipt(
    file: UploadFile = File(...),
    _user: AuthenticatedUser = Depends(get_current_user),
):
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
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a short-lived signed URL for an input request receipt."""
    try:
        input_request, _project_name = await _get_input_request_with_project(db, request_id)
        if user.role == "subcontractor" and input_request.subcontractor_id != user.subcontractor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This input request does not belong to the current subcontractor.",
            )

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
    _user: AuthenticatedUser = Depends(require_admin_user),
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


async def _get_payment_context(
    db: AsyncSession,
    payment_id: UUID,
) -> tuple[InputPayment, InputRequest, str]:
    row = (
        await db.execute(
            select(InputPayment, InputRequest, Project.name)
            .join(InputRequest, InputRequest.id == InputPayment.input_request_id)
            .join(Project, Project.id == InputRequest.project_id)
            .options(selectinload(InputPayment.confirmations))
            .where(InputPayment.id == payment_id)
        )
    ).one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )
    return row[0], row[1], row[2]


async def _get_confirmation_context(
    db: AsyncSession,
    confirmation_id: UUID,
) -> tuple[InputPaymentConfirmation, InputPayment, InputRequest, str]:
    row = (
        await db.execute(
            select(
                InputPaymentConfirmation,
                InputPayment,
                InputRequest,
                Project.name,
            )
            .join(InputPayment, InputPayment.id == InputPaymentConfirmation.payment_id)
            .join(InputRequest, InputRequest.id == InputPayment.input_request_id)
            .join(Project, Project.id == InputRequest.project_id)
            .where(InputPaymentConfirmation.id == confirmation_id)
        )
    ).one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment confirmation not found.",
        )
    return row[0], row[1], row[2], row[3]


def _serialize_payment_confirmation(
    confirmation: InputPaymentConfirmation,
    payment: InputPayment,
    input_request: InputRequest,
    project_name: str,
) -> InputPaymentConfirmationItem:
    return InputPaymentConfirmationItem(
        confirmation_id=confirmation.id,
        payment_id=payment.id,
        request_id=input_request.id,
        project_id=input_request.project_id,
        project_name=project_name,
        subcontractor_id=confirmation.subcontractor_id,
        internal_reference=payment.internal_reference,
        payment_date=payment.payment_date,
        amount=float(payment.amount or 0),
        version=confirmation.version,
        status=confirmation.status,
        received_date=confirmation.received_date,
        received_full_amount=bool(confirmation.received_full_amount),
        note=confirmation.note,
        file_name=confirmation.file_name,
        content_type=confirmation.content_type,
        size_bytes=confirmation.size_bytes,
        submitted_at=confirmation.submitted_at,
        verified_at=confirmation.verified_at,
        verified_by=confirmation.verified_by,
        verification_note=confirmation.verification_note,
    )


@router.get(
    "/me/payments/awaiting-confirmation",
    response_model=StandardResponse[list[InputPaymentAwaitingConfirmationItem]],
)
async def list_my_payments_awaiting_confirmation(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subcontractor_id = _require_subcontractor_identity(user)
    rows = (
        await db.execute(
            select(InputPayment, InputRequest, Project.name)
            .join(InputRequest, InputRequest.id == InputPayment.input_request_id)
            .join(Project, Project.id == InputRequest.project_id)
            .options(selectinload(InputPayment.confirmations))
            .where(
                InputRequest.subcontractor_id == subcontractor_id,
                InputRequest.entry_type == "EXPENSE",
                InputRequest.status == "PAID",
            )
            .order_by(InputPayment.payment_date.desc(), InputPayment.recorded_at.desc())
        )
    ).all()
    items: list[InputPaymentAwaitingConfirmationItem] = []
    for payment, input_request, project_name in rows:
        latest = _latest_payment_confirmation(payment)
        confirmation_status = latest.status if latest else "AWAITING_SUBMISSION"
        if confirmation_status not in {"AWAITING_SUBMISSION", "CHANGES_REQUESTED"}:
            continue
        items.append(
            InputPaymentAwaitingConfirmationItem(
                payment_id=payment.id,
                request_id=input_request.id,
                project_id=input_request.project_id,
                project_name=project_name,
                requester_name=input_request.requester_name,
                request_type=input_request.request_type,
                amount=float(payment.amount or 0),
                payment_date=payment.payment_date,
                internal_reference=payment.internal_reference,
                confirmation_status=confirmation_status,
                latest_confirmation_id=latest.id if latest else None,
            )
        )
    return StandardResponse(data=items)


@router.get(
    "/me/payments/payment-confirmations",
    response_model=StandardResponse[list[InputPaymentConfirmationSummaryItem]],
)
async def list_my_payment_confirmation_statuses(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return paid expenses with their latest technician confirmation state."""

    subcontractor_id = _require_subcontractor_identity(user)
    rows = (
        await db.execute(
            select(InputPayment, InputRequest, Project.name)
            .join(InputRequest, InputRequest.id == InputPayment.input_request_id)
            .join(Project, Project.id == InputRequest.project_id)
            .options(selectinload(InputPayment.confirmations))
            .where(
                InputRequest.subcontractor_id == subcontractor_id,
                InputRequest.entry_type == "EXPENSE",
                InputRequest.status == "PAID",
            )
            .order_by(InputPayment.payment_date.desc(), InputPayment.recorded_at.desc())
        )
    ).all()

    items: list[InputPaymentConfirmationSummaryItem] = []
    for payment, input_request, project_name in rows:
        latest = _latest_payment_confirmation(payment)
        confirmation_status = latest.status if latest else "AWAITING_SUBMISSION"
        items.append(
            InputPaymentConfirmationSummaryItem(
                payment_id=payment.id,
                request_id=input_request.id,
                project_id=input_request.project_id,
                project_name=project_name,
                requester_name=input_request.requester_name,
                request_type=input_request.request_type,
                amount=float(payment.amount or 0),
                payment_date=payment.payment_date,
                internal_reference=payment.internal_reference,
                confirmation_status=confirmation_status,
                action_required=confirmation_status
                in {"AWAITING_SUBMISSION", "CHANGES_REQUESTED"},
                latest_confirmation_id=latest.id if latest else None,
                latest_confirmation_version=latest.version if latest else None,
                latest_received_date=latest.received_date if latest else None,
                latest_received_full_amount=(
                    bool(latest.received_full_amount) if latest else None
                ),
                latest_note=latest.note if latest else None,
                latest_file_name=latest.file_name if latest else None,
                latest_content_type=latest.content_type if latest else None,
                latest_submitted_at=latest.submitted_at if latest else None,
                latest_verified_at=latest.verified_at if latest else None,
                latest_verification_note=(
                    latest.verification_note if latest else None
                ),
            )
        )
    return StandardResponse(data=items)


@router.post(
    "/me/payments/{payment_id}/confirmation",
    response_model=StandardResponse[InputPaymentConfirmationItem],
)
async def submit_my_payment_confirmation(
    payment_id: UUID,
    file: UploadFile = File(...),
    received_date: date = Form(...),
    received_full_amount: bool = Form(True),
    note: str | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subcontractor_id = _require_subcontractor_identity(user)
    payment, input_request, project_name = await _get_payment_context(db, payment_id)
    if (
        input_request.subcontractor_id != subcontractor_id
        or input_request.entry_type != "EXPENSE"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This payment does not belong to the current subcontractor.",
        )
    if input_request.status != "PAID":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment confirmation can be submitted only after the request is paid.",
        )

    normalized_idempotency_key = _clean_optional_text(idempotency_key)
    if normalized_idempotency_key and len(normalized_idempotency_key) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must not exceed 200 characters.",
        )
    if normalized_idempotency_key:
        existing = (
            await db.execute(
                select(InputPaymentConfirmation).where(
                    InputPaymentConfirmation.payment_id == payment_id,
                    InputPaymentConfirmation.idempotency_key == normalized_idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return StandardResponse(
                data=_serialize_payment_confirmation(
                    existing,
                    payment,
                    input_request,
                    project_name,
                )
            )

    latest = _latest_payment_confirmation(payment)
    if latest and latest.status in {"SUBMITTED", "VERIFIED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A payment confirmation is already awaiting review."
                if latest.status == "SUBMITTED"
                else "This payment confirmation has already been verified."
            ),
        )

    file_bytes, content_type = await _read_payment_confirmation_upload(file)
    version = max([item.version for item in payment.confirmations or []] or [0]) + 1
    confirmation_id = uuid4()
    storage_key: str | None = None
    committed = False
    try:
        storage_key = await upload_payment_confirmation_to_storage(
            file_bytes=file_bytes,
            file_name=file.filename,
            content_type=content_type,
            payment_date=payment.payment_date,
            internal_reference=payment.internal_reference,
            confirmation_id=confirmation_id,
            version=version,
        )
        now = datetime.now(timezone.utc)
        if latest:
            latest.status = "SUPERSEDED"
            latest.superseded_at = now
        confirmation = InputPaymentConfirmation(
            id=confirmation_id,
            payment_id=payment.id,
            subcontractor_id=subcontractor_id,
            idempotency_key=normalized_idempotency_key,
            version=version,
            status="SUBMITTED",
            received_date=received_date,
            received_full_amount=received_full_amount,
            note=_clean_optional_text(note),
            file_name=file.filename or f"payment-confirmation-{confirmation_id}",
            content_type=content_type,
            size_bytes=len(file_bytes),
            storage_key=storage_key,
            submitted_at=now,
        )
        db.add(confirmation)
        await db.commit()
        committed = True
        await db.refresh(confirmation)
        return StandardResponse(
            data=_serialize_payment_confirmation(
                confirmation,
                payment,
                input_request,
                project_name,
            )
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        if storage_key and not committed:
            await delete_storage_key(storage_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit payment confirmation: {exc}",
        ) from exc


@router.get(
    "/payment-confirmations/{confirmation_id}/signed-url",
    response_model=StandardResponse[InputPaymentConfirmationAccessResponse],
)
async def get_payment_confirmation_signed_url(
    confirmation_id: UUID,
    expires_in_minutes: int = Query(default=15, ge=1, le=60),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    confirmation, _payment, input_request, _project_name = await _get_confirmation_context(
        db,
        confirmation_id,
    )
    is_owner = (
        user.has_role("subcontractor")
        and input_request.subcontractor_id == user.subcontractor_id
    )
    if not is_owner and not user.has_any_role({"admin", "owner"}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Payment confirmation access is not allowed.",
        )
    signed_url = await generate_signed_url_for_storage_key(
        storage_key=confirmation.storage_key,
        expires_in_minutes=expires_in_minutes,
    )
    return StandardResponse(
        data=InputPaymentConfirmationAccessResponse(
            confirmation_id=confirmation.id,
            url=signed_url,
            expires_in_minutes=expires_in_minutes,
            file_name=confirmation.file_name,
            content_type=confirmation.content_type,
        )
    )


@router.get(
    "/admin/payment-confirmations",
    response_model=StandardResponse[list[InputPaymentConfirmationItem]],
)
async def list_admin_payment_confirmations(
    confirmation_status: str | None = Query(default=None, alias="status"),
    _user: AuthenticatedUser = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(InputPaymentConfirmation, InputPayment, InputRequest, Project.name)
        .join(InputPayment, InputPayment.id == InputPaymentConfirmation.payment_id)
        .join(InputRequest, InputRequest.id == InputPayment.input_request_id)
        .join(Project, Project.id == InputRequest.project_id)
        .order_by(InputPaymentConfirmation.submitted_at.desc())
    )
    if confirmation_status:
        statement = statement.where(
            InputPaymentConfirmation.status == confirmation_status.strip().upper()
        )
    rows = (await db.execute(statement)).all()
    return StandardResponse(
        data=[
            _serialize_payment_confirmation(
                confirmation,
                payment,
                input_request,
                project_name,
            )
            for confirmation, payment, input_request, project_name in rows
        ]
    )


@router.post(
    "/admin/payment-confirmations/{confirmation_id}/review",
    response_model=StandardResponse[InputPaymentConfirmationItem],
)
async def review_payment_confirmation(
    confirmation_id: UUID,
    request: InputPaymentConfirmationReviewAction,
    user: AuthenticatedUser = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    confirmation, payment, input_request, project_name = await _get_confirmation_context(
        db,
        confirmation_id,
    )
    if confirmation.status != "SUBMITTED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only submitted payment confirmations can be reviewed.",
        )
    now = datetime.now(timezone.utc)
    confirmation.status = (
        "VERIFIED" if request.action == "VERIFY" else "CHANGES_REQUESTED"
    )
    confirmation.verified_at = now if request.action == "VERIFY" else None
    confirmation.verified_by = user.subject if request.action == "VERIFY" else None
    confirmation.verification_note = request.note
    await db.commit()
    await db.refresh(confirmation)
    return StandardResponse(
        data=_serialize_payment_confirmation(
            confirmation,
            payment,
            input_request,
            project_name,
        )
    )


@router.post(
    "/admin/cleanup-temp-receipts",
    response_model=StandardResponse[TempReceiptCleanupResponse],
)
async def cleanup_admin_temp_receipts(
    older_than_hours: int = Query(default=24, ge=1, le=168),
    _user: AuthenticatedUser = Depends(require_owner_user),
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
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an input request from the frontend form and persist it to Postgres."""
    try:
        _validate_entry_type_for_user(user=user, entry_type=request.entry_type)

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

        if user.role == "subcontractor":
            assigned_project_ids = _assigned_project_ids_for_subcontractor(user)
            if request.project_id not in assigned_project_ids and not _is_company_project(project):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This subcontractor is not assigned to the selected project.",
                )

        _validate_request_business_rules(
            entry_type=request.entry_type,
            request_type=request.request_type,
        )

        stored_work_type = None if request.entry_type == "INCOME" else _clean_optional_text(request.work_type)
        stored_request_type = None if request.entry_type == "INCOME" else _clean_optional_text(request.request_type)
        stored_tags = _request_tags(request.tags)
        stored_amount = _decimal_money(request.amount)

        record = InputRequest(
            project_id=request.project_id,
            subcontractor_id=_resolve_subcontractor_id_for_create(request, user),
            entry_type=request.entry_type,
            requester_name=request.requester_name.strip(),
            phone=_clean_optional_text(request.phone),
            request_date=request.request_date,
            work_type=stored_work_type,
            request_type=stored_request_type,
            tags=stored_tags,
            note=_clean_optional_text(request.note),
            vendor_name=_clean_optional_text(request.vendor_name),
            vendor_tax_id=_normalize_vendor_tax_id(request.vendor_tax_id),
            vendor_branch=_clean_optional_text(request.vendor_branch),
            vendor_address=_clean_optional_text(request.vendor_address),
            receipt_no=_normalize_receipt_no(request.receipt_no),
            document_date=request.document_date,
            accounting_vat_mode=_clean_optional_text(request.accounting_vat_mode),
            bank_name=_clean_optional_text(request.bank_account.bank_name),
            account_no=_clean_optional_text(request.bank_account.account_no),
            account_name=_clean_optional_text(request.bank_account.account_name),
            amount=stored_amount,
            receipt_file_name=_clean_optional_text(request.receipt_file_name),
            receipt_content_type=_clean_optional_text(request.receipt_content_type),
            receipt_storage_key=_clean_optional_text(request.receipt_storage_key),
            ocr_raw_json=request.ocr_raw_json,
            ocr_low_confidence_fields=request.ocr_low_confidence_fields,
            status="PENDING_ADMIN",
        )
        if request.line_items:
            record.line_items = _build_line_item_records(
                request.line_items,
                entry_type=request.entry_type,
                fallback_work_type=stored_work_type,
                fallback_request_type=stored_request_type,
            )
        db.add(record)
        await db.flush()
        await _apply_duplicate_detection(db, record, exclude_request_id=record.id)
        if stored_work_type:
            await _upsert_option_suggestions(db, OPTION_TYPE_WORK_TYPE, [stored_work_type])
        line_item_work_types = [
            line_item.work_type
            for line_item in record.line_items or []
            if line_item.work_type
        ]
        if line_item_work_types:
            await _upsert_option_suggestions(db, OPTION_TYPE_WORK_TYPE, line_item_work_types)
        if stored_tags:
            await _upsert_option_suggestions(db, OPTION_TYPE_TAG, stored_tags)
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
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List submitted input requests for review or debugging."""
    try:
        query = (
            select(InputRequest, Project.name)
            .join(Project, Project.id == InputRequest.project_id)
            .options(selectinload(InputRequest.line_items), noload(InputRequest.project))
            .order_by(InputRequest.created_at.desc())
        )
        query = _filter_input_requests_for_user(query, user)

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
    _user: AuthenticatedUser = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin review queue for input requests."""
    try:
        query = (
            select(InputRequest, Project.name)
            .join(Project, Project.id == InputRequest.project_id)
            .options(selectinload(InputRequest.line_items), noload(InputRequest.project))
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


@router.get(
    "/admin/requests/summary",
    response_model=StandardResponse[InputRequestAdminSummaryResponse],
)
async def get_admin_input_requests_summary(
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        rows = (
            await db.execute(select(InputRequest).options(noload("*")))
        ).scalars().all()

        status_map: dict[str, dict[str, float | int]] = {}
        total_amount = 0.0
        duplicate_count = 0
        paid_amount = 0.0

        for item in rows:
            status_key = str(item.status or "UNKNOWN").upper()
            amount = _money_value(
                item.approved_amount if item.approved_amount is not None else item.amount
            )
            total_amount += amount
            if _duplicate_flag_value(item.is_duplicate_flag):
                duplicate_count += 1
            if status_key == "PAID":
                paid_amount += amount
            if status_key not in status_map:
                status_map[status_key] = {"count": 0, "amount": 0.0}
            status_map[status_key]["count"] = int(status_map[status_key]["count"]) + 1
            status_map[status_key]["amount"] = _money_value(status_map[status_key]["amount"]) + amount

        pending = status_map.get("PENDING_ADMIN", {"count": 0, "amount": 0.0})
        paid = status_map.get("PAID", {"count": 0, "amount": 0.0})

        return StandardResponse(
            data=InputRequestAdminSummaryResponse(
                total_count=len(rows),
                total_amount=round(total_amount, 2),
                pending_count=int(pending["count"]),
                pending_amount=round(_money_value(pending["amount"]), 2),
                duplicate_count=duplicate_count,
                paid_count=int(paid["count"]),
                paid_amount=round(paid_amount, 2),
                by_status=[
                    InputRequestStatusSummaryItem(
                        status=status_key,
                        count=int(values["count"]),
                        amount=round(_money_value(values["amount"]), 2),
                    )
                    for status_key, values in sorted(status_map.items())
                ],
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to summarize input requests: {exc}",
        ) from exc


@router.get("/admin/requests/{request_id}", response_model=StandardResponse[InputRequestItem])
async def get_admin_input_request_detail(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: AuthenticatedUser = Depends(require_admin_user),
):
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)
        return StandardResponse(
            data=_serialize_input_request(input_request, project_name)
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch input request {request_id}: {exc}",
        ) from exc


@router.put("/admin/requests/{request_id}", response_model=StandardResponse[InputRequestItem])
async def update_admin_input_request(
    request_id: UUID,
    request: InputRequestAdminUpdate,
    _user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin direct edit before approval, matching the project docs review flow."""
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)

        if not _editable_status(input_request.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Input request in status '{input_request.status}' can no longer be edited.",
            )
        requested_fields = set(request.model_fields_set)
        has_line_item_updates = "line_items" in requested_fields
        update_field_names = requested_fields - {"line_items"}
        flowaccount_safe_update_fields = {
            "review_note",
            "payment_reference",
            "vendor_tax_id",
            "vendor_branch",
            "vendor_address",
            "receipt_no",
        }
        is_flowaccount_safe_update = not has_line_item_updates and update_field_names <= flowaccount_safe_update_fields

        if input_request.status == "APPROVED" and input_request.flowaccount_payment_status == "PAYMENT_SYNCED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input request can no longer be edited after FlowAccount payment sync.",
            )
        if (
            input_request.status == "APPROVED"
            and input_request.flowaccount_expense_id
            and not is_flowaccount_safe_update
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input request can no longer be edited after a FlowAccount document is linked or created.",
            )

        line_item_updates = request.line_items if has_line_item_updates else None
        if has_line_item_updates and line_item_updates is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="line_items cannot be null when provided.",
            )
        updates = request.model_dump(exclude_unset=True, exclude={"line_items"})
        if not updates and not has_line_item_updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field is required for admin review update.",
            )

        for field, value in updates.items():
            if field == "bank_account":
                input_request.bank_name = _clean_optional_text(value.get("bank_name")) if value else None
                input_request.account_no = _clean_optional_text(value.get("account_no")) if value else None
                input_request.account_name = _clean_optional_text(value.get("account_name")) if value else None
            elif field == "tags":
                input_request.tags = _request_tags(value)
            elif field == "subcontractor_id":
                input_request.subcontractor_id = _clean_optional_text(value)
            elif field == "amount":
                input_request.amount = Decimal(str(value))
            elif field == "receipt_no":
                input_request.receipt_no = _normalize_receipt_no(value)
            elif field == "vendor_tax_id":
                input_request.vendor_tax_id = _normalize_vendor_tax_id(value)
            elif field == "accounting_wht_rate":
                input_request.accounting_wht_rate = Decimal(str(value)) if value is not None else None
            elif isinstance(value, str):
                setattr(input_request, field, _clean_optional_text(value))
            else:
                setattr(input_request, field, value)

        if line_item_updates is not None:
            input_request.line_items = _build_line_item_records(
                line_item_updates,
                entry_type=input_request.entry_type,
                fallback_work_type=input_request.work_type,
                fallback_request_type=input_request.request_type,
            )
            input_request.amount = _line_item_total(line_item_updates)

        if input_request.entry_type == "INCOME":
            input_request.work_type = None
            input_request.request_type = None
            for line_item in input_request.line_items or []:
                line_item.work_type = None
                line_item.request_type = None
            if "tags" in updates and not _request_tags(input_request.tags):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="INCOME requests require at least 1 tag.",
                )

        _validate_request_business_rules(
            entry_type=input_request.entry_type,
            request_type=input_request.request_type,
        )
        input_request.reviewed_at = datetime.now(timezone.utc)
        await _apply_duplicate_detection(db, input_request, exclude_request_id=input_request.id)
        if input_request.work_type:
            await _upsert_option_suggestions(db, OPTION_TYPE_WORK_TYPE, [input_request.work_type])
        line_item_work_types = [
            line_item.work_type
            for line_item in input_request.line_items or []
            if line_item.work_type
        ]
        if line_item_work_types:
            await _upsert_option_suggestions(db, OPTION_TYPE_WORK_TYPE, line_item_work_types)
        if input_request.tags:
            await _upsert_option_suggestions(db, OPTION_TYPE_TAG, _request_tags(input_request.tags))
        if input_request.status == "APPROVED":
            await _refresh_accounting_readiness(db, input_request, project_name)
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
    _user: AuthenticatedUser = Depends(require_owner_user),
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
        if request.line_items is not None:
            input_request.line_items = _build_line_item_records(
                request.line_items,
                entry_type=input_request.entry_type,
                fallback_work_type=input_request.work_type,
                fallback_request_type=input_request.request_type,
            )
            input_request.amount = _line_item_total(request.line_items)
            approved_amount = float(input_request.amount or 0)
        input_request.approved_amount = Decimal(str(approved_amount))
        input_request.review_note = (request.review_note or "").strip() or None
        input_request.receipt_storage_key = await move_input_receipt_to_perm_storage(
            storage_key=input_request.receipt_storage_key,
            request_id=input_request.id,
        )
        input_request.status = "APPROVED"
        input_request.reviewed_at = now
        input_request.approved_at = now

        await _apply_duplicate_detection(db, input_request, exclude_request_id=input_request.id)
        line_item_work_types = [
            line_item.work_type
            for line_item in input_request.line_items or []
            if line_item.work_type
        ]
        if line_item_work_types:
            await _upsert_option_suggestions(db, OPTION_TYPE_WORK_TYPE, line_item_work_types)
        await _refresh_accounting_readiness(db, input_request, project_name)
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
    _user: AuthenticatedUser = Depends(require_owner_user),
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


@router.get(
    "/admin/requests/{request_id}/accounting-readiness",
    response_model=StandardResponse[FlowAccountReadinessResponse],
)
async def get_input_request_accounting_readiness(
    request_id: UUID,
    _user: AuthenticatedUser = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)
        readiness = await _refresh_accounting_readiness(db, input_request, project_name)
        await db.commit()
        return StandardResponse(data=_readiness_response(readiness))

    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check accounting readiness: {exc}",
        ) from exc


@router.post("/admin/requests/{request_id}/sync-flowaccount", response_model=StandardResponse[InputRequestItem])
async def sync_input_request_to_flowaccount(
    request_id: UUID,
    request: FlowAccountSyncAction,
    _user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)

        if input_request.is_duplicate_flag and not input_request.flowaccount_duplicate_override_reason:
            if not request.override_duplicate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Duplicate-flagged requests require Owner confirmation before FlowAccount sync.",
                )
            input_request.flowaccount_duplicate_override_reason = (
                request.override_reason or "Owner confirmed duplicate FlowAccount sync in Approval."
            )

        readiness = await _refresh_accounting_readiness(db, input_request, project_name)
        if not readiness.can_sync_expense:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FlowAccount sync is not ready: " + "; ".join(readiness.missing_fields + readiness.errors),
            )

        service = FlowAccountService()
        now = datetime.now(timezone.utc)

        if not input_request.flowaccount_expense_id:
            input_request.flowaccount_sync_status = "SYNCING"
            input_request.flowaccount_sync_error = None
            await db.flush()
            try:
                payload = await service.create_expense(input_request, project_name=project_name)
            except FlowAccountError as exc:
                input_request.flowaccount_sync_status = "FAILED"
                input_request.flowaccount_sync_error = str(exc)
                await db.commit()
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

            _apply_flowaccount_document_result(input_request, payload)
            input_request.flowaccount_sync_status = "SYNCED"

        receipt_bytes: bytes | None = None
        if input_request.receipt_storage_key and input_request.flowaccount_attachment_status != "SYNCED":
            input_request.flowaccount_attachment_status = "SYNCING"
            input_request.flowaccount_attachment_error = None
            await db.flush()
            try:
                receipt_bytes = await _download_request_receipt(input_request)
                await service.attach_expense_receipt(
                    expense_id=_expense_id_from_request(input_request),
                    file_bytes=receipt_bytes,
                    file_name=input_request.receipt_file_name,
                    content_type=input_request.receipt_content_type,
                )
                input_request.flowaccount_attachment_status = "SYNCED"
                input_request.flowaccount_attachment_synced_at = now
            except (FlowAccountError, HTTPException) as exc:
                input_request.flowaccount_sync_status = "PARTIAL_SYNC"
                input_request.flowaccount_attachment_status = "FAILED"
                input_request.flowaccount_attachment_error = str(exc.detail if isinstance(exc, HTTPException) else exc)

        readiness = await _refresh_accounting_readiness(db, input_request, project_name)
        if input_request.accounting_vat_mode in {"vat_inclusive", "vat_exclusive"}:
            if input_request.flowaccount_supplier_invoice_status != "SYNCED" and readiness.can_sync_supplier_invoice:
                input_request.flowaccount_supplier_invoice_status = "SYNCING"
                input_request.flowaccount_supplier_invoice_error = None
                await db.flush()
                try:
                    if receipt_bytes is None:
                        receipt_bytes = await _download_request_receipt(input_request)
                    payload = await service.create_supplier_invoice(
                        input_request,
                        expense_id=_expense_id_from_request(input_request),
                        file_bytes=receipt_bytes,
                        file_name=input_request.receipt_file_name,
                    )
                    supplier_data = flowaccount_document_data(payload)
                    input_request.flowaccount_supplier_invoice_id = (
                        str(supplier_data.get("recordId") or supplier_data.get("documentId") or "")
                        or input_request.flowaccount_supplier_invoice_id
                    )
                    input_request.flowaccount_supplier_invoice_status = "SYNCED"
                    input_request.flowaccount_supplier_invoice_synced_at = now
                except (FlowAccountError, HTTPException) as exc:
                    input_request.flowaccount_supplier_invoice_status = "FAILED"
                    input_request.flowaccount_supplier_invoice_error = str(exc.detail if isinstance(exc, HTTPException) else exc)
            elif input_request.flowaccount_supplier_invoice_status != "SYNCED":
                input_request.flowaccount_supplier_invoice_status = "NOT_READY"
                input_request.flowaccount_supplier_invoice_error = None
        elif input_request.flowaccount_supplier_invoice_status != "SYNCED":
            input_request.flowaccount_supplier_invoice_status = "NOT_REQUIRED"
            input_request.flowaccount_supplier_invoice_error = None

        readiness = await _refresh_accounting_readiness(db, input_request, project_name)
        payment = input_request.payment
        if (
            input_request.status == "PAID"
            and payment
            and input_request.flowaccount_payment_status != "PAYMENT_SYNCED"
        ):
            if readiness.can_mark_paid:
                input_request.flowaccount_payment_status = "SYNCING"
                input_request.flowaccount_payment_error = None
                await db.flush()
                try:
                    await service.create_expense_payment(
                        input_request,
                        expense_id=_expense_id_from_request(input_request),
                        payment_date=payment.payment_date,
                        payment_reference=payment.internal_reference,
                    )
                    input_request.flowaccount_payment_status = "PAYMENT_SYNCED"
                    input_request.flowaccount_payment_synced_at = now
                except FlowAccountError as exc:
                    input_request.flowaccount_payment_status = "PAYMENT_FAILED"
                    input_request.flowaccount_payment_error = str(exc)
            else:
                input_request.flowaccount_payment_status = "NOT_READY"

        await _refresh_accounting_readiness(db, input_request, project_name)
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
            detail=f"Failed to sync FlowAccount expense: {exc}",
        ) from exc


@router.post("/admin/requests/{request_id}/retry-flowaccount-attachment", response_model=StandardResponse[InputRequestItem])
async def retry_input_request_flowaccount_attachment(
    request_id: UUID,
    _user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)
        service = FlowAccountService()
        input_request.flowaccount_attachment_status = "SYNCING"
        input_request.flowaccount_attachment_error = None
        await db.flush()
        try:
            receipt_bytes = await _download_request_receipt(input_request)
            await service.attach_expense_receipt(
                expense_id=_expense_id_from_request(input_request),
                file_bytes=receipt_bytes,
                file_name=input_request.receipt_file_name,
                content_type=input_request.receipt_content_type,
            )
            input_request.flowaccount_attachment_status = "SYNCED"
            input_request.flowaccount_attachment_synced_at = datetime.now(timezone.utc)
            if input_request.flowaccount_sync_status == "PARTIAL_SYNC":
                input_request.flowaccount_sync_status = "SYNCED"
        except (FlowAccountError, HTTPException) as exc:
            input_request.flowaccount_attachment_status = "FAILED"
            input_request.flowaccount_attachment_error = str(exc.detail if isinstance(exc, HTTPException) else exc)

        await _refresh_accounting_readiness(db, input_request, project_name)
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
            detail=f"Failed to retry FlowAccount attachment: {exc}",
        ) from exc


@router.post("/admin/requests/{request_id}/retry-flowaccount-supplier-invoice", response_model=StandardResponse[InputRequestItem])
async def retry_input_request_flowaccount_supplier_invoice(
    request_id: UUID,
    _user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)
        readiness = await _refresh_accounting_readiness(db, input_request, project_name)
        if not readiness.can_sync_supplier_invoice:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier Invoice is not ready: " + "; ".join(readiness.missing_fields + readiness.errors),
            )

        service = FlowAccountService()
        input_request.flowaccount_supplier_invoice_status = "SYNCING"
        input_request.flowaccount_supplier_invoice_error = None
        await db.flush()
        try:
            receipt_bytes = await _download_request_receipt(input_request)
            payload = await service.create_supplier_invoice(
                input_request,
                expense_id=_expense_id_from_request(input_request),
                file_bytes=receipt_bytes,
                file_name=input_request.receipt_file_name,
            )
            supplier_data = flowaccount_document_data(payload)
            input_request.flowaccount_supplier_invoice_id = (
                str(supplier_data.get("recordId") or supplier_data.get("documentId") or "")
                or input_request.flowaccount_supplier_invoice_id
            )
            input_request.flowaccount_supplier_invoice_status = "SYNCED"
            input_request.flowaccount_supplier_invoice_synced_at = datetime.now(timezone.utc)
            if (
                input_request.flowaccount_sync_status == "PARTIAL_SYNC"
                and input_request.flowaccount_attachment_status == "SYNCED"
            ):
                input_request.flowaccount_sync_status = "SYNCED"
        except (FlowAccountError, HTTPException) as exc:
            input_request.flowaccount_supplier_invoice_status = "FAILED"
            input_request.flowaccount_supplier_invoice_error = str(exc.detail if isinstance(exc, HTTPException) else exc)

        await _refresh_accounting_readiness(db, input_request, project_name)
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
            detail=f"Failed to retry FlowAccount Supplier Invoice: {exc}",
        ) from exc


@router.post("/admin/requests/{request_id}/link-flowaccount-document", response_model=StandardResponse[InputRequestItem])
async def link_existing_flowaccount_document(
    request_id: UUID,
    request: FlowAccountLinkExistingAction,
    _user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)

        if input_request.entry_type != "EXPENSE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only expense input requests can be linked to FlowAccount documents.",
            )
        if input_request.status not in {"APPROVED", "PAID"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only approved or paid requests can be linked to FlowAccount documents.",
            )

        input_request.flowaccount_expense_id = request.expense_id
        input_request.flowaccount_document_no = request.document_no
        input_request.flowaccount_external_document_id = request.external_document_id or flowaccount_external_document_id(input_request.id)
        input_request.flowaccount_linked_manually = True
        input_request.flowaccount_sync_status = "SYNCED"
        input_request.flowaccount_sync_error = None
        input_request.flowaccount_synced_at = datetime.now(timezone.utc)
        if request.note:
            input_request.review_note = request.note

        await _refresh_accounting_readiness(db, input_request, project_name)
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
            detail=f"Failed to link FlowAccount document: {exc}",
        ) from exc


@router.post("/admin/requests/{request_id}/mark-paid", response_model=StandardResponse[InputRequestItem])
async def mark_paid_admin_input_request(
    request_id: UUID,
    request: InputRequestMarkPaidAction,
    user: AuthenticatedUser = Depends(require_owner_user),
    db: AsyncSession = Depends(get_db),
):
    """Record an internal payment independently from external accounting sync."""
    original_receipt_storage_key: str | None = None
    paid_receipt_storage_key: str | None = None
    committed = False
    try:
        input_request, project_name = await _get_input_request_with_project(db, request_id)

        if input_request.status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only approved input requests can be marked paid. Current status: '{input_request.status}'.",
            )

        if input_request.payment:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This input request already has a recorded payment.",
            )

        now = datetime.now(timezone.utc)
        payment_date = request.payment_date or datetime.now(THAILAND_TIMEZONE).date()
        sequence, internal_reference = await _next_payment_reference(
            db,
            entry_type=input_request.entry_type,
            payment_date=payment_date,
        )
        bank_transfer_reference = _clean_optional_text(request.payment_reference)
        input_request.payment_reference = bank_transfer_reference
        if request.review_note is not None:
            input_request.review_note = _clean_optional_text(request.review_note)

        original_receipt_storage_key = input_request.receipt_storage_key
        paid_receipt_storage_key = await organize_input_receipt_in_paid_storage(
            storage_key=original_receipt_storage_key,
            request_id=input_request.id,
            payment_date=payment_date,
            internal_reference=internal_reference,
        )
        input_request.receipt_storage_key = paid_receipt_storage_key

        payment = InputPayment(
            input_request=input_request,
            internal_reference=internal_reference,
            sequence_number=sequence,
            payment_date=payment_date,
            amount=(
                input_request.approved_amount
                if input_request.approved_amount is not None
                else input_request.amount
            ),
            bank_transfer_reference=bank_transfer_reference,
            paid_storage_prefix=paid_document_storage_prefix(
                payment_date,
                internal_reference,
            ),
            recorded_by=user.subject,
            recorded_at=now,
        )
        db.add(payment)

        input_request.status = "PAID"
        input_request.paid_at = now
        input_request.reviewed_at = now
        input_request.flowaccount_payment_status = (
            "NOT_SYNCED" if input_request.entry_type == "EXPENSE" else "NOT_REQUIRED"
        )
        input_request.flowaccount_payment_error = None

        await db.flush()
        await _refresh_accounting_readiness(db, input_request, project_name)
        await db.commit()
        committed = True
        await db.refresh(input_request)

        response = StandardResponse(data=_serialize_input_request(input_request, project_name))

    except HTTPException:
        await db.rollback()
        if (
            not committed
            and paid_receipt_storage_key
            and paid_receipt_storage_key != original_receipt_storage_key
        ):
            try:
                await delete_storage_key(paid_receipt_storage_key)
            except Exception:
                logger.warning(
                    "Failed to remove uncommitted paid receipt copy %s",
                    paid_receipt_storage_key,
                    exc_info=True,
                )
        raise
    except Exception as exc:
        await db.rollback()
        if (
            not committed
            and paid_receipt_storage_key
            and paid_receipt_storage_key != original_receipt_storage_key
        ):
            try:
                await delete_storage_key(paid_receipt_storage_key)
            except Exception:
                logger.warning(
                    "Failed to remove uncommitted paid receipt copy %s",
                    paid_receipt_storage_key,
                    exc_info=True,
                )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark input request as paid: {exc}",
        ) from exc

    if (
        original_receipt_storage_key
        and paid_receipt_storage_key
        and original_receipt_storage_key != paid_receipt_storage_key
    ):
        try:
            await delete_storage_key(original_receipt_storage_key)
        except Exception:
            logger.warning(
                "Payment committed but the previous receipt copy could not be removed: %s",
                original_receipt_storage_key,
                exc_info=True,
            )

    return response
