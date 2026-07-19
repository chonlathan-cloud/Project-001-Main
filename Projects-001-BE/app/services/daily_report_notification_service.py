"""
Daily Report due-action scanning and idempotent notifications.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.core.config import get_settings
from app.core.observability import log_event
from app.services import daily_report_service
from app.services.identity_service import get_subcontractor

logger = logging.getLogger(__name__)


def _timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("Asia/Bangkok")


def _local_datetime(report_date: date, clock_value: str, timezone_name: str) -> datetime:
    try:
        hour_text, minute_text = clock_value.split(":", 1)
        clock = time(hour=int(hour_text), minute=int(minute_text))
    except (AttributeError, TypeError, ValueError):
        clock = time(hour=0, minute=0)
    return datetime.combine(report_date, clock, _timezone(timezone_name))


def _project_report(
    *,
    project_id: str,
    report_date: str,
) -> dict | None:
    return next(
        (
            item
            for item in daily_report_service.list_reports(project_ids={project_id})
            if item.get("report_date") == report_date
        ),
        None,
    )


def _is_working_date(*, project_id: str, report_date: date, settings: dict) -> bool:
    working_days = {
        int(value)
        for value in settings.get("working_days") or []
        if str(value).isdigit() and 1 <= int(value) <= 7
    }
    if report_date.isoweekday() not in working_days:
        return False
    return not daily_report_service.is_no_work_day(
        project_id=project_id,
        report_date=report_date,
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


async def _notify_subcontractor(
    *,
    project_id: str,
    project_name: str,
    report_date: str,
    subcontractor_id: str,
    notification_type: str,
    due_label: str,
    report_url: str,
) -> str:
    claimed = daily_report_service.claim_notification(
        project_id=project_id,
        report_date=report_date,
        subcontractor_id=subcontractor_id,
        notification_type=notification_type,
    )
    if claimed is None:
        return "SKIPPED"

    if notification_type == "CYCLE_AVAILABLE":
        text = (
            "รายงานประจำวันของวันนี้พร้อมแล้ว\n"
            f"โครงการ: {project_name}\n"
            f"กรุณาส่งภายในเวลา {due_label} น.\n"
            f"{report_url}"
        )
    elif notification_type == "OVERDUE":
        text = (
            "เลยกำหนดส่งรายงานประจำวันแล้ว\n"
            f"โครงการ: {project_name}\n"
            f"กำหนดส่ง: {due_label} น.\n"
            "กรุณาส่งรายงานโดยเร็ว\n"
            f"{report_url}"
        )
    else:
        text = (
            "แจ้งเตือน: กรุณาส่งรายงานประจำวัน\n"
            f"โครงการ: {project_name}\n"
            f"กำหนดส่ง: {due_label} น.\n"
            f"{report_url}"
        )

    try:
        profile = get_subcontractor(subcontractor_id)
        if not profile.is_active or not profile.line_uid:
            raise RuntimeError("Subcontractor has no active LINE binding.")
        await _send_line_text(line_uid=profile.line_uid, text=text)
        daily_report_service.complete_notification(
            notification_id=claimed["id"],
            notification_status="SENT",
        )
        return "SENT"
    except Exception as exc:
        daily_report_service.complete_notification(
            notification_id=claimed["id"],
            notification_status="FAILED",
            error=str(exc)[:500],
        )
        attempt_count = int(claimed.get("attempt_count") or 0) + 1
        log_event(
            logger,
            logging.ERROR,
            "daily_report_notification_failed",
            project_id=project_id,
            notification_type=notification_type,
            attempt_count=attempt_count,
            error_category=type(exc).__name__,
            status="FAILED",
        )
        if attempt_count >= 3:
            daily_report_service.ensure_staff_notification(
                project_id=project_id,
                report_date=report_date,
                notification_type="LINE_SUBCONTRACTOR_NOTIFICATION_FAILURE",
                title="ส่งข้อความแจ้งเตือนผู้รับเหมาไม่สำเร็จ",
                message=(
                    "ระบบลองส่งข้อความครบ 3 ครั้งแล้ว "
                    "กรุณาตรวจสอบการเชื่อมต่อ LINE ของผู้รับเหมา"
                ),
                discriminator=claimed["id"],
            )
        return "FAILED"


def _record_notification_result(counters: dict[str, int], result: str) -> None:
    counter_name = {
        "SENT": "notifications_sent",
        "SKIPPED": "notifications_skipped",
        "FAILED": "notifications_failed",
    }.get(result)
    if counter_name:
        counters[counter_name] += 1


def _reminder_milestones(
    *,
    report_date: date,
    settings: dict,
    timezone_name: str,
    due_at: datetime,
) -> list[tuple[str, datetime]]:
    first_reminder_at = _local_datetime(
        report_date,
        str(settings.get("first_reminder_time") or "16:00"),
        timezone_name,
    )
    reminder_times = {first_reminder_at}
    for value in settings.get("reminder_minutes_before") or [60]:
        try:
            reminder_at = due_at - timedelta(minutes=max(0, int(value)))
        except (TypeError, ValueError):
            continue
        if reminder_at >= first_reminder_at:
            reminder_times.add(reminder_at)
    return [
        (f"REMINDER_{reminder_at.strftime('%H%M')}", reminder_at)
        for reminder_at in sorted(reminder_times)
    ]


async def run_deadline_tick(
    *,
    projects: list[dict],
    fallback_project_subcontractors: dict[str, list[str]],
    now: datetime | None = None,
    cycle_only: bool = False,
) -> dict[str, int]:
    """
    Scan all active projects and run every due Daily Report milestone.

    The scan is safe to run every five minutes. Cycle, LINE-notification, and
    staff-alert identifiers are deterministic, so a repeated Scheduler request
    cannot send the same milestone twice after it has succeeded.
    """

    current_utc = now or datetime.now(UTC)
    if current_utc.tzinfo is None:
        current_utc = current_utc.replace(tzinfo=UTC)
    counters = {
        "projects_checked": 0,
        "projects_skipped": 0,
        "cycles_ready": 0,
        "notifications_sent": 0,
        "notifications_skipped": 0,
        "notifications_failed": 0,
        "overdue_alerts_created": 0,
        "draft_alerts_created": 0,
        "review_alerts_created": 0,
    }
    frontend_base_url = get_settings().frontend_base_url.rstrip("/")

    for project in projects:
        project_id = str(project["id"])
        project_name = str(project.get("name") or project_id)
        project_status = str(project.get("status") or "ACTIVE").upper()
        if project_status in {"COMPLETED", "ARCHIVED"}:
            counters["projects_skipped"] += 1
            continue

        if not daily_report_service.has_project_settings(project_id):
            counters["projects_skipped"] += 1
            continue
        settings = daily_report_service.get_project_settings(project_id)
        if not settings.get("enabled", True):
            counters["projects_skipped"] += 1
            continue
        counters["projects_checked"] += 1

        timezone_name = str(settings.get("timezone") or "Asia/Bangkok")
        local_now = current_utc.astimezone(_timezone(timezone_name))
        report_date_value = local_now.date()
        report_date = report_date_value.isoformat()
        if not _is_working_date(
            project_id=project_id,
            report_date=report_date_value,
            settings=settings,
        ):
            counters["projects_skipped"] += 1
            continue

        cycle_creation_at = _local_datetime(
            report_date_value,
            str(settings.get("cycle_creation_time") or "06:00"),
            timezone_name,
        )
        if local_now < cycle_creation_at:
            counters["projects_skipped"] += 1
            continue

        due_at = _local_datetime(
            report_date_value,
            str(settings.get("submission_due_time") or "17:00"),
            timezone_name,
        )
        overdue_at = due_at + timedelta(
            minutes=max(0, int(settings.get("overdue_grace_minutes") or 0))
        )
        draft_at = _local_datetime(
            report_date_value,
            str(settings.get("draft_time") or "18:00"),
            timezone_name,
        )
        review_at = _local_datetime(
            report_date_value,
            str(settings.get("review_target_time") or "19:00"),
            timezone_name,
        )

        cycle = daily_report_service.get_daily_cycle(
            project_id=project_id,
            report_date=report_date,
        )
        if cycle is None:
            expected_ids = list(settings.get("expected_subcontractor_ids") or [])
            if not expected_ids:
                expected_ids = list(fallback_project_subcontractors.get(project_id, []))
            cycle = daily_report_service.ensure_daily_cycle(
                project_id=project_id,
                project_name=project_name,
                report_date=report_date,
                submission_due_at=due_at.astimezone(UTC),
                review_target_at=review_at.astimezone(UTC),
                expected_subcontractor_ids=expected_ids,
                timezone_name=timezone_name,
            )
        expected_ids = list(cycle.get("expected_subcontractor_ids") or [])
        counters["cycles_ready"] += 1
        if cycle_only:
            continue

        received_submissions = daily_report_service.list_submissions(
            project_id=project_id,
            report_date=report_date,
            statuses=daily_report_service.RECEIVED_SUBMISSION_STATUSES,
        )
        submitted_ids = sorted(
            {
                str(item.get("subcontractor_id"))
                for item in received_submissions
                if item.get("subcontractor_id")
            }
        )
        missing_ids = [item for item in expected_ids if item not in submitted_ids]
        report = _project_report(project_id=project_id, report_date=report_date)
        report_url = (
            f"{frontend_base_url}/daily-reports/me"
            f"?project={project_id}&date={report_date}"
        )
        due_label = due_at.strftime("%H:%M")

        first_reminder_at = _local_datetime(
            report_date_value,
            str(settings.get("first_reminder_time") or "16:00"),
            timezone_name,
        )
        if local_now < first_reminder_at:
            for subcontractor_id in missing_ids:
                result = await _notify_subcontractor(
                    project_id=project_id,
                    project_name=project_name,
                    report_date=report_date,
                    subcontractor_id=subcontractor_id,
                    notification_type="CYCLE_AVAILABLE",
                    due_label=due_label,
                    report_url=report_url,
                )
                _record_notification_result(counters, result)

        reminder_milestones = _reminder_milestones(
            report_date=report_date_value,
            settings=settings,
            timezone_name=timezone_name,
            due_at=due_at,
        )
        if first_reminder_at <= local_now < due_at:
            eligible = [
                milestone
                for milestone in reminder_milestones
                if local_now >= milestone[1]
            ]
            active_reminder = max(eligible, key=lambda item: item[1]) if eligible else None
            if active_reminder is not None:
                for subcontractor_id in missing_ids:
                    result = await _notify_subcontractor(
                        project_id=project_id,
                        project_name=project_name,
                        report_date=report_date,
                        subcontractor_id=subcontractor_id,
                        notification_type=active_reminder[0],
                        due_label=due_label,
                        report_url=report_url,
                    )
                    _record_notification_result(counters, result)

        if expected_ids and not missing_ids:
            cycle_status = "PENDING_REVIEW"
        elif submitted_ids:
            cycle_status = "PARTIALLY_SUBMITTED"
        else:
            cycle_status = "COLLECTING"

        if local_now >= overdue_at and missing_ids:
            cycle_status = "PARTIALLY_SUBMITTED" if submitted_ids else "OVERDUE"
            for subcontractor_id in missing_ids:
                result = await _notify_subcontractor(
                    project_id=project_id,
                    project_name=project_name,
                    report_date=report_date,
                    subcontractor_id=subcontractor_id,
                    notification_type="OVERDUE",
                    due_label=due_label,
                    report_url=report_url,
                )
                _record_notification_result(counters, result)
            alert = daily_report_service.ensure_staff_notification(
                project_id=project_id,
                report_date=report_date,
                notification_type="MISSING_SUBMISSIONS",
                title="ยังได้รับรายงานไม่ครบ",
                message=(
                    f"โครงการ {project_name} ยังขาดรายงาน "
                    f"{len(missing_ids)} ราย ณ เวลา {local_now.strftime('%H:%M')} น."
                ),
                report_id=report.get("id") if report else None,
                missing_subcontractor_ids=missing_ids,
            )
            if alert is not None:
                counters["overdue_alerts_created"] += 1

        draft_due = local_now >= draft_at
        all_expected_received = bool(expected_ids) and not missing_ids
        if received_submissions and (draft_due or all_expected_received):
            if report is None:
                report = daily_report_service.rebuild_report(
                    project_id=project_id,
                    project_name=project_name,
                    report_date=report_date,
                    actor_id="daily-report-due-scanner",
                    actor_role="system",
                )
            cycle_status = "PENDING_REVIEW"
            alert = daily_report_service.ensure_staff_notification(
                project_id=project_id,
                report_date=report_date,
                notification_type="DRAFT_READY",
                title="ร่างรายงานพร้อมตรวจแล้ว",
                message=(
                    f"ร่างรายงานประจำวันของโครงการ {project_name} "
                    "พร้อมให้ Admin/Owner ตรวจแล้ว"
                ),
                report_id=report["id"],
            )
            if alert is not None:
                counters["draft_alerts_created"] += 1

        if (
            local_now >= review_at
            and report is not None
            and str(report.get("status") or "").upper()
            in daily_report_service.REVIEWABLE_REPORT_STATUSES
        ):
            alert = daily_report_service.ensure_staff_notification(
                project_id=project_id,
                report_date=report_date,
                notification_type="REVIEW_TARGET_REACHED",
                title="ถึงเวลาตรวจรายงานแล้ว",
                message=(
                    f"รายงานโครงการ {project_name} "
                    "ยังรอการตรวจและเผยแพร่ "
                    "ระบบจะไม่ส่งให้ลูกค้าอัตโนมัติ"
                ),
                report_id=report["id"],
            )
            if alert is not None:
                counters["review_alerts_created"] += 1

        daily_report_service.update_daily_cycle(
            project_id=project_id,
            report_date=report_date,
            status_value=cycle_status,
            submitted_subcontractor_ids=submitted_ids,
            missing_subcontractor_ids=missing_ids,
            report_id=report.get("id") if report else None,
        )

    return counters


async def run_due_action_scan(
    *,
    projects: list[dict],
    fallback_project_subcontractors: dict[str, list[str]],
    now: datetime | None = None,
) -> dict[str, int]:
    """Named Phase 7 entrypoint; retained wrapper keeps the old tick API compatible."""

    return await run_deadline_tick(
        projects=projects,
        fallback_project_subcontractors=fallback_project_subcontractors,
        now=now,
    )


async def run_cycle_creation_scan(
    *,
    projects: list[dict],
    fallback_project_subcontractors: dict[str, list[str]],
    now: datetime | None = None,
) -> dict[str, int]:
    """Create due project/date cycles without sending reminder milestones."""

    return await run_deadline_tick(
        projects=projects,
        fallback_project_subcontractors=fallback_project_subcontractors,
        now=now,
        cycle_only=True,
    )
