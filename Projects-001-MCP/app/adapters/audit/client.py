"""Bounded Cloud Logging adapter for Product MCP audit-event reads."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol

from pydantic import ValidationError

from app.audit.models import ProductAuditEvent
from app.config.settings import Settings

LOGGING_ENTRIES_URL = "https://logging.googleapis.com/v2/entries:list"
MAX_AUDIT_RESPONSE_BYTES = 2 * 1024 * 1024


class AuditReadError(RuntimeError):
    pass


class AuditReadNotFound(AuditReadError):
    pass


class AuditReadInvalidInput(AuditReadError):
    pass


class AuditReadClientProtocol(Protocol):
    async def search(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        tool_names: list[str],
        decisions: list[Literal["allow", "deny", "error"]],
        domain: str | None,
        subject_id: str | None,
        cursor: str | None,
        limit: int,
    ) -> dict[str, Any]: ...

    async def get(self, *, event_id: str) -> dict[str, Any]: ...


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _quoted(value: str) -> str:
    if any(character in value for character in {'"', "\\", "\n", "\r"}):
        raise AuditReadInvalidInput("Audit filter value contains unsupported characters.")
    return f'"{value}"'


def _field_clause(field: str, value: str) -> str:
    quoted = _quoted(value)
    escaped_text = json.dumps(f'"{field}":"{value}"')
    return f"(jsonPayload.{field}={quoted} OR textPayload:{escaped_text})"


def build_audit_filter(
    settings: Settings,
    *,
    date_from: datetime,
    date_to: datetime,
    tool_names: list[str],
    decisions: list[str],
    domain: str | None,
    subject_id: str | None,
    event_id: str | None = None,
) -> str:
    clauses = [
        'resource.type="cloud_run_revision"',
        f"resource.labels.service_name={_quoted(settings.service_name)}",
        "(jsonPayload.log_type=\"product_audit\" OR "
        'textPayload:"\\\"log_type\\\":\\\"product_audit\\\"")',
        f'timestamp>={_quoted(_utc(date_from).isoformat().replace("+00:00", "Z"))}',
        f'timestamp<={_quoted(_utc(date_to).isoformat().replace("+00:00", "Z"))}',
    ]
    if tool_names:
        clauses.append(
            "("
            + " OR ".join(
                _field_clause("tool_name", value) for value in tool_names
            )
            + ")"
        )
    if decisions:
        clauses.append(
            "(" + " OR ".join(
                _field_clause("authorization_decision", value) for value in decisions
            ) + ")"
        )
    if domain:
        clauses.append(_field_clause("target_domain", domain))
    if subject_id:
        clauses.append(_field_clause("user_subject_id", subject_id))
    if event_id:
        clauses.append(_field_clause("event_id", event_id))
    return " AND ".join(clauses)


def _parse_product_audit_text(value: str) -> dict[str, Any] | None:
    marker = '{"log_type":"product_audit"'
    start = value.find(marker)
    if start < 0:
        return None
    try:
        parsed, _end = json.JSONDecoder().raw_decode(value[start:])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _payload_from_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    payload = entry.get("jsonPayload")
    if isinstance(payload, dict):
        if isinstance(payload.get("message"), str):
            nested = _parse_product_audit_text(payload["message"])
            if nested is not None:
                payload = nested
        return payload
    text_payload = entry.get("textPayload")
    if not isinstance(text_payload, str):
        return None
    return _parse_product_audit_text(text_payload)


def _safe_event(entry: dict[str, Any]) -> dict[str, Any] | None:
    payload = _payload_from_entry(entry)
    if not payload or payload.get("log_type") != "product_audit":
        return None
    allowlisted = {
        field: payload[field]
        for field in ProductAuditEvent.model_fields
        if field in payload
    }
    allowlisted.setdefault("timestamp", entry.get("timestamp"))
    try:
        return ProductAuditEvent.model_validate(allowlisted).model_dump(mode="json")
    except ValidationError:
        return None


class GoogleCloudAuditReadClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _entries(self, body: dict[str, Any]) -> dict[str, Any]:
        try:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            credentials, _project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/logging.read"]
            )
            session = AuthorizedSession(credentials)
            response = session.post(
                LOGGING_ENTRIES_URL,
                json=body,
                timeout=self._settings.backend_timeout_seconds,
            )
        except Exception as exc:
            raise AuditReadError("Product Audit source is unavailable.") from exc
        if response.status_code in {400, 422}:
            raise AuditReadInvalidInput("Cloud Logging rejected the bounded audit filter.")
        if response.status_code in {403, 404}:
            raise AuditReadNotFound
        if response.status_code != 200:
            raise AuditReadError("Product Audit source is unavailable.")
        if len(response.content) > MAX_AUDIT_RESPONSE_BYTES:
            raise AuditReadError("Product Audit response exceeded the allowed size.")
        try:
            data = response.json()
        except ValueError as exc:
            raise AuditReadError("Product Audit source returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise AuditReadError("Product Audit source returned an invalid envelope.")
        return data

    async def search(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        tool_names: list[str],
        decisions: list[Literal["allow", "deny", "error"]],
        domain: str | None,
        subject_id: str | None,
        cursor: str | None,
        limit: int,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "resourceNames": [self._settings.audit_log_view],
            "filter": build_audit_filter(
                self._settings,
                date_from=date_from,
                date_to=date_to,
                tool_names=tool_names,
                decisions=decisions,
                domain=domain,
                subject_id=subject_id,
            ),
            "orderBy": "timestamp desc",
            "pageSize": min(limit, 50),
        }
        if cursor:
            body["pageToken"] = cursor
        data = await asyncio.to_thread(self._entries, body)
        items = [
            event
            for entry in list(data.get("entries") or [])
            if isinstance(entry, dict) and (event := _safe_event(entry)) is not None
        ]
        return {
            "items": items[:limit],
            "returned_count": min(len(items), limit),
            "next_cursor": data.get("nextPageToken"),
            "source_read_at": datetime.now(UTC),
        }

    async def get(self, *, event_id: str) -> dict[str, Any]:
        date_to = datetime.now(UTC)
        date_from = date_to - timedelta(days=self._settings.audit_read_max_days)
        data = await asyncio.to_thread(
            self._entries,
            {
                "resourceNames": [self._settings.audit_log_view],
                "filter": build_audit_filter(
                    self._settings,
                    date_from=date_from,
                    date_to=date_to,
                    tool_names=[],
                    decisions=[],
                    domain=None,
                    subject_id=None,
                    event_id=event_id,
                ),
                "orderBy": "timestamp desc",
                "pageSize": 2,
            },
        )
        event = next(
            (
                safe
                for entry in list(data.get("entries") or [])
                if isinstance(entry, dict)
                and (safe := _safe_event(entry)) is not None
                and safe.get("event_id") == event_id
            ),
            None,
        )
        if event is None:
            raise AuditReadNotFound
        return {**event, "source_read_at": datetime.now(UTC)}
