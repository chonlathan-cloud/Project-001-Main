"""
In-memory BOQ batch sync job service.

This is a development-oriented background execution layer that lets the API
return immediately while BOQ tabs continue syncing in the background.
"""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.boq import Project
from app.schemas.boq_schema import SyncBOQBatchJobResponse
from app.services.boq_sync_service import MAX_BATCH_SYNC_TABS, sync_boq_sheet

logger = logging.getLogger(__name__)

_JOB_STORE: dict[str, dict[str, Any]] = {}
_JOB_STORE_LOCK = asyncio.Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_initial_results(sheet_names: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "sheet_name": sheet_name,
            "status": "QUEUED",
            "inserted_items": 0,
            "version_closed_items": 0,
            "synced_at": None,
            "message": "Waiting for background sync to start.",
        }
        for sheet_name in sheet_names
    ]


def _clean_sheet_names(sheet_names: list[str]) -> list[str]:
    cleaned_sheet_names: list[str] = []
    seen_sheet_names: set[str] = set()
    for sheet_name in sheet_names:
        normalized = str(sheet_name or "").strip()
        if not normalized or normalized in seen_sheet_names:
            continue
        cleaned_sheet_names.append(normalized)
        seen_sheet_names.add(normalized)

    if not cleaned_sheet_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one sheet tab is required for batch BOQ sync.",
        )
    if len(cleaned_sheet_names) > MAX_BATCH_SYNC_TABS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Batch BOQ sync currently supports up to {MAX_BATCH_SYNC_TABS} tabs per request "
                "to keep AI parsing responsive. Please split larger workbooks into smaller batches."
            ),
        )
    return cleaned_sheet_names


async def create_boq_sync_job(
    project_id: UUID,
    project_name: str,
    boq_type: str,
    sheet_url: str,
    sheet_names: list[str],
) -> dict[str, Any]:
    cleaned_sheet_names = _clean_sheet_names(sheet_names)
    job_id = str(uuid4())
    created_at = _utc_now_iso()
    job_data = {
        "job_id": job_id,
        "project_id": project_id,
        "project_name": project_name,
        "boq_type": boq_type,
        "sheet_url": sheet_url,
        "sheet_names": cleaned_sheet_names,
        "status": "QUEUED",
        "total_requested_tabs": len(cleaned_sheet_names),
        "total_completed_tabs": 0,
        "total_failed_tabs": 0,
        "current_sheet_name": None,
        "created_at": created_at,
        "started_at": None,
        "finished_at": None,
        "message": "BOQ batch sync queued. Poll this job for progress updates.",
        "results": _build_initial_results(cleaned_sheet_names),
    }

    async with _JOB_STORE_LOCK:
        _JOB_STORE[job_id] = job_data

    return deepcopy(job_data)


async def get_boq_sync_job(job_id: str) -> dict[str, Any]:
    async with _JOB_STORE_LOCK:
        job_data = _JOB_STORE.get(job_id)
        if job_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BOQ sync job {job_id} was not found.",
            )
        return deepcopy(job_data)


async def _update_job(job_id: str, **updates: Any) -> dict[str, Any]:
    async with _JOB_STORE_LOCK:
        job_data = _JOB_STORE.get(job_id)
        if job_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BOQ sync job {job_id} was not found.",
            )
        job_data.update(updates)
        return deepcopy(job_data)


async def _update_result_item(job_id: str, sheet_name: str, **updates: Any) -> dict[str, Any]:
    async with _JOB_STORE_LOCK:
        job_data = _JOB_STORE.get(job_id)
        if job_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BOQ sync job {job_id} was not found.",
            )

        for result in job_data["results"]:
            if result["sheet_name"] == sheet_name:
                result.update(updates)
                break

        completed = sum(1 for item in job_data["results"] if item["status"] == "COMPLETED")
        failed = sum(1 for item in job_data["results"] if item["status"] == "FAILED")
        job_data["total_completed_tabs"] = completed
        job_data["total_failed_tabs"] = failed
        return deepcopy(job_data)


async def run_boq_sync_job(job_id: str) -> None:
    job = await get_boq_sync_job(job_id)
    await _update_job(
        job_id,
        status="RUNNING",
        started_at=_utc_now_iso(),
        message="BOQ batch sync is running.",
    )
    logger.info(
        "boq_sync.job.started job_id=%s project_id=%s requested_tabs=%s",
        job_id,
        job["project_id"],
        job["total_requested_tabs"],
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Project).filter_by(id=job["project_id"])
        )
        project = result.scalar_one_or_none()

        if project is None:
            await _update_job(
                job_id,
                status="FAILED",
                finished_at=_utc_now_iso(),
                message="Project no longer exists. BOQ batch sync could not continue.",
            )
            logger.warning("boq_sync.job.project_missing job_id=%s", job_id)
            return

        project_id = project.id
        project_name = project.name

        for sheet_name in job["sheet_names"]:
            await _update_job(job_id, current_sheet_name=sheet_name)
            await _update_result_item(
                job_id,
                sheet_name,
                status="RUNNING",
                message="Syncing this tab now.",
            )

            try:
                result_data = await sync_boq_sheet(
                    session=session,
                    project=None,
                    project_id=project_id,
                    project_name=project_name,
                    boq_type=job["boq_type"],
                    sheet_url=job["sheet_url"],
                    sheet_name=sheet_name,
                )
                await _update_result_item(
                    job_id,
                    sheet_name,
                    status="COMPLETED",
                    inserted_items=result_data["inserted_items"],
                    version_closed_items=result_data["version_closed_items"],
                    synced_at=result_data["synced_at"],
                    message=result_data["message"],
                )
            except HTTPException as exc:
                await _update_result_item(
                    job_id,
                    sheet_name,
                    status="FAILED",
                    synced_at=None,
                    message=str(exc.detail),
                )
            except Exception as exc:
                logger.exception("boq_sync.job.unexpected_tab_failure job_id=%s sheet_name=%s", job_id, sheet_name)
                await _update_result_item(
                    job_id,
                    sheet_name,
                    status="FAILED",
                    synced_at=None,
                    message=f"Unexpected sync failure: {exc}",
                )

    final_job = await get_boq_sync_job(job_id)
    final_status = "COMPLETED"
    if final_job["total_completed_tabs"] and final_job["total_failed_tabs"]:
        final_status = "PARTIAL_FAILURE"
    elif final_job["total_failed_tabs"] and not final_job["total_completed_tabs"]:
        final_status = "FAILED"

    await _update_job(
        job_id,
        status=final_status,
        current_sheet_name=None,
        finished_at=_utc_now_iso(),
        message=(
            "BOQ batch sync finished."
            if final_status == "COMPLETED"
            else "BOQ batch sync finished with some failures."
            if final_status == "PARTIAL_FAILURE"
            else "BOQ batch sync failed."
        ),
    )
    logger.info("boq_sync.job.completed job_id=%s status=%s", job_id, final_status)


def serialize_boq_sync_job(job_data: dict[str, Any]) -> SyncBOQBatchJobResponse:
    return SyncBOQBatchJobResponse(**job_data)
