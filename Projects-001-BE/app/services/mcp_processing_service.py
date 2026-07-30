"""Curated, read-only Product processing-state contracts for MCP."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.input_request import InputRequest
from app.schemas.mcp_schema import McpProcessingStatusRequest
from app.services import boq_sync_job_service, daily_report_service
from app.services.mcp_read_service import McpNotFoundOrForbidden, _authorize

INFRASTRUCTURE_PERMISSION = frozenset({"infrastructure_read"})


def _source_reference(workflow: str, job_id: str, updated_at: object) -> list[dict[str, Any]]:
    return [
        {
            "domain": "gcp_operations",
            "record_id": f"{workflow}.{job_id}",
            "source_system": "product_backend",
            "last_updated_at": updated_at,
        }
    ]


def _authorize_project(request: McpProcessingStatusRequest, project_id: str) -> None:
    try:
        UUID(project_id)
    except (TypeError, ValueError, AttributeError) as exc:
        raise McpNotFoundOrForbidden from exc
    _authorize(
        request,
        project_id=project_id,
        required_permissions=INFRASTRUCTURE_PERMISSION,
    )


async def _input_request(db: AsyncSession, job_id: str) -> InputRequest:
    try:
        record_id = UUID(job_id)
    except ValueError as exc:
        raise McpNotFoundOrForbidden from exc
    item = (
        await db.execute(
            select(InputRequest).options(noload("*")).where(InputRequest.id == record_id)
        )
    ).scalar_one_or_none()
    if item is None:
        raise McpNotFoundOrForbidden
    return item


async def _boq_status(request: McpProcessingStatusRequest) -> dict[str, Any]:
    try:
        job = await boq_sync_job_service.get_boq_sync_job(request.job_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise McpNotFoundOrForbidden from exc
        raise
    project_id = str(job.get("project_id") or "")
    _authorize_project(request, project_id)
    updated_at = job.get("finished_at") or job.get("started_at") or job.get("created_at")
    return {
        "workflow": request.workflow,
        "job_id": request.job_id,
        "project_id": project_id,
        "status": str(job.get("status") or "UNKNOWN").upper(),
        "progress": {
            "total": min(max(int(job.get("total_requested_tabs") or 0), 0), 100),
            "completed": min(max(int(job.get("total_completed_tabs") or 0), 0), 100),
            "failed": min(max(int(job.get("total_failed_tabs") or 0), 0), 100),
        },
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "source_references": _source_reference(request.workflow, request.job_id, updated_at),
        "source_read_at": datetime.now(UTC),
    }


async def _daily_report_status(request: McpProcessingStatusRequest) -> dict[str, Any]:
    try:
        job = daily_report_service.get_delivery_job_for_mcp(request.job_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise McpNotFoundOrForbidden from exc
        raise
    project_id = str(job.get("project_id") or "")
    _authorize_project(request, project_id)
    return {
        "workflow": request.workflow,
        "job_id": request.job_id,
        "project_id": project_id,
        "status": job["status"],
        "progress": {
            "attempt_count": job["attempt_count"],
            "version": job.get("version"),
        },
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "source_references": _source_reference(
            request.workflow,
            request.job_id,
            job.get("updated_at"),
        ),
        "source_read_at": datetime.now(UTC),
    }


async def _receipt_status(
    db: AsyncSession,
    request: McpProcessingStatusRequest,
) -> dict[str, Any]:
    item = await _input_request(db, request.job_id)
    project_id = str(item.project_id)
    _authorize_project(request, project_id)
    state = "READY" if isinstance(item.ocr_raw_json, dict) else "UNPROCESSED"
    return {
        "workflow": request.workflow,
        "job_id": request.job_id,
        "project_id": project_id,
        "status": state,
        "progress": {
            "has_existing_extraction": state == "READY",
            "low_confidence_field_count": min(
                len(item.ocr_low_confidence_fields)
                if isinstance(item.ocr_low_confidence_fields, list)
                else 0,
                100,
            ),
        },
        "updated_at": item.updated_at,
        "source_references": _source_reference(
            request.workflow,
            request.job_id,
            item.updated_at,
        ),
        "source_read_at": datetime.now(UTC),
    }


async def _flowaccount_status(
    db: AsyncSession,
    request: McpProcessingStatusRequest,
) -> dict[str, Any]:
    item = await _input_request(db, request.job_id)
    project_id = str(item.project_id)
    _authorize_project(request, project_id)
    return {
        "workflow": request.workflow,
        "job_id": request.job_id,
        "project_id": project_id,
        "status": str(item.flowaccount_sync_status or "NOT_READY").upper(),
        "progress": {
            "expense": str(item.flowaccount_sync_status or "NOT_READY").upper(),
            "attachment": str(item.flowaccount_attachment_status or "NOT_READY").upper(),
            "supplier_invoice": str(
                item.flowaccount_supplier_invoice_status or "NOT_READY"
            ).upper(),
            "payment": str(item.flowaccount_payment_status or "NOT_READY").upper(),
        },
        "updated_at": item.updated_at,
        "source_references": _source_reference(
            request.workflow,
            request.job_id,
            item.updated_at,
        ),
        "source_read_at": datetime.now(UTC),
    }


async def get_processing_status(
    db: AsyncSession,
    request: McpProcessingStatusRequest,
) -> dict[str, Any]:
    _authorize(request, required_permissions=INFRASTRUCTURE_PERMISSION)
    if request.workflow == "boq_sync":
        return await _boq_status(request)
    if request.workflow == "daily_report_delivery":
        return await _daily_report_status(request)
    if request.workflow == "receipt_ocr":
        return await _receipt_status(db, request)
    return await _flowaccount_status(db, request)
