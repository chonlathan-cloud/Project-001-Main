"""
Deadline cycle creation and subcontractor LINE reminders.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.core.config import get_settings
from app.services import daily_report_service
from app.services.identity_service import get_subcontractor


def _local_datetime(report_date, clock_value: str, timezone_name: str) -> datetime:
    hour_text, minute_text = clock_value.split(":", 1)
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo("Asia/Bangkok")
    return datetime.combine(
        report_date,
        time(hour=int(hour_text), minute=int(minute_text)),
        timezone,
    )


async def _send_line_text(*, line_uid: str, text: str) -> None:
    access_token = get_settings().line_subcontractor_channel_access_token
    if not access_token:
        raise RuntimeError("Subcontractor LINE channel access token is not configured.")
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"to": line_uid, "messages": [{"type": "text", "text": text}]},
        )
    response.raise_for_status()


async def run_deadline_tick(
    *,
    projects: list[dict],
    fallback_project_subcontractors: dict[str, list[str]],
    now: datetime | None = None,
) -> dict[str, int]:
    """
    Create today's cycles and send idempotent reminder/overdue messages.

    The caller is expected to be a private Cloud Scheduler/Task endpoint.
    Re-running the tick is safe because each notification milestone has a
    deterministic Firestore document ID.
    """

    current_utc = now or datetime.now(UTC)
    counters = {
        "projects_checked": 0,
        "cycles_ready": 0,
        "notifications_sent": 0,
        "notifications_skipped": 0,
        "notifications_failed": 0,
    }
    frontend_base_url = get_settings().frontend_base_url

    for project in projects:
        project_id = str(project["id"])
        project_name = str(project.get("name") or project_id)
        settings = daily_report_service.get_project_settings(project_id)
        if not settings.get("enabled", True):
            continue
        counters["projects_checked"] += 1

        timezone_name = str(settings.get("timezone") or "Asia/Bangkok")
        try:
            timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            timezone = ZoneInfo("Asia/Bangkok")
        local_now = current_utc.astimezone(timezone)
        report_date = local_now.date()
        due_at = _local_datetime(
            report_date,
            str(settings.get("submission_due_time") or "17:00"),
            timezone_name,
        )
        review_at = _local_datetime(
            report_date,
            str(settings.get("review_target_time") or "19:00"),
            timezone_name,
        )
        expected_ids = list(settings.get("expected_subcontractor_ids") or [])
        if not expected_ids:
            expected_ids = list(fallback_project_subcontractors.get(project_id, []))
        daily_report_service.ensure_daily_cycle(
            project_id=project_id,
            project_name=project_name,
            report_date=report_date.isoformat(),
            submission_due_at=due_at.astimezone(UTC),
            review_target_at=review_at.astimezone(UTC),
            expected_subcontractor_ids=expected_ids,
        )
        counters["cycles_ready"] += 1

        submitted_ids = {
            item.get("subcontractor_id")
            for item in daily_report_service.list_submissions(
                project_id=project_id,
                report_date=report_date.isoformat(),
                statuses={"SUBMITTED", "RESUBMITTED", "ACCEPTED"},
            )
        }
        if submitted_ids:
            daily_report_service.rebuild_report(
                project_id=project_id,
                project_name=project_name,
                report_date=report_date.isoformat(),
                actor_id="daily-report-deadline-tick",
                actor_role="system",
            )
        reminder_offsets = sorted(
            {max(0, int(value)) for value in settings.get("reminder_minutes_before") or [120, 30]},
            reverse=True,
        )
        milestones = [
            (f"REMINDER_{minutes}M", due_at - timedelta(minutes=minutes))
            for minutes in reminder_offsets
        ]
        milestones.append(("OVERDUE", due_at))
        if local_now < due_at:
            eligible_reminders = [
                item
                for item in milestones
                if item[0].startswith("REMINDER") and local_now >= item[1]
            ]
            active_milestones = [max(eligible_reminders, key=lambda item: item[1])] if eligible_reminders else []
        else:
            active_milestones = [("OVERDUE", due_at)]

        for subcontractor_id in expected_ids:
            if subcontractor_id in submitted_ids:
                continue
            for notification_type, _milestone_at in active_milestones:
                claimed = daily_report_service.claim_notification(
                    project_id=project_id,
                    report_date=report_date.isoformat(),
                    subcontractor_id=subcontractor_id,
                    notification_type=notification_type,
                )
                if claimed is None:
                    counters["notifications_skipped"] += 1
                    continue
                try:
                    profile = get_subcontractor(subcontractor_id)
                    if not profile.is_active or not profile.line_uid:
                        raise RuntimeError("Subcontractor has no active LINE binding.")
                    due_label = due_at.strftime("%H:%M")
                    message_prefix = (
                        "Daily report is overdue"
                        if notification_type == "OVERDUE"
                        else "Please submit today's daily report"
                    )
                    report_url = (
                        f"{frontend_base_url}/daily-reports/me"
                        f"?project={project_id}&date={report_date.isoformat()}"
                    )
                    await _send_line_text(
                        line_uid=profile.line_uid,
                        text=(
                            f"{message_prefix}\n"
                            f"Project: {project_name}\n"
                            f"Deadline: {due_label}\n"
                            f"{report_url}"
                        ),
                    )
                    daily_report_service.complete_notification(
                        notification_id=claimed["id"],
                        notification_status="SENT",
                    )
                    counters["notifications_sent"] += 1
                except Exception as exc:
                    daily_report_service.complete_notification(
                        notification_id=claimed["id"],
                        notification_status="FAILED",
                        error=str(exc)[:500],
                    )
                    counters["notifications_failed"] += 1

    return counters
