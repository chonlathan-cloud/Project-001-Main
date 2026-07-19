"""Privacy-safe structured logging for Cloud Run and local development."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_RAYADEE_LOGGER_NAMES = (
    "rayadee",
    "app.api.v1.auth",
    "app.api.v1.daily_reports",
    "app.services.daily_report_line_service",
    "app.services.daily_report_notification_service",
)
_STRUCTURED_FIELDS = {
    "attempt_count",
    "cycles_ready",
    "cycle_id",
    "delivery_job_id",
    "duration_ms",
    "error_category",
    "event",
    "event_type",
    "limit",
    "media_id",
    "method",
    "notification_type",
    "notifications_failed",
    "notifications_sent",
    "path",
    "projects_checked",
    "project_id",
    "remaining",
    "report_id",
    "request_id",
    "status",
    "status_code",
    "submission_id",
    "size_bytes",
    "version",
}


class JsonLogFormatter(logging.Formatter):
    """Render one JSON object per line without copying arbitrary record fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field_name in _STRUCTURED_FIELDS:
            value = getattr(record, field_name, None)
            if value is not None:
                payload[field_name] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_structured_logging(level: str = "INFO") -> None:
    """Install JSON handlers only on RAYADEE-owned logger namespaces."""

    normalized_level = getattr(logging, str(level or "INFO").upper(), logging.INFO)
    for logger_name in _RAYADEE_LOGGER_NAMES:
        target_logger = logging.getLogger(logger_name)
        target_logger.setLevel(normalized_level)
        target_logger.propagate = False
        if any(
            getattr(handler, "_rayadee_json_handler", False)
            for handler in target_logger.handlers
        ):
            continue
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(normalized_level)
        handler.setFormatter(JsonLogFormatter())
        handler._rayadee_json_handler = True  # type: ignore[attr-defined]
        target_logger.addHandler(handler)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    message: str | None = None,
    **fields: object,
) -> None:
    """Log an allow-listed operational event without private content."""

    extra = {"event": event}
    extra.update(
        {
            key: value
            for key, value in fields.items()
            if key in _STRUCTURED_FIELDS and value is not None
        }
    )
    logger.log(level, message or event.replace("_", " "), extra=extra)


def safe_request_id(value: str | None) -> str:
    candidate = str(value or "").strip()
    if _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid4().hex


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach request IDs, security headers, and privacy-safe request logs."""

    async def dispatch(self, request: Request, call_next):
        request_id = safe_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started_at = perf_counter()
        logger = logging.getLogger("rayadee.http")
        try:
            response = await call_next(request)
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "request_unhandled_exception",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round((perf_counter() - started_at) * 1000, 2),
                error_category=type(exc).__name__,
            )
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        status_code = response.status_code
        level = (
            logging.ERROR
            if status_code >= 500
            else logging.WARNING
            if status_code >= 400
            else logging.INFO
        )
        log_event(
            logger,
            level,
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(self), geolocation=()"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
