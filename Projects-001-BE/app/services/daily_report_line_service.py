"""
LINE Messaging API delivery for published Daily Reports.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode

import httpx

from app.core.config import get_settings
from app.core.observability import log_event
from app.services import daily_report_service
from app.services.identity_service import get_subcontractor

logger = logging.getLogger(__name__)

LINE_GROUP_SUMMARY_REFRESH_INTERVAL = timedelta(hours=24)
LINE_GROUP_SUMMARY_TIMEOUT_SECONDS = 5.0
LINE_GROUP_SUMMARY_REFRESH_LIMIT = 20


def _group_summary_needs_refresh(candidate: dict | None, *, now: datetime | None = None) -> bool:
    if not candidate:
        return True
    checked_at = candidate.get("display_name_checked_at")
    if not isinstance(checked_at, datetime):
        return True
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=UTC)
    current = now or datetime.now(UTC)
    return current - checked_at >= LINE_GROUP_SUMMARY_REFRESH_INTERVAL


async def _fetch_line_group_name(*, group_id: str, access_token: str) -> str:
    async with httpx.AsyncClient(timeout=LINE_GROUP_SUMMARY_TIMEOUT_SECONDS) as client:
        response = await client.get(
            f"https://api.line.me/v2/bot/group/{quote(group_id, safe='')}/summary",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    response.raise_for_status()
    payload = response.json()
    group_name = str(payload.get("groupName") or "").strip() if isinstance(payload, dict) else ""
    if not group_name:
        raise ValueError("LINE group summary did not include groupName.")
    return group_name


async def _refresh_line_group_name(*, group_id: str, access_token: str) -> None:
    try:
        group_name = await _fetch_line_group_name(
            group_id=group_id,
            access_token=access_token,
        )
    except Exception as exc:
        daily_report_service.update_line_destination_candidate_display_name(
            line_target_id=group_id,
            display_name=None,
            display_name_status="UNAVAILABLE",
        )
        log_event(
            logger,
            logging.WARNING,
            "line_group_summary_lookup_failed",
            error_category=type(exc).__name__,
            status="FAILED",
        )
        return
    daily_report_service.update_line_destination_candidate_display_name(
        line_target_id=group_id,
        display_name=group_name,
        display_name_status="AVAILABLE",
    )


async def refresh_line_destination_candidate_names(candidates: list[dict]) -> list[dict]:
    access_token = get_settings().line_customer_channel_access_token
    if not access_token:
        return candidates
    refreshable = [
        candidate
        for candidate in candidates
        if str(candidate.get("target_type") or "").strip().lower() == "group"
        and candidate.get("line_target_id")
        and _group_summary_needs_refresh(candidate)
    ][:LINE_GROUP_SUMMARY_REFRESH_LIMIT]
    if not refreshable:
        return candidates
    await asyncio.gather(
        *(
            _refresh_line_group_name(
                group_id=str(candidate["line_target_id"]),
                access_token=access_token,
            )
            for candidate in refreshable
        )
    )
    return daily_report_service.list_line_destination_candidates()


def _report_url(report: dict) -> str:
    settings = get_settings()
    if settings.customer_report_public_share_enabled:
        share_url = daily_report_service.get_customer_share_report_url(
            project_id=str(report["project_id"]),
            report_id=str(report["id"]),
        )
        if share_url:
            return share_url
    query = urlencode({"report": report["id"]})
    return f"{settings.frontend_base_url}/project-reports?{query}"


def _record_delivery_alert(report: dict, detail: str) -> None:
    daily_report_service.ensure_staff_notification(
        project_id=report["project_id"],
        report_date=report["report_date"],
        notification_type="LINE_DELIVERY_FAILURE",
        title="ส่งรายงานไปยัง LINE ไม่สำเร็จ",
        message=detail,
        report_id=report["id"],
        discriminator=str(report.get("published_version") or "current"),
    )


def _flex_message(report: dict) -> dict:
    issues = report.get("issues") or []
    progress = report.get("progress_percent")
    progress_label = f"{float(progress):.0f}%" if progress is not None else "Not stated"
    summary = str(report.get("summary") or "").strip()
    if len(summary) > 420:
        summary = f"{summary[:417]}..."
    return {
        "type": "flex",
        "altText": f"Latest progress: {report.get('project_name') or 'Project'}",
        "contents": {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "DAILY PROGRESS",
                        "weight": "bold",
                        "color": "#4F6F64",
                        "size": "sm",
                    },
                    {
                        "type": "text",
                        "text": str(report.get("project_name") or "Project"),
                        "weight": "bold",
                        "size": "xl",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": str(report.get("report_date") or ""),
                        "size": "sm",
                        "color": "#777777",
                    },
                ],
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "Progress", "color": "#777777", "flex": 3},
                            {"type": "text", "text": progress_label, "weight": "bold", "align": "end", "flex": 2},
                        ],
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "Issues", "color": "#777777", "flex": 3},
                            {"type": "text", "text": str(len(issues)), "weight": "bold", "align": "end", "flex": 2},
                        ],
                    },
                    {
                        "type": "text",
                        "text": summary or "The latest approved progress report is ready.",
                        "wrap": True,
                        "size": "sm",
                        "color": "#333333",
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#4F6F64",
                        "action": {
                            "type": "uri",
                            "label": "View approved report",
                            "uri": _report_url(report),
                        },
                    }
                ],
            },
        },
    }


async def deliver_published_report(report: dict) -> str:
    """
    Attempt one customer LINE delivery and persist its result.

    Cloud Tasks can call this function through a private task endpoint later.
    The first implementation performs the same idempotent job immediately.
    """

    settings = get_settings()
    job = daily_report_service.create_delivery_job(report=report)
    destination = daily_report_service.get_line_destination(report["project_id"])
    access_token = settings.line_customer_channel_access_token

    if settings.customer_report_public_share_enabled:
        share_link = daily_report_service.ensure_customer_share_link(report["project_id"])
        if not share_link.get("enabled"):
            error_detail = "ลิงก์รายงานสำหรับลูกค้าถูกปิดใช้งานในโครงการนี้"
            daily_report_service.update_delivery_status(
                report_id=report["id"],
                job_id=job["id"],
                delivery_status="NOT_CONFIGURED",
                last_error="The customer report share link is disabled.",
            )
            _record_delivery_alert(report, error_detail)
            return "NOT_CONFIGURED"

    if not access_token or not destination:
        error_detail = (
            "ยังไม่ได้ตั้งค่า LINE สำหรับลูกค้าหรือกลุ่ม LINE ของโครงการ"
        )
        daily_report_service.update_delivery_status(
            report_id=report["id"],
            job_id=job["id"],
            delivery_status="NOT_CONFIGURED",
            last_error="Customer LINE token or active project destination is not configured.",
        )
        _record_delivery_alert(report, error_detail)
        log_event(
            logger,
            logging.ERROR,
            "daily_report_line_delivery_failed",
            project_id=report["project_id"],
            report_id=report["id"],
            delivery_job_id=job["id"],
            version=report.get("published_version"),
            status="NOT_CONFIGURED",
            error_category="LineDestinationNotConfigured",
        )
        return "NOT_CONFIGURED"

    target_id = str(
        destination.get("line_target_id")
        or destination.get("customer_line_target_id")
        or ""
    ).strip()
    if not target_id:
        error_detail = (
            "ไม่พบปลายทาง LINE ที่เปิดใช้งานสำหรับโครงการนี้"
        )
        daily_report_service.update_delivery_status(
            report_id=report["id"],
            job_id=job["id"],
            delivery_status="NOT_CONFIGURED",
            last_error="Active project destination is missing line_target_id.",
        )
        _record_delivery_alert(report, error_detail)
        log_event(
            logger,
            logging.ERROR,
            "daily_report_line_delivery_failed",
            project_id=report["project_id"],
            report_id=report["id"],
            delivery_job_id=job["id"],
            version=report.get("published_version"),
            status="NOT_CONFIGURED",
            error_category="LineTargetMissing",
        )
        return "NOT_CONFIGURED"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.line.me/v2/bot/message/push",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"to": target_id, "messages": [_flex_message(report)]},
            )
        response.raise_for_status()
    except Exception as exc:
        daily_report_service.update_delivery_status(
            report_id=report["id"],
            job_id=job["id"],
            delivery_status="FAILED",
            last_error=str(exc)[:500],
        )
        _record_delivery_alert(
            report,
            (
                "ระบบส่งรายงานโครงการ "
                f"{report.get('project_name') or report['project_id']} "
                "ไปยัง LINE ไม่สำเร็จ"
            ),
        )
        log_event(
            logger,
            logging.ERROR,
            "daily_report_line_delivery_failed",
            project_id=report["project_id"],
            report_id=report["id"],
            delivery_job_id=job["id"],
            version=report.get("published_version"),
            status="FAILED",
            error_category=type(exc).__name__,
        )
        return "FAILED"

    daily_report_service.update_delivery_status(
        report_id=report["id"],
        job_id=job["id"],
        delivery_status="SENT",
    )
    log_event(
        logger,
        logging.INFO,
        "daily_report_line_delivery_succeeded",
        project_id=report["project_id"],
        report_id=report["id"],
        delivery_job_id=job["id"],
        version=report.get("published_version"),
        status="SENT",
    )
    return "SENT"


def verify_customer_webhook_signature(*, body: bytes, signature: str) -> bool:
    secret = get_settings().line_customer_channel_secret
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


async def handle_customer_webhook(payload: dict) -> dict[str, int]:
    """
    Discover LINE groups/rooms without automatically granting project access.

    An Owner must still link the discovered target to a project in RAYADEE.
    """

    discovered = 0
    replies_sent = 0
    access_token = get_settings().line_customer_channel_access_token
    for event in payload.get("events") or []:
        source = event.get("source") if isinstance(event.get("source"), dict) else {}
        source_type = str(source.get("type") or "").strip().lower()
        target_id = str(
            source.get("groupId")
            or source.get("roomId")
            or source.get("userId")
            or ""
        ).strip()
        if target_id and source_type in {"group", "room", "user"}:
            event_type = str(event.get("type") or "unknown")
            existing_candidate = daily_report_service.get_line_destination_candidate(target_id)
            daily_report_service.record_line_destination_candidate(
                line_target_id=target_id,
                target_type=source_type,
                event_type=event_type,
            )
            discovered += 1
            if (
                source_type == "group"
                and access_token
                and _group_summary_needs_refresh(existing_candidate)
            ):
                await _refresh_line_group_name(
                    group_id=target_id,
                    access_token=access_token,
                )

        reply_token = str(event.get("replyToken") or "").strip()
        if event.get("type") == "join" and reply_token and access_token:
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.post(
                        "https://api.line.me/v2/bot/message/reply",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "replyToken": reply_token,
                            "messages": [
                                {
                                    "type": "text",
                                    "text": (
                                        "RYD PROJECT CUSTOMER is connected. "
                                        "A RAYADEE Owner must link this LINE destination "
                                        "to the correct project before reports can be sent."
                                    ),
                                }
                            ],
                        },
                    )
                response.raise_for_status()
                replies_sent += 1
            except Exception as exc:
                # LINE retries webhooks. Candidate discovery is the durable action;
                # a failed courtesy reply must not make the webhook fail.
                log_event(
                    logger,
                    logging.WARNING,
                    "line_webhook_join_reply_failed",
                    error_category=type(exc).__name__,
                    status="FAILED",
                )
    return {"events": len(payload.get("events") or []), "discovered": discovered, "replies_sent": replies_sent}


async def notify_subcontractor_submission(
    *,
    submission: dict,
    event_type: str,
    reason: str | None = None,
) -> str:
    settings = get_settings()
    access_token = settings.line_subcontractor_channel_access_token
    if not access_token:
        return "NOT_CONFIGURED"
    try:
        profile = get_subcontractor(str(submission.get("subcontractor_id") or ""))
    except Exception:
        return "PROFILE_NOT_FOUND"
    if not profile.is_active or not profile.line_uid:
        return "NO_LINE_BINDING"

    report_url = (
        f"{settings.frontend_base_url}/daily-reports/me"
        f"?project={submission.get('project_id')}&date={submission.get('report_date')}"
    )
    if event_type == "CHANGES_REQUESTED":
        text = (
            "รายงานประจำวันของคุณต้องแก้ไข\n"
            f"โครงการ: {submission.get('project_name') or submission.get('project_id')}\n"
            "รายละเอียด: "
            f"{reason or 'กรุณาตรวจสอบความคิดเห็นจาก Admin'}\n"
            f"{report_url}"
        )
    elif event_type in {"SUBMITTED", "RESUBMITTED"}:
        text = (
            "ระบบได้รับรายงานประจำวันของคุณแล้ว\n"
            f"โครงการ: {submission.get('project_name') or submission.get('project_id')}\n"
            f"วันที่: {submission.get('report_date')}\n"
            "Admin/Owner จะตรวจสอบก่อนส่งให้ลูกค้า"
        )
    else:
        text = (
            "รายงานของคุณได้รับการตรวจและรวมไว้"
            "ในรายงานที่ส่งให้ลูกค้าแล้ว\n"
            f"โครงการ: {submission.get('project_name') or submission.get('project_id')}\n"
            f"วันที่: {submission.get('report_date')}"
        )
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.line.me/v2/bot/message/push",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"to": profile.line_uid, "messages": [{"type": "text", "text": text}]},
            )
        response.raise_for_status()
    except Exception as exc:
        log_event(
            logger,
            logging.ERROR,
            "subcontractor_line_notification_failed",
            project_id=submission.get("project_id"),
            submission_id=submission.get("id"),
            event_type=event_type,
            error_category=type(exc).__name__,
            status="FAILED",
        )
        return "FAILED"
    return "SENT"
