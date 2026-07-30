"""Environment-locked, read-only Google Cloud operations adapter."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from urllib.parse import quote

import httpx

from app.config.settings import Settings

CLOUD_PLATFORM_READ_SCOPE = "https://www.googleapis.com/auth/cloud-platform.read-only"
LOGGING_ENTRIES_URL = "https://logging.googleapis.com/v2/entries:list"
MAX_GCP_RESPONSE_BYTES = 2 * 1024 * 1024

ServiceAlias = Literal["frontend", "backend", "mcp"]
ComponentName = Literal["mcp", "backend", "cloud_sql", "firestore", "gcs", "oauth"]
ResourceType = Literal[
    "cloud_run",
    "cloud_sql",
    "firestore",
    "gcs",
    "logging",
    "artifact_registry",
]
DataSourceName = Literal["backend", "cloud_sql", "firestore", "gcs", "oauth"]

_SAFE_SEVERITIES = {"WARNING", "ERROR", "CRITICAL", "ALERT", "EMERGENCY"}
_SAFE_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_.~-]{0,63}$")
_URL = re.compile(r"https?://[^\s\]\[()<>{}\"']+", re.IGNORECASE)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_CREDENTIAL = re.compile(
    r"(?i)\b(?:authorization|token|secret|access[_ -]?token|refresh[_ -]?token|"
    r"api[_ -]?key|client[_ -]?secret|password|private[_ -]?key)\b"
    r"\s*[:=]\s*(?:bearer\s+)?[^\s,;]+|\bbearer\s+[^\s,;]+"
)
_GCS_PATH = re.compile(r"gs://[^\s]+", re.IGNORECASE)
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


class GcpOperationsError(RuntimeError):
    pass


class GcpOperationsInvalidInput(GcpOperationsError):
    pass


class GcpOperationsClientProtocol(Protocol):
    async def get_system_health(self, *, components: list[str]) -> dict[str, Any]: ...

    async def get_resource_summary(self, *, resource_types: list[str]) -> dict[str, Any]: ...

    async def get_cloud_run_status(self, *, service_alias: str) -> dict[str, Any]: ...

    async def search_application_errors(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        service_alias: str | None,
        workflow: str | None,
        severities: list[str],
        cursor: str | None,
        limit: int,
    ) -> dict[str, Any]: ...

    async def get_data_source_health(self, *, sources: list[str]) -> dict[str, Any]: ...


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _quoted(value: str) -> str:
    if any(character in value for character in {'"', "\\", "\n", "\r"}):
        raise GcpOperationsInvalidInput("Unsupported Cloud Logging filter value.")
    return f'"{value}"'


def _safe_summary(value: object) -> str:
    text = " ".join(str(value or "").split())
    text = _CREDENTIAL.sub("[REDACTED_CREDENTIAL]", text)
    text = _URL.sub("[REDACTED_URL]", text)
    text = _GCS_PATH.sub("[REDACTED_PATH]", text)
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _UUID.sub("[REDACTED_ID]", text)
    return text[:500] or "Application error metadata is available."


def build_application_error_filter(
    settings: Settings,
    *,
    date_from: datetime,
    date_to: datetime,
    service_alias: str | None,
    workflow: str | None,
    severities: list[str],
) -> str:
    services = settings.allowed_cloud_run_services
    if service_alias is not None and service_alias not in services:
        raise GcpOperationsInvalidInput("Unknown service alias.")
    selected_services = [services[service_alias]] if service_alias else list(services.values())
    selected_severities = severities or ["ERROR", "CRITICAL", "ALERT", "EMERGENCY"]
    if any(value not in _SAFE_SEVERITIES for value in selected_severities):
        raise GcpOperationsInvalidInput("Unknown severity.")

    clauses = [
        'resource.type="cloud_run_revision"',
        f'resource.labels.location={_quoted(settings.gcp_region)}',
        "(" + " OR ".join(
            f'resource.labels.service_name={_quoted(value)}' for value in selected_services
        ) + ")",
        "(" + " OR ".join(f"severity={value}" for value in selected_severities) + ")",
        f"timestamp>={_quoted(_timestamp(date_from))}",
        f"timestamp<={_quoted(_timestamp(date_to))}",
    ]
    if workflow:
        clauses.append(
            "(jsonPayload.workflow="
            f"{_quoted(workflow)} OR jsonPayload.message:{_quoted(workflow)} OR "
            f"textPayload:{_quoted(workflow)})"
        )
    return " AND ".join(clauses)


def _response_message(entry: dict[str, Any]) -> str:
    json_payload = entry.get("jsonPayload")
    if isinstance(json_payload, dict):
        for field in ("message", "error", "exception"):
            if isinstance(json_payload.get(field), str):
                return _safe_summary(json_payload[field])
    text_payload = entry.get("textPayload")
    if isinstance(text_payload, str):
        return _safe_summary(text_payload)
    proto_payload = entry.get("protoPayload")
    if isinstance(proto_payload, dict):
        status = proto_payload.get("status")
        if isinstance(status, dict) and isinstance(status.get("message"), str):
            return _safe_summary(status["message"])
    return "Application error metadata is available."


class GoogleCloudOperationsClient:
    """Calls only resources compiled into the current environment profile."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _authorized_json(
        self,
        method: str,
        url: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            credentials, _project = google.auth.default(scopes=[CLOUD_PLATFORM_READ_SCOPE])
            session = AuthorizedSession(credentials)
            response = session.request(
                method,
                url,
                json=body,
                timeout=self._settings.backend_timeout_seconds,
            )
        except Exception as exc:
            raise GcpOperationsError("Google Cloud operations source is unavailable.") from exc
        if response.status_code in {400, 422}:
            raise GcpOperationsInvalidInput("Google Cloud rejected the bounded request.")
        if response.status_code != 200:
            raise GcpOperationsError("Google Cloud operations source is unavailable.")
        if len(response.content) > MAX_GCP_RESPONSE_BYTES:
            raise GcpOperationsError("Google Cloud response exceeded the allowed size.")
        try:
            data = response.json()
        except ValueError as exc:
            raise GcpOperationsError("Google Cloud returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise GcpOperationsError("Google Cloud returned an invalid envelope.")
        return data

    async def _get(self, url: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._authorized_json, "GET", url)

    async def _probe(self, url: str) -> str:
        try:
            await self._get(url)
            return "available"
        except GcpOperationsError:
            return "unavailable"

    def _cloud_run_url(self, service_alias: str) -> str:
        service_name = self._settings.allowed_cloud_run_services.get(service_alias)
        if service_name is None:
            raise GcpOperationsInvalidInput("Unknown service alias.")
        return (
            "https://run.googleapis.com/v2/projects/"
            f"{self._settings.gcp_project_id}/locations/{self._settings.gcp_region}/"
            f"services/{service_name}"
        )

    def _cloud_sql_url(self) -> str:
        instance = self._settings.cloud_sql_instance.rsplit(":", 1)[-1]
        return (
            "https://sqladmin.googleapis.com/sql/v1beta4/projects/"
            f"{self._settings.gcp_project_id}/instances/{instance}"
        )

    def _firestore_url(self) -> str:
        database = quote(self._settings.firestore_database_id, safe="()")
        return (
            "https://firestore.googleapis.com/v1/projects/"
            f"{self._settings.gcp_project_id}/databases/{database}"
        )

    def _bucket_url(self, bucket: str) -> str:
        return f"https://storage.googleapis.com/storage/v1/b/{quote(bucket, safe='')}?fields=name"

    def _logging_view_url(self) -> str:
        return f"https://logging.googleapis.com/v2/{self._settings.operational_log_view}"

    def _artifact_url(self) -> str:
        return (
            "https://artifactregistry.googleapis.com/v1/projects/"
            f"{self._settings.gcp_project_id}/locations/{self._settings.gcp_region}/"
            f"repositories/{self._settings.allowed_artifact_repository}"
        )

    async def _backend_health(self) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.backend_timeout_seconds,
                follow_redirects=False,
            ) as client:
                response = await client.get(f"{self._settings.canonical_backend_url}/health")
            if response.status_code != 200 or len(response.content) > 64 * 1024:
                return "unavailable"
            payload = response.json()
            return "available" if payload.get("status") == "ok" else "degraded"
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return "unavailable"

    async def _oauth_health(self) -> str:
        issuer = self._settings.canonical_issuer.rstrip("/")
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.backend_timeout_seconds,
                follow_redirects=False,
            ) as client:
                response = await client.get(f"{issuer}/.well-known/openid-configuration")
            if response.status_code != 200 or len(response.content) > 256 * 1024:
                return "unavailable"
            payload = response.json()
            reported = str(payload.get("issuer") or "").rstrip("/")
            return "available" if reported == issuer else "degraded"
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return "unavailable"

    async def _gcs_health(self) -> str:
        statuses = await asyncio.gather(
            *(
                self._probe(self._bucket_url(bucket))
                for bucket in sorted(self._settings.allowed_buckets)
            )
        )
        available = statuses.count("available")
        if available == len(statuses):
            return "available"
        return "degraded" if available else "unavailable"

    async def _source_status(self, source: str) -> str:
        if source == "backend":
            return await self._backend_health()
        if source == "cloud_sql":
            return await self._probe(self._cloud_sql_url())
        if source == "firestore":
            return await self._probe(self._firestore_url())
        if source == "gcs":
            return await self._gcs_health()
        if source == "oauth":
            return await self._oauth_health()
        raise GcpOperationsInvalidInput("Unknown data source.")

    @staticmethod
    def _overall(statuses: list[str]) -> str:
        if statuses and all(value == "available" for value in statuses):
            return "healthy"
        if any(value in {"available", "degraded"} for value in statuses):
            return "degraded"
        return "unavailable"

    async def get_system_health(self, *, components: list[str]) -> dict[str, Any]:
        selected = components or ["mcp", "backend", "cloud_sql", "firestore", "gcs", "oauth"]
        allowed = {"mcp", "backend", "cloud_sql", "firestore", "gcs", "oauth"}
        if any(value not in allowed for value in selected):
            raise GcpOperationsInvalidInput("Unknown system component.")
        checks = [
            asyncio.sleep(0, result="available") if item == "mcp" else self._source_status(item)
            for item in selected
        ]
        statuses = await asyncio.gather(*checks)
        checked_at = datetime.now(UTC)
        items = [
            {"component": name, "status": status, "checked_at": checked_at}
            for name, status in zip(selected, statuses, strict=True)
        ]
        return {
            "overall_status": self._overall(statuses),
            "components": items,
            "returned_count": len(items),
            "partial": any(value != "available" for value in statuses),
            "warnings": (
                [
                    {
                        "code": "SOURCE_UNAVAILABLE",
                        "message": "One or more bounded health checks were unavailable.",
                    }
                ]
                if any(value != "available" for value in statuses)
                else []
            ),
            "source_read_at": checked_at,
        }

    async def get_data_source_health(self, *, sources: list[str]) -> dict[str, Any]:
        selected = sources or ["backend", "cloud_sql", "firestore", "gcs", "oauth"]
        allowed = {"backend", "cloud_sql", "firestore", "gcs", "oauth"}
        if any(value not in allowed for value in selected):
            raise GcpOperationsInvalidInput("Unknown data source.")
        statuses = await asyncio.gather(*(self._source_status(item) for item in selected))
        checked_at = datetime.now(UTC)
        items = [
            {"source": name, "status": status, "checked_at": checked_at}
            for name, status in zip(selected, statuses, strict=True)
        ]
        return {
            "overall_status": self._overall(statuses),
            "sources": items,
            "returned_count": len(items),
            "partial": any(value != "available" for value in statuses),
            "warnings": (
                [
                    {
                        "code": "SOURCE_UNAVAILABLE",
                        "message": "One or more bounded data-source checks were unavailable.",
                    }
                ]
                if any(value != "available" for value in statuses)
                else []
            ),
            "source_read_at": checked_at,
        }

    async def get_cloud_run_status(self, *, service_alias: str) -> dict[str, Any]:
        data = await self._get(self._cloud_run_url(service_alias))
        terminal = (
            data.get("terminalCondition")
            if isinstance(data.get("terminalCondition"), dict)
            else {}
        )
        state = str(terminal.get("state") or "STATE_UNSPECIFIED")
        status = "available" if state == "CONDITION_SUCCEEDED" else "degraded"
        revision = str(data.get("latestReadyRevision") or "").rsplit("/", 1)[-1] or None
        traffic = [
            int(item.get("percent") or 0)
            for item in list(data.get("trafficStatuses") or [])
            if isinstance(item, dict)
        ]
        return {
            "service_alias": service_alias,
            "status": status,
            "latest_ready_revision": revision,
            "ready_traffic_percent": min(sum(traffic), 100),
            "condition": state,
            "last_updated_at": data.get("updateTime"),
            "source_read_at": datetime.now(UTC),
        }

    async def _resource_group(self, resource_type: str) -> dict[str, Any]:
        if resource_type == "cloud_run":
            aliases = list(self._settings.allowed_cloud_run_services)
            statuses = await asyncio.gather(
                *(self._probe(self._cloud_run_url(alias)) for alias in aliases)
            )
        elif resource_type == "cloud_sql":
            aliases = ["primary"]
            statuses = [await self._probe(self._cloud_sql_url())]
        elif resource_type == "firestore":
            aliases = ["product_database"]
            statuses = [await self._probe(self._firestore_url())]
        elif resource_type == "gcs":
            aliases = [
                f"bucket_{index + 1}"
                for index in range(len(self._settings.allowed_buckets))
            ]
            statuses = await asyncio.gather(
                *(
                    self._probe(self._bucket_url(bucket))
                    for bucket in sorted(self._settings.allowed_buckets)
                )
            )
        elif resource_type == "logging":
            aliases = ["operational_view"]
            statuses = [await self._probe(self._logging_view_url())]
        elif resource_type == "artifact_registry":
            aliases = ["product_images"]
            statuses = [await self._probe(self._artifact_url())]
        else:
            raise GcpOperationsInvalidInput("Unknown resource type.")
        return {
            "resource_type": resource_type,
            "configured_count": len(aliases),
            "available_count": statuses.count("available"),
            "status": self._overall(statuses),
            "aliases": aliases,
        }

    async def get_resource_summary(self, *, resource_types: list[str]) -> dict[str, Any]:
        selected = resource_types or [
            "cloud_run",
            "cloud_sql",
            "firestore",
            "gcs",
            "logging",
            "artifact_registry",
        ]
        allowed = {"cloud_run", "cloud_sql", "firestore", "gcs", "logging", "artifact_registry"}
        if any(value not in allowed for value in selected):
            raise GcpOperationsInvalidInput("Unknown resource type.")
        items = await asyncio.gather(*(self._resource_group(item) for item in selected))
        checked_at = datetime.now(UTC)
        return {
            "resources": items,
            "returned_count": len(items),
            "partial": any(item["status"] != "healthy" for item in items),
            "warnings": (
                [
                    {
                        "code": "SOURCE_UNAVAILABLE",
                        "message": "One or more allowlisted resource checks were unavailable.",
                    }
                ]
                if any(item["status"] != "healthy" for item in items)
                else []
            ),
            "source_read_at": checked_at,
        }

    async def search_application_errors(
        self,
        *,
        date_from: datetime,
        date_to: datetime,
        service_alias: str | None,
        workflow: str | None,
        severities: list[str],
        cursor: str | None,
        limit: int,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "resourceNames": [self._settings.operational_log_view],
            "filter": build_application_error_filter(
                self._settings,
                date_from=date_from,
                date_to=date_to,
                service_alias=service_alias,
                workflow=workflow,
                severities=severities,
            ),
            "orderBy": "timestamp desc",
            "pageSize": min(limit, 50),
        }
        if cursor:
            body["pageToken"] = cursor
        data = await asyncio.to_thread(
            self._authorized_json,
            "POST",
            LOGGING_ENTRIES_URL,
            body=body,
        )
        service_by_name = {
            value: key for key, value in self._settings.allowed_cloud_run_services.items()
        }
        items: list[dict[str, Any]] = []
        for entry in list(data.get("entries") or []):
            if not isinstance(entry, dict):
                continue
            resource = entry.get("resource") if isinstance(entry.get("resource"), dict) else {}
            labels = resource.get("labels") if isinstance(resource.get("labels"), dict) else {}
            alias = service_by_name.get(str(labels.get("service_name") or ""))
            severity = str(entry.get("severity") or "DEFAULT").upper()
            if alias is None or severity not in _SAFE_SEVERITIES:
                continue
            payload = entry.get("jsonPayload") if isinstance(entry.get("jsonPayload"), dict) else {}
            code_value = str(payload.get("error_code") or payload.get("code") or "")
            code = code_value if _SAFE_CODE.fullmatch(code_value) else None
            identity = json.dumps(
                [entry.get("timestamp"), alias, entry.get("insertId"), _response_message(entry)],
                separators=(",", ":"),
            )
            items.append(
                {
                    "event_id": "op_" + hashlib.sha256(identity.encode()).hexdigest()[:24],
                    "timestamp": entry.get("timestamp"),
                    "severity": severity,
                    "service_alias": alias,
                    "workflow": workflow,
                    "error_code": code,
                    "summary": _response_message(entry),
                }
            )
        return {
            "items": items[:limit],
            "returned_count": min(len(items), limit),
            "next_cursor": data.get("nextPageToken"),
            "source_read_at": datetime.now(UTC),
        }
