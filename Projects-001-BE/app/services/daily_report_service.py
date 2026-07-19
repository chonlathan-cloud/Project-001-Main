"""
Firestore-backed business logic for project Daily Reports.

Published versions are immutable. The mutable report document is the current
review workspace, while every publication stores a complete customer-facing
snapshot in ``daily_report_versions``.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from google.api_core.exceptions import AlreadyExists

from app.core.google_clients import get_firestore_client

SETTINGS_COLLECTION = "daily_report_project_settings"
CYCLES_COLLECTION = "daily_report_cycles"
NO_WORK_DAYS_COLLECTION = "daily_report_no_work_days"
SUBMISSIONS_COLLECTION = "daily_report_submissions"
MEDIA_COLLECTION = "daily_report_media"
REPORTS_COLLECTION = "daily_reports"
VERSIONS_COLLECTION = "daily_report_versions"
EVENTS_COLLECTION = "daily_report_events"
MEMBERSHIPS_COLLECTION = "project_memberships"
DESTINATIONS_COLLECTION = "line_destinations"
DESTINATION_CANDIDATES_COLLECTION = "line_destination_candidates"
DELIVERY_JOBS_COLLECTION = "daily_report_delivery_jobs"
ACKNOWLEDGEMENTS_COLLECTION = "daily_report_acknowledgements"
QUESTIONS_COLLECTION = "daily_report_questions"
NOTIFICATIONS_COLLECTION = "daily_report_notifications"

EDITABLE_SUBMISSION_STATUSES = {"DRAFT", "CHANGES_REQUESTED"}
CONSOLIDATABLE_SUBMISSION_STATUSES = {
    "SUBMITTED",
    "RESUBMITTED",
    "ACCEPTED",
    "CHANGES_REQUESTED",
}
REVIEWABLE_REPORT_STATUSES = {"PENDING_REVIEW", "CHANGES_REQUESTED", "CORRECTION_DRAFT"}
RECEIVED_SUBMISSION_STATUSES = {
    "SUBMITTED",
    "RESUBMITTED",
    "ACCEPTED",
    "CHANGES_REQUESTED",
}
DEFAULT_PROJECT_SETTINGS = {
    "enabled": True,
    "timezone": "Asia/Bangkok",
    "working_days": [1, 2, 3, 4, 5, 6],
    "cycle_creation_time": "06:00",
    "first_reminder_time": "16:00",
    "submission_due_time": "17:00",
    "overdue_grace_minutes": 15,
    "draft_time": "18:00",
    "review_target_time": "19:00",
    "reminder_minutes_before": [60],
    "expected_subcontractor_ids": [],
}


def _client():
    return get_firestore_client()


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _optional_text(value: object) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _public(snapshot) -> dict[str, Any]:
    payload = snapshot.to_dict() or {}
    payload["id"] = payload.get("id") or snapshot.id
    return payload


def _stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(_clean_text(part).lower() for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def _not_found(entity: str, entity_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} {entity_id} not found.",
    )


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _get_doc(collection: str, item_id: str, entity: str) -> dict[str, Any]:
    snapshot = _client().collection(collection).document(item_id).get()
    if not snapshot.exists:
        raise _not_found(entity, item_id)
    return _public(snapshot)


def _stream_collection(collection: str) -> list[dict[str, Any]]:
    return [_public(snapshot) for snapshot in _client().collection(collection).stream()]


def _sort_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.min.replace(tzinfo=UTC)


def _normalize_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(_clean_text(value)).isoformat()
    except ValueError as exc:
        raise _bad_request("report_date must use YYYY-MM-DD format.") from exc


def _event(
    *,
    project_id: str,
    event_type: str,
    actor_id: str,
    actor_role: str,
    report_id: str | None = None,
    submission_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ref = _client().collection(EVENTS_COLLECTION).document()
    payload = {
        "id": ref.id,
        "project_id": project_id,
        "report_id": report_id,
        "submission_id": submission_id,
        "event_type": event_type,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "detail": detail or {},
        "created_at": _now_utc(),
    }
    ref.set(payload)
    return payload


def get_project_settings(project_id: str) -> dict[str, Any]:
    ref = _client().collection(SETTINGS_COLLECTION).document(project_id)
    snapshot = ref.get()
    if snapshot.exists:
        payload = _public(snapshot)
        payload.setdefault("project_id", project_id)
        for key, value in DEFAULT_PROJECT_SETTINGS.items():
            payload.setdefault(key, list(value) if isinstance(value, list) else value)
        return payload
    return {
        "project_id": project_id,
        **{
            key: list(value) if isinstance(value, list) else value
            for key, value in DEFAULT_PROJECT_SETTINGS.items()
        },
        "updated_at": None,
        "updated_by": None,
    }


def has_project_settings(project_id: str) -> bool:
    return _client().collection(SETTINGS_COLLECTION).document(project_id).get().exists


def update_project_settings(
    *,
    project_id: str,
    updates: dict[str, Any],
    actor_id: str,
) -> dict[str, Any]:
    current = get_project_settings(project_id)
    allowed = {
        "enabled",
        "timezone",
        "working_days",
        "cycle_creation_time",
        "first_reminder_time",
        "submission_due_time",
        "overdue_grace_minutes",
        "draft_time",
        "review_target_time",
        "reminder_minutes_before",
        "expected_subcontractor_ids",
    }
    payload = {key: value for key, value in updates.items() if key in allowed}
    if "working_days" in payload:
        payload["working_days"] = sorted(
            {
                int(value)
                for value in payload["working_days"]
                if 1 <= int(value) <= 7
            }
        )
    if "reminder_minutes_before" in payload:
        payload["reminder_minutes_before"] = sorted(
            {max(0, int(value)) for value in payload["reminder_minutes_before"]},
            reverse=True,
        )
    if "expected_subcontractor_ids" in payload:
        payload["expected_subcontractor_ids"] = list(
            dict.fromkeys(_clean_text(value) for value in payload["expected_subcontractor_ids"] if _clean_text(value))
        )
    payload.update(
        {
            "project_id": project_id,
            "updated_at": _now_utc(),
            "updated_by": actor_id,
        }
    )
    _client().collection(SETTINGS_COLLECTION).document(project_id).set(payload, merge=True)
    current.update(payload)
    _event(
        project_id=project_id,
        event_type="PROJECT_SETTINGS_UPDATED",
        actor_id=actor_id,
        actor_role="owner",
        detail={"changed_fields": sorted(updates)},
    )
    return current


def ensure_daily_cycle(
    *,
    project_id: str,
    project_name: str,
    report_date: str,
    submission_due_at: datetime,
    review_target_at: datetime,
    expected_subcontractor_ids: list[str],
    timezone_name: str = "Asia/Bangkok",
) -> dict[str, Any]:
    normalized_date = _normalize_date(report_date)
    cycle_id = _stable_id("cycle", project_id, normalized_date)
    ref = _client().collection(CYCLES_COLLECTION).document(cycle_id)
    snapshot = ref.get()
    if snapshot.exists:
        return _public(snapshot)

    now = _now_utc()
    expected_ids = list(dict.fromkeys(expected_subcontractor_ids))
    payload = {
        "id": cycle_id,
        "project_id": project_id,
        "project_name": project_name,
        "report_date": normalized_date,
        "timezone": timezone_name,
        "status": "COLLECTING",
        "submission_due_at": submission_due_at,
        "review_target_at": review_target_at,
        "expected_subcontractor_ids": expected_ids,
        "submitted_subcontractor_ids": [],
        "missing_subcontractor_ids": expected_ids,
        "report_id": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        ref.create(payload)
    except AlreadyExists:
        return _public(ref.get())
    return payload


def get_daily_cycle(*, project_id: str, report_date: date | str) -> dict[str, Any] | None:
    normalized_date = _normalize_date(report_date)
    cycle_id = _stable_id("cycle", project_id, normalized_date)
    snapshot = _client().collection(CYCLES_COLLECTION).document(cycle_id).get()
    return _public(snapshot) if snapshot.exists else None


def update_daily_cycle(
    *,
    project_id: str,
    report_date: date | str,
    status_value: str | None = None,
    submitted_subcontractor_ids: list[str] | None = None,
    missing_subcontractor_ids: list[str] | None = None,
    report_id: str | None = None,
) -> dict[str, Any] | None:
    cycle = get_daily_cycle(project_id=project_id, report_date=report_date)
    if cycle is None:
        return None
    if cycle.get("status") in {"NO_WORK", "CANCELLED", "CLOSED", "PUBLISHED"}:
        return cycle
    updates: dict[str, Any] = {"updated_at": _now_utc()}
    if status_value:
        updates["status"] = _clean_text(status_value).upper()
    if submitted_subcontractor_ids is not None:
        updates["submitted_subcontractor_ids"] = list(
            dict.fromkeys(_clean_text(item) for item in submitted_subcontractor_ids if _clean_text(item))
        )
    if missing_subcontractor_ids is not None:
        updates["missing_subcontractor_ids"] = list(
            dict.fromkeys(_clean_text(item) for item in missing_subcontractor_ids if _clean_text(item))
        )
    if report_id is not None:
        updates["report_id"] = _optional_text(report_id)
    _client().collection(CYCLES_COLLECTION).document(cycle["id"]).set(updates, merge=True)
    cycle.update(updates)
    return cycle


def get_no_work_day(*, project_id: str, report_date: date | str) -> dict[str, Any] | None:
    normalized_date = _normalize_date(report_date)
    item_id = _stable_id("no-work", project_id, normalized_date)
    snapshot = _client().collection(NO_WORK_DAYS_COLLECTION).document(item_id).get()
    if not snapshot.exists:
        return None
    payload = _public(snapshot)
    return payload if _clean_text(payload.get("status")).upper() == "ACTIVE" else None


def is_no_work_day(*, project_id: str, report_date: date | str) -> bool:
    return get_no_work_day(project_id=project_id, report_date=report_date) is not None


def list_no_work_days(*, project_id: str) -> list[dict[str, Any]]:
    return sorted(
        [
            item
            for item in _stream_collection(NO_WORK_DAYS_COLLECTION)
            if item.get("project_id") == project_id
            and _clean_text(item.get("status")).upper() == "ACTIVE"
        ],
        key=lambda item: _clean_text(item.get("report_date")),
        reverse=True,
    )


def set_no_work_day(
    *,
    project_id: str,
    report_date: date | str,
    reason: str | None,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    normalized_date = _normalize_date(report_date)
    received = list_submissions(
        project_id=project_id,
        report_date=normalized_date,
        statuses=RECEIVED_SUBMISSION_STATUSES,
    )
    if received:
        raise _conflict("A no-work day cannot be set after a subcontractor report was submitted.")

    item_id = _stable_id("no-work", project_id, normalized_date)
    ref = _client().collection(NO_WORK_DAYS_COLLECTION).document(item_id)
    existing = ref.get()
    now = _now_utc()
    payload = {
        "id": item_id,
        "project_id": project_id,
        "report_date": normalized_date,
        "status": "ACTIVE",
        "reason": _optional_text(reason),
        "updated_at": now,
        "updated_by": actor_id,
    }
    if not existing.exists:
        payload["created_at"] = now
        payload["created_by"] = actor_id
    ref.set(payload, merge=True)

    cycle = get_daily_cycle(project_id=project_id, report_date=normalized_date)
    if cycle is not None:
        _client().collection(CYCLES_COLLECTION).document(cycle["id"]).set(
            {"status": "NO_WORK", "updated_at": now},
            merge=True,
        )
    _event(
        project_id=project_id,
        event_type="NO_WORK_DAY_SET",
        actor_id=actor_id,
        actor_role=actor_role,
        detail={"report_date": normalized_date, "reason": payload["reason"]},
    )
    return {**(_public(existing) if existing.exists else {}), **payload}


def clear_no_work_day(
    *,
    project_id: str,
    report_date: date | str,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    normalized_date = _normalize_date(report_date)
    item = get_no_work_day(project_id=project_id, report_date=normalized_date)
    if item is None:
        raise _not_found("Daily report no-work day", normalized_date)
    now = _now_utc()
    updates = {
        "status": "CANCELLED",
        "updated_at": now,
        "updated_by": actor_id,
    }
    _client().collection(NO_WORK_DAYS_COLLECTION).document(item["id"]).set(updates, merge=True)
    cycle = get_daily_cycle(project_id=project_id, report_date=normalized_date)
    if cycle is not None and cycle.get("status") == "NO_WORK":
        _client().collection(CYCLES_COLLECTION).document(cycle["id"]).set(
            {"status": "COLLECTING", "updated_at": now},
            merge=True,
        )
    _event(
        project_id=project_id,
        event_type="NO_WORK_DAY_CLEARED",
        actor_id=actor_id,
        actor_role=actor_role,
        detail={"report_date": normalized_date},
    )
    item.update(updates)
    return item


def claim_notification(
    *,
    project_id: str,
    report_date: str,
    subcontractor_id: str,
    notification_type: str,
) -> dict[str, Any] | None:
    notification_id = _stable_id(
        "notification",
        project_id,
        report_date,
        subcontractor_id,
        notification_type,
    )
    ref = _client().collection(NOTIFICATIONS_COLLECTION).document(notification_id)
    snapshot = ref.get()
    if snapshot.exists:
        existing = _public(snapshot)
        next_attempt_at = existing.get("next_attempt_at")
        retry_ready = (
            existing.get("status") == "FAILED"
            and int(existing.get("attempt_count") or 0) < 3
            and (not isinstance(next_attempt_at, datetime) or next_attempt_at <= _now_utc())
        )
        if not retry_ready:
            return None
        updates = {"status": "CLAIMED", "updated_at": _now_utc()}
        ref.set(updates, merge=True)
        existing.update(updates)
        return existing
    now = _now_utc()
    payload = {
        "id": notification_id,
        "project_id": project_id,
        "report_date": report_date,
        "subcontractor_id": subcontractor_id,
        "notification_type": notification_type,
        "status": "CLAIMED",
        "attempt_count": 0,
        "next_attempt_at": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        ref.create(payload)
    except AlreadyExists:
        return None
    return payload


def complete_notification(
    *,
    notification_id: str,
    notification_status: str,
    error: str | None = None,
) -> None:
    ref = _client().collection(NOTIFICATIONS_COLLECTION).document(notification_id)
    snapshot = ref.get()
    current = snapshot.to_dict() or {}
    now = _now_utc()
    ref.set(
        {
            "status": notification_status,
            "attempt_count": int(current.get("attempt_count") or 0) + 1,
            "next_attempt_at": now + timedelta(minutes=5) if notification_status == "FAILED" else None,
            "error": _optional_text(error),
            "updated_at": now,
        },
        merge=True,
    )


def ensure_staff_notification(
    *,
    project_id: str,
    report_date: date | str,
    notification_type: str,
    title: str,
    message: str,
    report_id: str | None = None,
    submission_id: str | None = None,
    missing_subcontractor_ids: list[str] | None = None,
    discriminator: str | None = None,
    scope: str = "PROJECT",
) -> dict[str, Any] | None:
    normalized_date = _normalize_date(report_date)
    normalized_type = _clean_text(notification_type).upper()
    normalized_scope = _clean_text(scope).upper() or "PROJECT"
    if normalized_scope not in {"PROJECT", "GLOBAL"}:
        normalized_scope = "PROJECT"
    notification_id = _stable_id(
        "notification",
        project_id,
        normalized_date,
        "staff",
        normalized_type,
        discriminator or "",
    )
    ref = _client().collection(NOTIFICATIONS_COLLECTION).document(notification_id)
    now = _now_utc()
    payload = {
        "id": notification_id,
        "project_id": project_id,
        "report_date": normalized_date,
        "notification_type": normalized_type,
        "audience": "STAFF",
        "scope": normalized_scope,
        "status": "UNREAD",
        "title": _clean_text(title),
        "message": _clean_text(message),
        "report_id": _optional_text(report_id),
        "submission_id": _optional_text(submission_id),
        "missing_subcontractor_ids": list(
            dict.fromkeys(
                _clean_text(item)
                for item in missing_subcontractor_ids or []
                if _clean_text(item)
            )
        ),
        "created_at": now,
        "updated_at": now,
    }
    try:
        ref.create(payload)
    except AlreadyExists:
        return None
    return payload


def ensure_global_staff_notification(
    *,
    notification_type: str,
    title: str,
    message: str,
    discriminator: str | None = None,
) -> dict[str, Any] | None:
    """Create one alert visible to every active Admin and Owner."""

    return ensure_staff_notification(
        project_id="__global__",
        report_date=_now_utc().date(),
        notification_type=notification_type,
        title=title,
        message=message,
        discriminator=discriminator,
        scope="GLOBAL",
    )


def list_staff_notifications(
    *,
    project_ids: set[str] | None,
    unread_only: bool = False,
) -> list[dict[str, Any]]:
    items = [
        item
        for item in _stream_collection(NOTIFICATIONS_COLLECTION)
        if _clean_text(item.get("audience")).upper() == "STAFF"
        and (
            _clean_text(item.get("scope")).upper() == "GLOBAL"
            or project_ids is None
            or item.get("project_id") in project_ids
        )
        and (not unread_only or _clean_text(item.get("status")).upper() == "UNREAD")
    ]
    return sorted(items, key=lambda item: _sort_datetime(item.get("created_at")), reverse=True)


def mark_staff_notification_read(
    *,
    notification_id: str,
    actor_id: str,
) -> dict[str, Any]:
    item = _get_doc(NOTIFICATIONS_COLLECTION, notification_id, "Daily report notification")
    if _clean_text(item.get("audience")).upper() != "STAFF":
        raise _not_found("Daily report staff notification", notification_id)
    updates = {
        "status": "READ",
        "read_at": _now_utc(),
        "read_by": actor_id,
        "updated_at": _now_utc(),
    }
    _client().collection(NOTIFICATIONS_COLLECTION).document(notification_id).set(updates, merge=True)
    item.update(updates)
    return item


def upsert_project_membership(
    *,
    project_id: str,
    principal_type: str,
    principal_id: str,
    is_active: bool,
    actor_id: str,
) -> dict[str, Any]:
    normalized_type = _clean_text(principal_type).lower()
    normalized_id = _clean_text(principal_id)
    membership_id = _stable_id("membership", normalized_type, normalized_id, project_id)
    now = _now_utc()
    ref = _client().collection(MEMBERSHIPS_COLLECTION).document(membership_id)
    existing = ref.get()
    payload = {
        "id": membership_id,
        "project_id": project_id,
        "principal_type": normalized_type,
        "principal_id": normalized_id,
        "status": "ACTIVE" if is_active else "INACTIVE",
        "updated_at": now,
        "updated_by": actor_id,
    }
    if not existing.exists:
        payload["created_at"] = now
    ref.set(payload, merge=True)
    return payload


def has_project_membership(
    *,
    project_id: str,
    principal_type: str,
    principal_id: str,
) -> bool:
    membership_id = _stable_id("membership", principal_type, principal_id, project_id)
    snapshot = _client().collection(MEMBERSHIPS_COLLECTION).document(membership_id).get()
    if not snapshot.exists:
        return False
    payload = snapshot.to_dict() or {}
    return _clean_text(payload.get("status")).upper() == "ACTIVE"


def list_membership_project_ids(*, principal_type: str, principal_id: str) -> list[str]:
    items = _stream_collection(MEMBERSHIPS_COLLECTION)
    return sorted(
        {
            _clean_text(item.get("project_id"))
            for item in items
            if _clean_text(item.get("principal_type")).lower() == _clean_text(principal_type).lower()
            and _clean_text(item.get("principal_id")) == _clean_text(principal_id)
            and _clean_text(item.get("status")).upper() == "ACTIVE"
            and _clean_text(item.get("project_id"))
        }
    )


def get_submission(submission_id: str) -> dict[str, Any]:
    return _get_doc(SUBMISSIONS_COLLECTION, submission_id, "Daily report submission")


def create_submission(
    *,
    project_id: str,
    project_name: str,
    report_date: date | str,
    subcontractor_id: str,
    subcontractor_name: str,
    actor_id: str,
) -> dict[str, Any]:
    normalized_date = _normalize_date(report_date)
    submission_id = _stable_id("submission", project_id, normalized_date, subcontractor_id)
    ref = _client().collection(SUBMISSIONS_COLLECTION).document(submission_id)
    snapshot = ref.get()
    if snapshot.exists:
        return _public(snapshot)

    now = _now_utc()
    payload = {
        "id": submission_id,
        "project_id": project_id,
        "project_name": project_name,
        "report_date": normalized_date,
        "subcontractor_id": subcontractor_id,
        "subcontractor_name": subcontractor_name,
        "status": "DRAFT",
        "work_summary": None,
        "work_areas": [],
        "manpower_total": 0,
        "progress_percent": None,
        "checklist": {},
        "site_conditions": {},
        "issues": [],
        "tomorrow_plan": None,
        "notes": None,
        "media_ids": [],
        "change_request_reason": None,
        "submitted_at": None,
        "created_at": now,
        "created_by": actor_id,
        "updated_at": now,
        "updated_by": actor_id,
    }
    ref.set(payload)
    _event(
        project_id=project_id,
        submission_id=submission_id,
        event_type="SUBMISSION_DRAFT_CREATED",
        actor_id=actor_id,
        actor_role="subcontractor",
    )
    return payload


def update_submission(
    *,
    submission_id: str,
    subcontractor_id: str,
    updates: dict[str, Any],
    actor_id: str,
) -> dict[str, Any]:
    current = get_submission(submission_id)
    if current.get("subcontractor_id") != subcontractor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This submission belongs to another subcontractor.")
    if current.get("status") not in EDITABLE_SUBMISSION_STATUSES:
        raise _conflict("Only draft or change-requested submissions can be edited.")

    allowed = {
        "work_summary",
        "work_areas",
        "manpower_total",
        "progress_percent",
        "checklist",
        "site_conditions",
        "issues",
        "tomorrow_plan",
        "notes",
    }
    payload = {key: value for key, value in updates.items() if key in allowed}
    payload.update({"updated_at": _now_utc(), "updated_by": actor_id})
    _client().collection(SUBMISSIONS_COLLECTION).document(submission_id).set(payload, merge=True)
    current.update(payload)
    return current


def list_submissions(
    *,
    subcontractor_id: str | None = None,
    project_id: str | None = None,
    report_date: str | None = None,
    statuses: set[str] | None = None,
) -> list[dict[str, Any]]:
    items = _stream_collection(SUBMISSIONS_COLLECTION)
    normalized_statuses = {_clean_text(item).upper() for item in statuses or set()}
    filtered = [
        item
        for item in items
        if (not subcontractor_id or item.get("subcontractor_id") == subcontractor_id)
        and (not project_id or item.get("project_id") == project_id)
        and (not report_date or item.get("report_date") == report_date)
        and (not normalized_statuses or _clean_text(item.get("status")).upper() in normalized_statuses)
    ]
    return sorted(filtered, key=lambda item: (_clean_text(item.get("report_date")), _sort_datetime(item.get("updated_at"))), reverse=True)


def new_media_id() -> str:
    return _client().collection(MEDIA_COLLECTION).document().id


def record_media(
    *,
    media_id: str,
    submission_id: str,
    project_id: str,
    owner_id: str,
    media_type: str,
    file_name: str,
    content_type: str,
    size_bytes: int,
    storage_key: str,
) -> dict[str, Any]:
    submission = get_submission(submission_id)
    if submission.get("project_id") != project_id or submission.get("subcontractor_id") != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Media does not match the submission owner.")
    if submission.get("status") not in EDITABLE_SUBMISSION_STATUSES:
        raise _conflict("Media cannot be added after the submission is sent for review.")
    payload = {
        "id": media_id,
        "submission_id": submission_id,
        "project_id": project_id,
        "owner_id": owner_id,
        "media_type": _clean_text(media_type).upper(),
        "file_name": file_name,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "storage_key": storage_key,
        "status": "READY",
        "created_at": _now_utc(),
    }
    _client().collection(MEDIA_COLLECTION).document(media_id).set(payload)
    media_ids = list(dict.fromkeys([*(submission.get("media_ids") or []), media_id]))
    _client().collection(SUBMISSIONS_COLLECTION).document(submission_id).set(
        {"media_ids": media_ids, "updated_at": _now_utc()},
        merge=True,
    )
    return payload


def get_media(media_id: str) -> dict[str, Any]:
    return _get_doc(MEDIA_COLLECTION, media_id, "Daily report media")


def list_media(*, submission_ids: list[str] | None = None) -> list[dict[str, Any]]:
    ids = set(submission_ids or [])
    items = _stream_collection(MEDIA_COLLECTION)
    return [
        item
        for item in items
        if not ids or item.get("submission_id") in ids
    ]


def delete_media(*, media_id: str, owner_id: str) -> dict[str, Any]:
    media = get_media(media_id)
    if media.get("owner_id") != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This media belongs to another subcontractor.")
    submission = get_submission(_clean_text(media.get("submission_id")))
    if submission.get("status") not in EDITABLE_SUBMISSION_STATUSES:
        raise _conflict("Media cannot be removed after the submission is sent for review.")
    _client().collection(MEDIA_COLLECTION).document(media_id).delete()
    media_ids = [item for item in submission.get("media_ids") or [] if item != media_id]
    _client().collection(SUBMISSIONS_COLLECTION).document(submission["id"]).set(
        {"media_ids": media_ids, "updated_at": _now_utc()},
        merge=True,
    )
    return media


def _validate_submission_ready(submission: dict[str, Any]) -> None:
    if not _optional_text(submission.get("work_summary")):
        raise _bad_request("Work summary is required before submission.")
    if not _optional_text(submission.get("tomorrow_plan")):
        raise _bad_request("Tomorrow plan is required before submission.")
    media_ids = submission.get("media_ids") if isinstance(submission.get("media_ids"), list) else []
    ready_media = [
        get_media(media_id)
        for media_id in media_ids
        if _clean_text(media_id)
    ]
    if not any(item.get("status") == "READY" and _clean_text(item.get("content_type")).startswith("image/") for item in ready_media):
        raise _bad_request("At least one site photo is required before submission.")


def submit_submission(
    *,
    submission_id: str,
    subcontractor_id: str,
    actor_id: str,
) -> dict[str, Any]:
    current = get_submission(submission_id)
    if current.get("subcontractor_id") != subcontractor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This submission belongs to another subcontractor.")
    if current.get("status") not in EDITABLE_SUBMISSION_STATUSES:
        raise _conflict("This submission is already in review or finalized.")
    if is_no_work_day(
        project_id=current["project_id"],
        report_date=current["report_date"],
    ):
        raise _conflict("This project date is marked as a no-work day.")
    _validate_submission_ready(current)
    next_status = "RESUBMITTED" if current.get("status") == "CHANGES_REQUESTED" else "SUBMITTED"
    now = _now_utc()
    updates = {
        "status": next_status,
        "submitted_at": now,
        "updated_at": now,
        "updated_by": actor_id,
        "change_request_reason": None,
    }
    _client().collection(SUBMISSIONS_COLLECTION).document(submission_id).set(updates, merge=True)
    current.update(updates)
    report = rebuild_report(
        project_id=current["project_id"],
        project_name=current.get("project_name") or current["project_id"],
        report_date=current["report_date"],
        actor_id=actor_id,
        actor_role="subcontractor",
    )
    cycle = get_daily_cycle(
        project_id=current["project_id"],
        report_date=current["report_date"],
    )
    if cycle is not None:
        received_submissions = list_submissions(
            project_id=current["project_id"],
            report_date=current["report_date"],
            statuses=RECEIVED_SUBMISSION_STATUSES,
        )
        submitted_ids = sorted(
            {
                _clean_text(item.get("subcontractor_id"))
                for item in received_submissions
                if _clean_text(item.get("subcontractor_id"))
            }
        )
        expected_ids = list(cycle.get("expected_subcontractor_ids") or [])
        missing_ids = [item for item in expected_ids if item not in submitted_ids]
        update_daily_cycle(
            project_id=current["project_id"],
            report_date=current["report_date"],
            status_value="PENDING_REVIEW" if expected_ids and not missing_ids else "PARTIALLY_SUBMITTED",
            submitted_subcontractor_ids=submitted_ids,
            missing_subcontractor_ids=missing_ids,
            report_id=report["id"],
        )
    notification_type = (
        "CHANGE_REQUEST_RESPONSE"
        if next_status == "RESUBMITTED"
        else "NEW_SUBMISSION"
    )
    notification_title = (
        "ผู้รับเหมาส่งรายงานแก้ไขแล้ว"
        if next_status == "RESUBMITTED"
        else "มีรายงานใหม่"
    )
    ensure_staff_notification(
        project_id=current["project_id"],
        report_date=current["report_date"],
        notification_type=notification_type,
        title=notification_title,
        message=(
            f"{current.get('subcontractor_name') or 'ผู้รับเหมา'} "
            "ส่งรายงานประจำวัน"
            f"ของโครงการ {current.get('project_name') or current['project_id']} แล้ว"
        ),
        report_id=report["id"],
        submission_id=submission_id,
        discriminator=submission_id,
    )
    _event(
        project_id=current["project_id"],
        report_id=report["id"],
        submission_id=submission_id,
        event_type=next_status,
        actor_id=actor_id,
        actor_role="subcontractor",
    )
    return current


def _report_id(project_id: str, report_date: str) -> str:
    return _stable_id("report", project_id, report_date)


def get_report(report_id: str, *, include_sources: bool = True) -> dict[str, Any]:
    report = _get_doc(REPORTS_COLLECTION, report_id, "Daily report")
    if include_sources:
        submission_ids = report.get("source_submission_ids") or []
        report["submissions"] = [
            get_submission(submission_id)
            for submission_id in submission_ids
        ]
        report["media"] = list_media(submission_ids=submission_ids)
        report["acknowledgements"] = [
            item
            for item in _stream_collection(ACKNOWLEDGEMENTS_COLLECTION)
            if item.get("report_id") == report_id
        ]
        report["questions"] = [
            item
            for item in _stream_collection(QUESTIONS_COLLECTION)
            if item.get("report_id") == report_id
        ]
    return report


def rebuild_report(
    *,
    project_id: str,
    project_name: str,
    report_date: str,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    normalized_date = _normalize_date(report_date)
    report_id = _report_id(project_id, normalized_date)
    report_ref = _client().collection(REPORTS_COLLECTION).document(report_id)
    existing_snapshot = report_ref.get()
    existing = _public(existing_snapshot) if existing_snapshot.exists else {}
    if existing.get("status") == "PUBLISHED":
        return existing

    submissions = list_submissions(
        project_id=project_id,
        report_date=normalized_date,
        statuses=CONSOLIDATABLE_SUBMISSION_STATUSES,
    )
    if not submissions:
        raise _bad_request("No submitted subcontractor reports are available to consolidate.")

    summaries = [
        f"{item.get('subcontractor_name') or 'Subcontractor'}: {_clean_text(item.get('work_summary'))}"
        for item in submissions
        if _optional_text(item.get("work_summary"))
    ]
    tomorrow_parts = [
        f"{item.get('subcontractor_name') or 'Subcontractor'}: {_clean_text(item.get('tomorrow_plan'))}"
        for item in submissions
        if _optional_text(item.get("tomorrow_plan"))
    ]
    issues: list[dict[str, Any]] = []
    for item in submissions:
        for issue in item.get("issues") or []:
            normalized_issue = dict(issue) if isinstance(issue, dict) else {"title": _clean_text(issue)}
            normalized_issue["source_submission_id"] = item["id"]
            normalized_issue["source_subcontractor_name"] = item.get("subcontractor_name")
            issues.append(normalized_issue)
    progress_values = [
        float(item["progress_percent"])
        for item in submissions
        if item.get("progress_percent") is not None
    ]
    now = _now_utc()
    cycle_id = _stable_id("cycle", project_id, normalized_date)
    cycle_snapshot = _client().collection(CYCLES_COLLECTION).document(cycle_id).get()
    if cycle_snapshot.exists:
        expected_subcontractor_ids = list(
            (cycle_snapshot.to_dict() or {}).get("expected_subcontractor_ids") or []
        )
    else:
        expected_subcontractor_ids = list(
            get_project_settings(project_id).get("expected_subcontractor_ids") or []
        )
    received_subcontractor_ids = {
        _clean_text(item.get("subcontractor_id"))
        for item in submissions
        if _clean_text(item.get("subcontractor_id"))
    }
    missing_subcontractor_ids = [
        item
        for item in expected_subcontractor_ids
        if item not in received_subcontractor_ids
    ]
    next_status = (
        "CHANGES_REQUESTED"
        if any(item.get("status") == "CHANGES_REQUESTED" for item in submissions)
        else "PENDING_REVIEW"
    )
    payload = {
        "id": report_id,
        "project_id": project_id,
        "project_name": project_name,
        "report_date": normalized_date,
        "status": next_status,
        "title": existing.get("title") or f"Daily progress report — {project_name}",
        "summary": "\n\n".join(summaries),
        "progress_percent": round(sum(progress_values) / len(progress_values), 1) if progress_values else None,
        "manpower_total": sum(int(item.get("manpower_total") or 0) for item in submissions),
        "issues": issues,
        "tomorrow_plan": "\n".join(tomorrow_parts) or None,
        "customer_note": existing.get("customer_note"),
        "source_submission_ids": [item["id"] for item in submissions],
        "expected_subcontractor_ids": expected_subcontractor_ids,
        "missing_subcontractor_ids": missing_subcontractor_ids,
        "published_version": existing.get("published_version"),
        "published_at": existing.get("published_at"),
        "published_by": existing.get("published_by"),
        "delivery_status": existing.get("delivery_status"),
        "updated_at": now,
        "updated_by": actor_id,
    }
    if not existing_snapshot.exists:
        payload["created_at"] = now
        payload["created_by"] = actor_id
    report_ref.set(payload, merge=True)
    return payload


def list_reports(
    *,
    project_ids: set[str] | None = None,
    statuses: set[str] | None = None,
    published_only: bool = False,
) -> list[dict[str, Any]]:
    items = _stream_collection(REPORTS_COLLECTION)
    normalized_statuses = {_clean_text(item).upper() for item in statuses or set()}
    filtered = [
        item
        for item in items
        if (project_ids is None or item.get("project_id") in project_ids)
        and (not normalized_statuses or _clean_text(item.get("status")).upper() in normalized_statuses)
        and (not published_only or item.get("status") == "PUBLISHED")
    ]
    return sorted(
        filtered,
        key=lambda item: (_clean_text(item.get("report_date")), _sort_datetime(item.get("updated_at"))),
        reverse=True,
    )


def update_report_draft(
    *,
    report_id: str,
    updates: dict[str, Any],
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    report = get_report(report_id, include_sources=False)
    if report.get("status") not in REVIEWABLE_REPORT_STATUSES:
        raise _conflict("Published reports are locked. Start a correction to create a new version.")
    allowed = {"title", "summary", "progress_percent", "issues", "tomorrow_plan", "customer_note"}
    payload = {key: value for key, value in updates.items() if key in allowed}
    payload.update({"updated_at": _now_utc(), "updated_by": actor_id})
    _client().collection(REPORTS_COLLECTION).document(report_id).set(payload, merge=True)
    report.update(payload)
    _event(
        project_id=report["project_id"],
        report_id=report_id,
        event_type="REPORT_DRAFT_UPDATED",
        actor_id=actor_id,
        actor_role=actor_role,
        detail={"changed_fields": sorted(updates)},
    )
    return report


def request_changes(
    *,
    report_id: str,
    reason: str,
    submission_ids: list[str],
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    report = get_report(report_id, include_sources=False)
    if report.get("status") not in {"PENDING_REVIEW", "CHANGES_REQUESTED"}:
        raise _conflict("Changes can be requested only while a report is under review.")
    target_ids = submission_ids or list(report.get("source_submission_ids") or [])
    valid_ids = set(report.get("source_submission_ids") or [])
    if not target_ids or any(item not in valid_ids for item in target_ids):
        raise _bad_request("Change requests must target source submissions in this report.")
    now = _now_utc()
    for submission_id in target_ids:
        _client().collection(SUBMISSIONS_COLLECTION).document(submission_id).set(
            {
                "status": "CHANGES_REQUESTED",
                "change_request_reason": reason,
                "updated_at": now,
                "updated_by": actor_id,
            },
            merge=True,
        )
    updates = {"status": "CHANGES_REQUESTED", "updated_at": now, "updated_by": actor_id}
    _client().collection(REPORTS_COLLECTION).document(report_id).set(updates, merge=True)
    report.update(updates)
    _event(
        project_id=report["project_id"],
        report_id=report_id,
        event_type="CHANGES_REQUESTED",
        actor_id=actor_id,
        actor_role=actor_role,
        detail={"reason": reason, "submission_ids": target_ids},
    )
    return report


def _publication_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": report["id"],
        "project_id": report["project_id"],
        "project_name": report.get("project_name"),
        "report_date": report["report_date"],
        "title": report.get("title"),
        "summary": report.get("summary"),
        "progress_percent": report.get("progress_percent"),
        "manpower_total": report.get("manpower_total"),
        "issues": report.get("issues") or [],
        "tomorrow_plan": report.get("tomorrow_plan"),
        "customer_note": report.get("customer_note"),
    }


def publish_report(
    *,
    report_id: str,
    publication_note: str | None,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    report = get_report(report_id, include_sources=False)
    if report.get("status") not in {"PENDING_REVIEW", "CORRECTION_DRAFT"}:
        raise _conflict("Only a reviewed draft or correction draft can be published.")
    if not _optional_text(report.get("summary")):
        raise _bad_request("Customer-facing summary is required before publication.")
    now = _now_utc()
    version = int(report.get("published_version") or 0) + 1
    version_id = f"{report_id}-v{version}"
    snapshot = _publication_snapshot(report)
    version_payload = {
        "id": version_id,
        "report_id": report_id,
        "project_id": report["project_id"],
        "version": version,
        "snapshot": snapshot,
        "publication_note": _optional_text(publication_note),
        "published_at": now,
        "published_by": actor_id,
    }
    version_ref = _client().collection(VERSIONS_COLLECTION).document(version_id)
    if version_ref.get().exists:
        raise _conflict("This report version already exists.")
    version_ref.set(version_payload)
    updates = {
        "status": "PUBLISHED",
        "published_version": version,
        "published_at": now,
        "published_by": actor_id,
        "delivery_status": "PENDING",
        "updated_at": now,
        "updated_by": actor_id,
    }
    _client().collection(REPORTS_COLLECTION).document(report_id).set(updates, merge=True)
    update_daily_cycle(
        project_id=report["project_id"],
        report_date=report["report_date"],
        status_value="PUBLISHED",
        report_id=report_id,
    )
    for submission_id in report.get("source_submission_ids") or []:
        _client().collection(SUBMISSIONS_COLLECTION).document(submission_id).set(
            {"status": "ACCEPTED", "updated_at": now, "updated_by": actor_id},
            merge=True,
        )
    report.update(updates)
    _event(
        project_id=report["project_id"],
        report_id=report_id,
        event_type="PUBLISHED",
        actor_id=actor_id,
        actor_role=actor_role,
        detail={"version": version},
    )
    return report


def start_correction(
    *,
    report_id: str,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    report = get_report(report_id, include_sources=False)
    if report.get("status") != "PUBLISHED":
        raise _conflict("A correction can be started only from a published report.")
    updates = {
        "status": "CORRECTION_DRAFT",
        "delivery_status": report.get("delivery_status"),
        "updated_at": _now_utc(),
        "updated_by": actor_id,
    }
    _client().collection(REPORTS_COLLECTION).document(report_id).set(updates, merge=True)
    report.update(updates)
    _event(
        project_id=report["project_id"],
        report_id=report_id,
        event_type="CORRECTION_STARTED",
        actor_id=actor_id,
        actor_role=actor_role,
    )
    return report


def list_versions(report_id: str) -> list[dict[str, Any]]:
    items = [
        item
        for item in _stream_collection(VERSIONS_COLLECTION)
        if item.get("report_id") == report_id
    ]
    return sorted(items, key=lambda item: int(item.get("version") or 0), reverse=True)


def get_customer_report(report_id: str) -> dict[str, Any]:
    """
    Return only the latest immutable published snapshot and approved media metadata.

    A mutable correction draft may exist on the report document. Customers must
    continue seeing the last published version until a new version is published.
    """

    report = get_report(report_id, include_sources=False)
    published_version = int(report.get("published_version") or 0)
    if published_version < 1:
        raise _not_found("Published daily report", report_id)
    version_id = f"{report_id}-v{published_version}"
    version = _get_doc(VERSIONS_COLLECTION, version_id, "Daily report version")
    snapshot = dict(version.get("snapshot") or {})
    media = [
        {
            "id": item["id"],
            "media_type": item.get("media_type"),
            "file_name": item.get("file_name"),
            "content_type": item.get("content_type"),
            "size_bytes": item.get("size_bytes"),
            "created_at": item.get("created_at"),
        }
        for item in list_media(submission_ids=list(report.get("source_submission_ids") or []))
        if item.get("status") == "READY"
    ]
    return {
        **snapshot,
        "id": report_id,
        "status": "PUBLISHED",
        "source_submission_ids": [],
        "submissions": [],
        "media": media,
        "acknowledgements": [],
        "questions": [],
        "published_version": published_version,
        "published_at": version.get("published_at"),
        "published_by": version.get("published_by"),
        "delivery_status": report.get("delivery_status"),
        "created_at": report.get("created_at"),
        "updated_at": version.get("published_at"),
    }


def list_customer_reports(*, project_ids: set[str]) -> list[dict[str, Any]]:
    reports = [
        report
        for report in list_reports(project_ids=project_ids)
        if int(report.get("published_version") or 0) > 0
    ]
    items = [get_customer_report(report["id"]) for report in reports]
    return sorted(
        items,
        key=lambda item: (_clean_text(item.get("report_date")), _sort_datetime(item.get("published_at"))),
        reverse=True,
    )


def list_events(report_id: str) -> list[dict[str, Any]]:
    items = [
        item
        for item in _stream_collection(EVENTS_COLLECTION)
        if item.get("report_id") == report_id
    ]
    return sorted(items, key=lambda item: _sort_datetime(item.get("created_at")), reverse=True)


def create_delivery_job(*, report: dict[str, Any]) -> dict[str, Any]:
    job_id = _stable_id("delivery", report["id"], report.get("published_version"))
    ref = _client().collection(DELIVERY_JOBS_COLLECTION).document(job_id)
    existing = ref.get()
    if existing.exists:
        return _public(existing)
    now = _now_utc()
    payload = {
        "id": job_id,
        "report_id": report["id"],
        "project_id": report["project_id"],
        "version": report.get("published_version"),
        "status": "PENDING",
        "attempt_count": 0,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
    }
    ref.set(payload)
    return payload


def update_delivery_status(
    *,
    report_id: str,
    job_id: str,
    delivery_status: str,
    last_error: str | None = None,
) -> None:
    now = _now_utc()
    job = _get_doc(DELIVERY_JOBS_COLLECTION, job_id, "Daily report delivery job")
    _client().collection(DELIVERY_JOBS_COLLECTION).document(job_id).set(
        {
            "status": delivery_status,
            "attempt_count": int(job.get("attempt_count") or 0) + 1,
            "last_error": _optional_text(last_error),
            "updated_at": now,
        },
        merge=True,
    )
    _client().collection(REPORTS_COLLECTION).document(report_id).set(
        {"delivery_status": delivery_status, "updated_at": now},
        merge=True,
    )


def get_line_destination(project_id: str) -> dict[str, Any] | None:
    snapshot = _client().collection(DESTINATIONS_COLLECTION).document(project_id).get()
    if not snapshot.exists:
        return None
    payload = _public(snapshot)
    return payload if _clean_text(payload.get("status")).upper() == "ACTIVE" else None


def get_line_destination_config(project_id: str) -> dict[str, Any]:
    snapshot = _client().collection(DESTINATIONS_COLLECTION).document(project_id).get()
    if not snapshot.exists:
        return {
            "project_id": project_id,
            "line_target_id": None,
            "target_type": "group",
            "status": "INACTIVE",
            "updated_at": None,
            "updated_by": None,
        }
    payload = _public(snapshot)
    payload.setdefault("project_id", project_id)
    payload.setdefault("target_type", "group")
    payload.setdefault("status", "INACTIVE")
    return payload


def update_line_destination(
    *,
    project_id: str,
    line_target_id: str | None,
    target_type: str,
    is_active: bool,
    actor_id: str,
) -> dict[str, Any]:
    payload = {
        "project_id": project_id,
        "line_target_id": _optional_text(line_target_id),
        "target_type": _clean_text(target_type).lower() or "group",
        "status": "ACTIVE" if is_active and _optional_text(line_target_id) else "INACTIVE",
        "updated_at": _now_utc(),
        "updated_by": actor_id,
    }
    _client().collection(DESTINATIONS_COLLECTION).document(project_id).set(payload, merge=True)
    _event(
        project_id=project_id,
        event_type="LINE_DESTINATION_UPDATED",
        actor_id=actor_id,
        actor_role="owner",
        detail={"target_type": payload["target_type"], "status": payload["status"]},
    )
    return payload


def record_line_destination_candidate(
    *,
    line_target_id: str,
    target_type: str,
    event_type: str,
) -> dict[str, Any]:
    now = _now_utc()
    ref = _client().collection(DESTINATION_CANDIDATES_COLLECTION).document(line_target_id)
    snapshot = ref.get()
    payload = {
        "id": line_target_id,
        "line_target_id": line_target_id,
        "target_type": target_type,
        "status": "DISCOVERED",
        "last_event_type": event_type,
        "last_seen_at": now,
        "updated_at": now,
    }
    if not snapshot.exists:
        payload["created_at"] = now
    ref.set(payload, merge=True)
    return payload


def list_line_destination_candidates() -> list[dict[str, Any]]:
    return sorted(
        _stream_collection(DESTINATION_CANDIDATES_COLLECTION),
        key=lambda item: _sort_datetime(item.get("last_seen_at")),
        reverse=True,
    )


def acknowledge_report(
    *,
    report_id: str,
    customer_id: str,
    note: str | None,
) -> dict[str, Any]:
    report = get_report(report_id, include_sources=False)
    if int(report.get("published_version") or 0) < 1:
        raise _not_found("Published daily report", report_id)
    ack_id = _stable_id("ack", report_id, customer_id)
    ref = _client().collection(ACKNOWLEDGEMENTS_COLLECTION).document(ack_id)
    existing = ref.get()
    now = _now_utc()
    payload = {
        "id": ack_id,
        "report_id": report_id,
        "project_id": report["project_id"],
        "customer_id": customer_id,
        "note": _optional_text(note),
        "created_at": (existing.to_dict() or {}).get("created_at", now) if existing.exists else now,
        "updated_at": now,
    }
    ref.set(payload, merge=True)
    _event(
        project_id=report["project_id"],
        report_id=report_id,
        event_type="CUSTOMER_ACKNOWLEDGED",
        actor_id=customer_id,
        actor_role="customer",
    )
    return payload


def ask_report_question(
    *,
    report_id: str,
    customer_id: str,
    question: str,
) -> dict[str, Any]:
    report = get_report(report_id, include_sources=False)
    if int(report.get("published_version") or 0) < 1:
        raise _not_found("Published daily report", report_id)
    ref = _client().collection(QUESTIONS_COLLECTION).document()
    now = _now_utc()
    payload = {
        "id": ref.id,
        "report_id": report_id,
        "project_id": report["project_id"],
        "customer_id": customer_id,
        "question": question.strip(),
        "status": "OPEN",
        "created_at": now,
        "updated_at": now,
    }
    ref.set(payload)
    ensure_staff_notification(
        project_id=report["project_id"],
        report_date=report["report_date"],
        notification_type="CUSTOMER_QUESTION",
        title="ลูกค้ามีคำถามเกี่ยวกับรายงาน",
        message=question.strip(),
        report_id=report_id,
        discriminator=ref.id,
    )
    _event(
        project_id=report["project_id"],
        report_id=report_id,
        event_type="CUSTOMER_QUESTION_CREATED",
        actor_id=customer_id,
        actor_role="customer",
        detail={"question_id": ref.id},
    )
    return payload
