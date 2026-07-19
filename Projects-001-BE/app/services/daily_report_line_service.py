"""
LINE Messaging API delivery for published Daily Reports.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings
from app.services import daily_report_service
from app.services.identity_service import get_subcontractor


def _report_url(report_id: str) -> str:
    settings = get_settings()
    query = urlencode({"report": report_id})
    return f"{settings.frontend_base_url}/project-reports?{query}"


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
                            "uri": _report_url(report["id"]),
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

    if not access_token or not destination:
        daily_report_service.update_delivery_status(
            report_id=report["id"],
            job_id=job["id"],
            delivery_status="NOT_CONFIGURED",
            last_error="Customer LINE token or active project destination is not configured.",
        )
        return "NOT_CONFIGURED"

    target_id = str(
        destination.get("line_target_id")
        or destination.get("customer_line_target_id")
        or ""
    ).strip()
    if not target_id:
        daily_report_service.update_delivery_status(
            report_id=report["id"],
            job_id=job["id"],
            delivery_status="NOT_CONFIGURED",
            last_error="Active project destination is missing line_target_id.",
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
        return "FAILED"

    daily_report_service.update_delivery_status(
        report_id=report["id"],
        job_id=job["id"],
        delivery_status="SENT",
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
            daily_report_service.record_line_destination_candidate(
                line_target_id=target_id,
                target_type=source_type,
                event_type=str(event.get("type") or "unknown"),
            )
            discovered += 1

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
            except Exception:
                # LINE retries webhooks. Candidate discovery is the durable action;
                # a failed courtesy reply must not make the webhook fail.
                pass
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
            "Changes were requested for your daily report.\n"
            f"Project: {submission.get('project_name') or submission.get('project_id')}\n"
            f"Reason: {reason or 'Please review the Admin comments.'}\n"
            f"{report_url}"
        )
    else:
        text = (
            "Your daily report was accepted and included in the published project update.\n"
            f"Project: {submission.get('project_name') or submission.get('project_id')}\n"
            f"Date: {submission.get('report_date')}"
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
    except Exception:
        return "FAILED"
    return "SENT"
