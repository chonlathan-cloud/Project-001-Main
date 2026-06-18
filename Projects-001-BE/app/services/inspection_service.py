"""
Firestore-backed services for construction inspection workflows.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException, status

try:
    from google.cloud import firestore
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    firestore = None  # type: ignore[assignment]
    _FIRESTORE_IMPORT_ERROR = exc
else:
    _FIRESTORE_IMPORT_ERROR = None

from app.core.google_clients import get_firestore_client
from app.schemas.inspection_schema import DEFAULT_INSPECTION_CATEGORIES

ROUNDS_COLLECTION = "inspection_rounds"
ZONES_COLLECTION = "inspection_zones"
DEFECTS_COLLECTION = "inspection_defects"
FILES_COLLECTION = "inspection_files"
EVENTS_COLLECTION = "inspection_events"
REPORT_LOGS_COLLECTION = "inspection_report_logs"
SETTINGS_COLLECTION = "inspection_project_settings"
COUNTERS_COLLECTION = "inspection_counters"

ROUND_STATUSES = {"ACTIVE", "CLOSED", "ARCHIVED"}
DEFECT_STATUSES = {"OPEN", "IN_PROGRESS", "READY_FOR_REVIEW", "RESOLVED"}
DEFECT_SEVERITIES = {"CRITICAL", "MAJOR", "MINOR", "COSMETIC"}
FILE_KINDS = {"PLAN_IMAGE", "BEFORE_PHOTO", "AFTER_PHOTO", "REPORT_PDF"}

ALLOWED_STATUS_TRANSITIONS = {
    "OPEN": {"IN_PROGRESS", "READY_FOR_REVIEW"},
    "IN_PROGRESS": {"READY_FOR_REVIEW"},
    "READY_FOR_REVIEW": {"RESOLVED", "IN_PROGRESS"},
    "RESOLVED": set(),
}


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _client():
    return get_firestore_client()


def _require_firestore_module():
    if firestore is None:
        raise RuntimeError(
            "google-cloud-firestore is not installed. Install backend dependencies first."
        ) from _FIRESTORE_IMPORT_ERROR
    return firestore


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _clean_optional_text(value: object) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _upper(value: object, default: str = "") -> str:
    cleaned = _clean_text(value).upper().replace(" ", "_").replace("-", "_")
    return cleaned or default


def _date_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    cleaned = _clean_optional_text(value)
    return cleaned


def _datetime_value(value: object) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _public_doc(snapshot) -> dict[str, Any]:
    payload = snapshot.to_dict() or {}
    payload["id"] = payload.get("id") or snapshot.id
    return payload


def _not_found(entity: str, entity_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity} {entity_id} not found.",
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _validate_round_status(value: str) -> str:
    normalized = _upper(value)
    if normalized not in ROUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid inspection round status: {value}",
        )
    return normalized


def _validate_defect_status(value: str) -> str:
    normalized = _upper(value)
    if normalized not in DEFECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid defect status: {value}",
        )
    return normalized


def _validate_severity(value: str) -> str:
    normalized = _upper(value)
    if normalized not in DEFECT_SEVERITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid defect severity: {value}",
        )
    return normalized


def _validate_file_kind(value: str) -> str:
    normalized = _upper(value)
    if normalized not in FILE_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid inspection file kind: {value}",
        )
    return normalized


def _document_id(collection_name: str) -> str:
    return _client().collection(collection_name).document().id


def new_file_id() -> str:
    return _document_id(FILES_COLLECTION)


def _project_round_query(collection_name: str, project_id: str, round_id: str):
    return (
        _client()
        .collection(collection_name)
        .where("project_id", "==", project_id)
        .where("round_id", "==", round_id)
    )


def _round_ref(round_id: str):
    return _client().collection(ROUNDS_COLLECTION).document(round_id)


def _zone_ref(zone_id: str):
    return _client().collection(ZONES_COLLECTION).document(zone_id)


def _defect_ref(defect_id: str):
    return _client().collection(DEFECTS_COLLECTION).document(defect_id)


def _file_ref(file_id: str):
    return _client().collection(FILES_COLLECTION).document(file_id)


def _get_round(project_id: str, round_id: str) -> dict[str, Any]:
    snapshot = _round_ref(round_id).get()
    if not snapshot.exists:
        raise _not_found("Inspection round", round_id)
    payload = _public_doc(snapshot)
    if payload.get("project_id") != project_id:
        raise _not_found("Inspection round", round_id)
    return payload


def _get_zone(project_id: str, round_id: str, zone_id: str) -> dict[str, Any]:
    snapshot = _zone_ref(zone_id).get()
    if not snapshot.exists:
        raise _not_found("Inspection zone", zone_id)
    payload = _public_doc(snapshot)
    if payload.get("project_id") != project_id or payload.get("round_id") != round_id:
        raise _not_found("Inspection zone", zone_id)
    return payload


def _get_defect(project_id: str, round_id: str, defect_id: str) -> dict[str, Any]:
    snapshot = _defect_ref(defect_id).get()
    if not snapshot.exists:
        raise _not_found("Inspection defect", defect_id)
    payload = _public_doc(snapshot)
    if payload.get("project_id") != project_id or payload.get("round_id") != round_id:
        raise _not_found("Inspection defect", defect_id)
    return payload


def get_file(file_id: str) -> dict[str, Any]:
    snapshot = _file_ref(file_id).get()
    if not snapshot.exists:
        raise _not_found("Inspection file", file_id)
    return _public_doc(snapshot)


def _ensure_project_settings(project_id: str, actor_id: str | None = None) -> dict[str, Any]:
    client = _client()
    ref = client.collection(SETTINGS_COLLECTION).document(project_id)
    snapshot = ref.get()
    if snapshot.exists:
        payload = _public_doc(snapshot)
        categories = payload.get("categories")
        if isinstance(categories, list) and categories:
            return payload

    now = _now_utc()
    payload = {
        "id": project_id,
        "project_id": project_id,
        "categories": DEFAULT_INSPECTION_CATEGORIES,
        "updated_at": now,
        "updated_by": actor_id,
    }
    ref.set(payload, merge=True)
    return payload


def get_project_categories(project_id: str) -> dict[str, Any]:
    return _ensure_project_settings(project_id)


def update_project_categories(
    *,
    project_id: str,
    categories: list[str],
    actor_id: str,
) -> dict[str, Any]:
    payload = {
        "id": project_id,
        "project_id": project_id,
        "categories": categories,
        "updated_at": _now_utc(),
        "updated_by": actor_id,
    }
    _client().collection(SETTINGS_COLLECTION).document(project_id).set(payload, merge=True)
    return payload


def _next_defect_display_no(project_id: str, round_id: str) -> str:
    firestore_module = _require_firestore_module()
    client = _client()
    counter_ref = client.collection(COUNTERS_COLLECTION).document(f"{project_id}_{round_id}")
    transaction = client.transaction()

    @firestore_module.transactional
    def _advance(transaction):
        snapshot = counter_ref.get(transaction=transaction)
        payload = snapshot.to_dict() or {}
        next_value = int(payload.get("next_defect_no") or 1)
        transaction.set(
            counter_ref,
            {
                "project_id": project_id,
                "round_id": round_id,
                "next_defect_no": next_value + 1,
                "updated_at": _now_utc(),
            },
            merge=True,
        )
        return next_value

    return f"DF-{_advance(transaction):04d}"


def list_rounds(
    *,
    project_id: str,
    subcontractor_id: str | None = None,
) -> list[dict[str, Any]]:
    client = _client()
    snapshots = client.collection(ROUNDS_COLLECTION).where("project_id", "==", project_id).stream()
    rounds = [_public_doc(snapshot) for snapshot in snapshots]
    if subcontractor_id:
        visible_round_ids = {
            defect.get("round_id")
            for defect in list_defects(
                project_id=project_id,
                round_id=None,
                filters={"assigned_subcontractor_id": subcontractor_id},
            )
        }
        rounds = [item for item in rounds if item.get("id") in visible_round_ids]
    return sorted(rounds, key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=UTC), reverse=True)


def create_round(
    *,
    project_id: str,
    payload: dict[str, Any],
    actor_id: str,
) -> dict[str, Any]:
    client = _client()
    doc_ref = client.collection(ROUNDS_COLLECTION).document()
    now = _now_utc()
    data = {
        "id": doc_ref.id,
        "project_id": project_id,
        "name": _clean_text(payload.get("name")),
        "description": _clean_optional_text(payload.get("description")),
        "status": "ACTIVE",
        "started_at": now,
        "target_close_at": payload.get("target_close_at"),
        "created_by": actor_id,
        "created_at": now,
        "updated_at": now,
    }
    doc_ref.set(data)
    _ensure_project_settings(project_id, actor_id)
    return data


def get_round(project_id: str, round_id: str) -> dict[str, Any]:
    return _get_round(project_id, round_id)


def update_round(
    *,
    project_id: str,
    round_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    current = _get_round(project_id, round_id)
    updates: dict[str, Any] = {"updated_at": _now_utc()}
    for field in ("name", "description", "target_close_at"):
        if field in payload:
            updates[field] = _clean_optional_text(payload[field]) if field != "target_close_at" else payload[field]
    if "status" in payload and payload["status"] is not None:
        updates["status"] = _validate_round_status(payload["status"])
    _round_ref(round_id).set(updates, merge=True)
    current.update(updates)
    return current


def list_zones(
    *,
    project_id: str,
    round_id: str,
    subcontractor_id: str | None = None,
) -> list[dict[str, Any]]:
    _get_round(project_id, round_id)
    snapshots = _project_round_query(ZONES_COLLECTION, project_id, round_id).stream()
    zones = [_public_doc(snapshot) for snapshot in snapshots]
    if subcontractor_id:
        visible_zone_ids = {
            defect.get("zone_id")
            for defect in list_defects(
                project_id=project_id,
                round_id=round_id,
                filters={"assigned_subcontractor_id": subcontractor_id},
            )
        }
        zones = [item for item in zones if item.get("id") in visible_zone_ids]
    return sorted(zones, key=lambda item: (int(item.get("sort_order") or 0), str(item.get("name") or "")))


def create_zone(
    *,
    project_id: str,
    round_id: str,
    payload: dict[str, Any],
    actor_id: str,
) -> dict[str, Any]:
    _get_round(project_id, round_id)
    client = _client()
    doc_ref = client.collection(ZONES_COLLECTION).document()
    now = _now_utc()
    data = {
        "id": doc_ref.id,
        "project_id": project_id,
        "round_id": round_id,
        "name": _clean_text(payload.get("name")),
        "floor": _clean_optional_text(payload.get("floor")),
        "room": _clean_optional_text(payload.get("room")),
        "sort_order": int(payload.get("sort_order") or 0),
        "plan_file_id": _clean_optional_text(payload.get("plan_file_id")),
        "created_by": actor_id,
        "created_at": now,
        "updated_at": now,
    }
    doc_ref.set(data)
    return data


def update_zone(
    *,
    project_id: str,
    round_id: str,
    zone_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    current = _get_zone(project_id, round_id, zone_id)
    updates: dict[str, Any] = {"updated_at": _now_utc()}
    for field in ("name", "floor", "room", "plan_file_id"):
        if field in payload:
            updates[field] = _clean_optional_text(payload[field])
    if "sort_order" in payload and payload["sort_order"] is not None:
        updates["sort_order"] = int(payload["sort_order"])
    _zone_ref(zone_id).set(updates, merge=True)
    current.update(updates)
    return current


def list_defects(
    *,
    project_id: str,
    round_id: str | None,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    filters = filters or {}
    query = _client().collection(DEFECTS_COLLECTION).where("project_id", "==", project_id)
    if round_id:
        query = query.where("round_id", "==", round_id)

    defects = [_public_doc(snapshot) for snapshot in query.stream()]

    def _matches(defect: dict[str, Any]) -> bool:
        for field in ("zone_id", "category", "assigned_subcontractor_id"):
            expected = _clean_optional_text(filters.get(field))
            if expected and defect.get(field) != expected:
                return False

        for field in ("status", "severity"):
            values = filters.get(field)
            if values:
                normalized_values = {_upper(value) for value in values}
                if _upper(defect.get(field)) not in normalized_values:
                    return False

        search = _clean_optional_text(filters.get("search"))
        if search:
            haystack = " ".join(
                str(defect.get(field) or "")
                for field in ("display_no", "title", "description", "category", "assigned_subcontractor_name")
            ).casefold()
            if search.casefold() not in haystack:
                return False

        due_before = _date_value(filters.get("due_before"))
        if due_before and (not defect.get("due_date") or str(defect.get("due_date")) > due_before):
            return False

        if filters.get("overdue") is True:
            due_date = _date_value(defect.get("due_date"))
            if not due_date or due_date >= date.today().isoformat() or defect.get("status") == "RESOLVED":
                return False

        return True

    return sorted(
        [defect for defect in defects if _matches(defect)],
        key=lambda item: (str(item.get("display_no") or ""), item.get("created_at") or datetime.min.replace(tzinfo=UTC)),
    )


def create_defect(
    *,
    project_id: str,
    round_id: str,
    payload: dict[str, Any],
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    _get_round(project_id, round_id)
    _get_zone(project_id, round_id, str(payload.get("zone_id") or ""))
    client = _client()
    doc_ref = client.collection(DEFECTS_COLLECTION).document()
    now = _now_utc()
    status_value = _validate_defect_status(payload.get("status") or "OPEN")
    severity = _validate_severity(payload.get("severity") or "MINOR")
    data = {
        "id": doc_ref.id,
        "display_no": _next_defect_display_no(project_id, round_id),
        "project_id": project_id,
        "round_id": round_id,
        "zone_id": _clean_text(payload.get("zone_id")),
        "title": _clean_text(payload.get("title")),
        "description": _clean_optional_text(payload.get("description")),
        "category": _clean_optional_text(payload.get("category")) or "Other",
        "severity": severity,
        "status": status_value,
        "assigned_subcontractor_id": _clean_optional_text(payload.get("assigned_subcontractor_id")),
        "assigned_subcontractor_name": _clean_optional_text(payload.get("assigned_subcontractor_name")),
        "due_date": _date_value(payload.get("due_date")),
        "plan_x": payload.get("plan_x"),
        "plan_y": payload.get("plan_y"),
        "before_file_ids": list(payload.get("before_file_ids") or []),
        "after_file_ids": [],
        "created_by": actor_id,
        "created_at": now,
        "updated_at": now,
        "resolved_at": now if status_value == "RESOLVED" else None,
    }
    doc_ref.set(data)
    create_event(
        project_id=project_id,
        round_id=round_id,
        defect_id=doc_ref.id,
        event_type="DEFECT_CREATED",
        actor_id=actor_id,
        actor_role=actor_role,
        metadata={"display_no": data["display_no"]},
    )
    if data["assigned_subcontractor_id"]:
        create_event(
            project_id=project_id,
            round_id=round_id,
            defect_id=doc_ref.id,
            event_type="ASSIGNED",
            actor_id=actor_id,
            actor_role=actor_role,
            metadata={
                "assigned_subcontractor_id": data["assigned_subcontractor_id"],
                "assigned_subcontractor_name": data["assigned_subcontractor_name"],
            },
        )
    return data


def get_defect(project_id: str, round_id: str, defect_id: str) -> dict[str, Any]:
    return _get_defect(project_id, round_id, defect_id)


def update_defect(
    *,
    project_id: str,
    round_id: str,
    defect_id: str,
    payload: dict[str, Any],
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    current = _get_defect(project_id, round_id, defect_id)
    updates: dict[str, Any] = {"updated_at": _now_utc()}
    for field in (
        "zone_id",
        "title",
        "description",
        "category",
        "assigned_subcontractor_id",
        "assigned_subcontractor_name",
    ):
        if field in payload:
            updates[field] = _clean_optional_text(payload[field])
    if "severity" in payload and payload["severity"] is not None:
        updates["severity"] = _validate_severity(payload["severity"])
    if "due_date" in payload:
        updates["due_date"] = _date_value(payload["due_date"])
    for field in ("plan_x", "plan_y"):
        if field in payload:
            updates[field] = payload[field]
    if updates.get("zone_id"):
        _get_zone(project_id, round_id, updates["zone_id"])

    _defect_ref(defect_id).set(updates, merge=True)
    if "assigned_subcontractor_id" in updates and updates["assigned_subcontractor_id"] != current.get("assigned_subcontractor_id"):
        create_event(
            project_id=project_id,
            round_id=round_id,
            defect_id=defect_id,
            event_type="ASSIGNED",
            actor_id=actor_id,
            actor_role=actor_role,
            metadata={
                "assigned_subcontractor_id": updates.get("assigned_subcontractor_id"),
                "assigned_subcontractor_name": updates.get("assigned_subcontractor_name"),
            },
        )
    current.update(updates)
    return current


def update_defect_status(
    *,
    project_id: str,
    round_id: str,
    defect_id: str,
    to_status: str,
    comment: str | None,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    current = _get_defect(project_id, round_id, defect_id)
    from_status = _validate_defect_status(current.get("status") or "OPEN")
    next_status = _validate_defect_status(to_status)
    if next_status == from_status:
        return current

    if next_status not in ALLOWED_STATUS_TRANSITIONS[from_status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status transition {from_status} -> {next_status} is not allowed.",
        )
    if from_status == "READY_FOR_REVIEW" and next_status == "IN_PROGRESS" and not comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rejection comment is required when moving a defect back to In Progress.",
        )

    now = _now_utc()
    updates = {
        "status": next_status,
        "updated_at": now,
        "resolved_at": now if next_status == "RESOLVED" else None,
    }
    _defect_ref(defect_id).set(updates, merge=True)

    event_type = "STATUS_CHANGED"
    if next_status == "READY_FOR_REVIEW":
        event_type = "READY_FOR_REVIEW"
    elif next_status == "RESOLVED":
        event_type = "RESOLVED"
    elif from_status == "READY_FOR_REVIEW" and next_status == "IN_PROGRESS":
        event_type = "REVIEW_REJECTED"

    create_event(
        project_id=project_id,
        round_id=round_id,
        defect_id=defect_id,
        event_type=event_type,
        from_status=from_status,
        to_status=next_status,
        comment=comment,
        actor_id=actor_id,
        actor_role=actor_role,
    )
    current.update(updates)
    return current


def create_comment_event(
    *,
    project_id: str,
    round_id: str,
    defect_id: str,
    comment: str,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    _get_defect(project_id, round_id, defect_id)
    return create_event(
        project_id=project_id,
        round_id=round_id,
        defect_id=defect_id,
        event_type="COMMENT_ADDED",
        comment=comment,
        actor_id=actor_id,
        actor_role=actor_role,
    )


def create_file_record(
    *,
    file_id: str,
    project_id: str,
    round_id: str,
    kind: str,
    gcs_path: str,
    content_type: str | None,
    size_bytes: int,
    original_filename: str | None,
    uploaded_by: str,
    actor_role: str,
    zone_id: str | None = None,
    defect_id: str | None = None,
) -> dict[str, Any]:
    firestore_module = _require_firestore_module()
    kind_value = _validate_file_kind(kind)
    _get_round(project_id, round_id)
    if zone_id:
        _get_zone(project_id, round_id, zone_id)
    if defect_id:
        _get_defect(project_id, round_id, defect_id)

    now = _now_utc()
    payload = {
        "id": file_id,
        "project_id": project_id,
        "round_id": round_id,
        "defect_id": _clean_optional_text(defect_id),
        "zone_id": _clean_optional_text(zone_id),
        "kind": kind_value,
        "gcs_path": gcs_path,
        "content_type": _clean_optional_text(content_type),
        "size_bytes": int(size_bytes or 0),
        "original_filename": _clean_optional_text(original_filename),
        "uploaded_by": uploaded_by,
        "uploaded_at": now,
    }
    _file_ref(file_id).set(payload)

    if kind_value == "PLAN_IMAGE" and zone_id:
        _zone_ref(zone_id).set({"plan_file_id": file_id, "updated_at": now}, merge=True)
    elif kind_value == "BEFORE_PHOTO" and defect_id:
        _defect_ref(defect_id).set(
            {"before_file_ids": firestore_module.ArrayUnion([file_id]), "updated_at": now},
            merge=True,
        )
    elif kind_value == "AFTER_PHOTO" and defect_id:
        _defect_ref(defect_id).set(
            {"after_file_ids": firestore_module.ArrayUnion([file_id]), "updated_at": now},
            merge=True,
        )

    create_event(
        project_id=project_id,
        round_id=round_id,
        defect_id=defect_id,
        event_type="FILE_UPLOADED",
        actor_id=uploaded_by,
        actor_role=actor_role,
        metadata={"file_id": file_id, "kind": kind_value, "zone_id": zone_id},
    )
    return payload


def delete_file_record(file_id: str) -> dict[str, Any]:
    firestore_module = _require_firestore_module()
    payload = get_file(file_id)
    kind = payload.get("kind")
    zone_id = payload.get("zone_id")
    defect_id = payload.get("defect_id")
    if kind == "PLAN_IMAGE" and zone_id:
        _zone_ref(zone_id).set({"plan_file_id": None, "updated_at": _now_utc()}, merge=True)
    elif kind == "BEFORE_PHOTO" and defect_id:
        _defect_ref(defect_id).set(
            {"before_file_ids": firestore_module.ArrayRemove([file_id]), "updated_at": _now_utc()},
            merge=True,
        )
    elif kind == "AFTER_PHOTO" and defect_id:
        _defect_ref(defect_id).set(
            {"after_file_ids": firestore_module.ArrayRemove([file_id]), "updated_at": _now_utc()},
            merge=True,
        )
    _file_ref(file_id).delete()
    return payload


def list_events(
    *,
    project_id: str,
    round_id: str,
    defect_id: str | None = None,
) -> list[dict[str, Any]]:
    query = _project_round_query(EVENTS_COLLECTION, project_id, round_id)
    if defect_id:
        query = query.where("defect_id", "==", defect_id)
    events = [_public_doc(snapshot) for snapshot in query.stream()]
    return sorted(events, key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=UTC))


def create_event(
    *,
    project_id: str,
    round_id: str,
    defect_id: str | None,
    event_type: str,
    actor_id: str,
    actor_role: str,
    from_status: str | None = None,
    to_status: str | None = None,
    comment: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client = _client()
    doc_ref = client.collection(EVENTS_COLLECTION).document()
    payload = {
        "id": doc_ref.id,
        "project_id": project_id,
        "round_id": round_id,
        "defect_id": _clean_optional_text(defect_id),
        "event_type": _upper(event_type, "EVENT"),
        "from_status": _clean_optional_text(from_status),
        "to_status": _clean_optional_text(to_status),
        "comment": _clean_optional_text(comment),
        "actor_id": actor_id,
        "actor_role": actor_role,
        "created_at": _now_utc(),
        "metadata": metadata or {},
    }
    doc_ref.set(payload)
    return payload


def create_report_log(
    *,
    project_id: str,
    round_id: str,
    report_type: str,
    filters: dict[str, Any],
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    _get_round(project_id, round_id)
    client = _client()
    doc_ref = client.collection(REPORT_LOGS_COLLECTION).document()
    now = _now_utc()
    payload = {
        "id": doc_ref.id,
        "project_id": project_id,
        "round_id": round_id,
        "report_type": _upper(report_type),
        "filters": filters or {},
        "printed_by": actor_id,
        "printed_at": now,
    }
    doc_ref.set(payload)
    create_event(
        project_id=project_id,
        round_id=round_id,
        defect_id=None,
        event_type="REPORT_PRINTED",
        actor_id=actor_id,
        actor_role=actor_role,
        metadata={"report_type": payload["report_type"], "report_log_id": doc_ref.id},
    )
    return payload


def list_report_logs(project_id: str, round_id: str) -> list[dict[str, Any]]:
    _get_round(project_id, round_id)
    logs = [
        _public_doc(snapshot)
        for snapshot in _project_round_query(REPORT_LOGS_COLLECTION, project_id, round_id).stream()
    ]
    return sorted(logs, key=lambda item: item.get("printed_at") or datetime.min.replace(tzinfo=UTC), reverse=True)


def get_summary(project_id: str, round_id: str, subcontractor_id: str | None = None) -> dict[str, Any]:
    _get_round(project_id, round_id)
    filters = {"assigned_subcontractor_id": subcontractor_id} if subcontractor_id else {}
    defects = list_defects(project_id=project_id, round_id=round_id, filters=filters)
    total = len(defects)
    status_counts = {status_value: 0 for status_value in DEFECT_STATUSES}
    severity_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    contractor_counts: dict[str, int] = {}
    overdue_count = 0
    today = date.today().isoformat()

    for defect in defects:
        defect_status = _upper(defect.get("status"), "OPEN")
        if defect_status in status_counts:
            status_counts[defect_status] += 1
        severity = _upper(defect.get("severity"), "MINOR")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        category = str(defect.get("category") or "Other")
        category_counts[category] = category_counts.get(category, 0) + 1
        contractor = str(defect.get("assigned_subcontractor_name") or defect.get("assigned_subcontractor_id") or "Unassigned")
        contractor_counts[contractor] = contractor_counts.get(contractor, 0) + 1
        due_date = _date_value(defect.get("due_date"))
        if due_date and due_date < today and defect_status != "RESOLVED":
            overdue_count += 1

    resolved = status_counts["RESOLVED"]
    readiness_score = round((resolved / total) * 100, 1) if total else 0.0
    return {
        "project_id": project_id,
        "round_id": round_id,
        "total_defects": total,
        "open_defects": status_counts["OPEN"],
        "in_progress_defects": status_counts["IN_PROGRESS"],
        "ready_for_review_defects": status_counts["READY_FOR_REVIEW"],
        "resolved_defects": resolved,
        "overdue_count": overdue_count,
        "severity_counts": severity_counts,
        "category_counts": category_counts,
        "contractor_counts": contractor_counts,
        "readiness_score": readiness_score,
    }


def assert_subcontractor_can_access_defect(defect: dict[str, Any], subcontractor_id: str | None) -> None:
    if not subcontractor_id or defect.get("assigned_subcontractor_id") != subcontractor_id:
        raise _forbidden("This defect is not assigned to the current subcontractor.")
