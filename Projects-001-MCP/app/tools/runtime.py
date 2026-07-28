"""Shared authorization, audit and response-envelope orchestration."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from mcp.server.auth.middleware.auth_context import get_access_token

from app.audit.emitter import AuditEmitter, AuditUnavailable
from app.audit.models import ProductAuditEvent
from app.config.settings import Settings
from app.policy.client import PolicyClient, PolicyUnavailable
from app.policy.engine import PolicyEngine
from app.policy.models import AccessContext
from app.schemas.common import (
    AccessScope,
    ErrorCode,
    Freshness,
    Pagination,
    SourceReference,
    ToolError,
    ToolResponse,
    WarningItem,
    utc_now,
)
from app.server.request_context import current_request_id
from app.tools.registry import ToolDefinition


class NotFoundOrForbidden(RuntimeError):
    pass


class InvalidToolInput(RuntimeError):
    pass


class ToolRateLimited(RuntimeError):
    pass


class FixedWindowToolRateLimiter:
    """Per-instance, per-subject defense-in-depth limit for tool execution."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, int], int] = {}

    def consume(
        self,
        *,
        subject_id: str,
        limit: int,
        now: float | None = None,
    ) -> bool:
        current_time = time.time() if now is None else now
        window = int(current_time // 60)
        key = (subject_id, window)
        count = self._counters.get(key, 0) + 1
        self._counters[key] = count
        if len(self._counters) > 10_000:
            self._counters = {
                item_key: value
                for item_key, value in self._counters.items()
                if item_key[1] >= window - 1
            }
        return count <= limit


@dataclass(slots=True)
class ToolPayload:
    data: Any
    sources: list[SourceReference] = field(default_factory=list)
    pagination: Pagination | None = None
    freshness: Freshness | None = None
    warnings: list[WarningItem] = field(default_factory=list)
    partial: bool = False
    result_count: int = 1


ToolOperation = Callable[[AccessContext], Awaitable[ToolPayload]]


class ToolRuntime:
    def __init__(
        self,
        settings: Settings,
        policy_client: PolicyClient,
        audit_emitter: AuditEmitter,
        rate_limiter: FixedWindowToolRateLimiter | None = None,
    ) -> None:
        self._settings = settings
        self._policy_client = policy_client
        self._policy = PolicyEngine(settings.environment)
        self._audit = audit_emitter
        self._rate_limiter = rate_limiter or FixedWindowToolRateLimiter()

    async def execute(
        self,
        definition: ToolDefinition,
        operation: ToolOperation,
        *,
        project_id: str | None = None,
        target_record_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        request_id = current_request_id()
        token = get_access_token()
        if token is None or not token.subject:
            return self._error(
                request_id,
                ErrorCode.UNAUTHENTICATED,
                "A valid MCP OAuth access token is required.",
            )

        claims = token.claims or {}
        issuer = str(claims.get("iss") or "").rstrip("/")
        subject_id = self._stable_subject_id(issuer, token.subject)
        channel = self._client_channel(claims)
        if not self._rate_limiter.consume(
            subject_id=subject_id,
            limit=self._settings.rate_limit_per_minute,
        ):
            await self._best_effort_audit(
                definition=definition,
                request_id=request_id,
                channel=channel,
                subject_id=subject_id,
                role="unknown",
                decision="deny",
                reason="subject_rate_limited",
                result_status="denied",
                started=started,
                target_record_ids=target_record_ids,
                error_code=ErrorCode.RATE_LIMITED.value,
            )
            return self._error(
                request_id,
                ErrorCode.RATE_LIMITED,
                "The MCP request limit was reached. Try again shortly.",
                retryable=True,
            )
        try:
            access = await self._policy_client.resolve_access(
                subject=token.subject,
                issuer=issuer,
                client_id=token.client_id,
                request_id=request_id,
            )
        except PolicyUnavailable:
            await self._best_effort_audit(
                definition=definition,
                request_id=request_id,
                channel=channel,
                subject_id=subject_id,
                role="unknown",
                decision="error",
                reason="policy_source_unavailable",
                result_status="error",
                started=started,
                error_code=ErrorCode.SOURCE_UNAVAILABLE.value,
            )
            return self._error(
                request_id,
                ErrorCode.SOURCE_UNAVAILABLE,
                "Product authorization is temporarily unavailable.",
                retryable=True,
            )

        decision = self._policy.authorize(
            access,
            required_permissions=definition.required_permissions,
            project_id=project_id,
        )
        if not decision.allowed:
            await self._best_effort_audit(
                definition=definition,
                request_id=request_id,
                channel=channel,
                subject_id=access.user_id,
                role=access.role,
                decision="deny",
                reason=decision.reason_code,
                result_status="denied",
                started=started,
                target_record_ids=target_record_ids,
                error_code=ErrorCode.NOT_FOUND_OR_FORBIDDEN.value,
            )
            return self._error(
                request_id,
                ErrorCode.NOT_FOUND_OR_FORBIDDEN,
                "The requested record is not available in the current access scope.",
            )

        if definition.sensitive:
            try:
                await self._emit_audit(
                    definition=definition,
                    request_id=request_id,
                    channel=channel,
                    subject_id=access.user_id,
                    role=access.role,
                    decision="allow",
                    reason="sensitive_access_started",
                    result_status="started",
                    started=started,
                    target_record_ids=target_record_ids,
                )
            except AuditUnavailable:
                return self._error(
                    request_id,
                    ErrorCode.SOURCE_UNAVAILABLE,
                    "Mandatory sensitive-access audit is unavailable.",
                    retryable=True,
                )

        try:
            payload = await operation(access)
        except InvalidToolInput:
            await self._best_effort_audit(
                definition=definition,
                request_id=request_id,
                channel=channel,
                subject_id=access.user_id,
                role=access.role,
                decision="deny",
                reason="invalid_input",
                result_status="denied",
                started=started,
                target_record_ids=target_record_ids,
                error_code=ErrorCode.INVALID_INPUT.value,
            )
            return self._error(
                request_id,
                ErrorCode.INVALID_INPUT,
                "The request did not match the tool contract.",
            )
        except ToolRateLimited:
            await self._best_effort_audit(
                definition=definition,
                request_id=request_id,
                channel=channel,
                subject_id=access.user_id,
                role=access.role,
                decision="error",
                reason="rate_limited",
                result_status="error",
                started=started,
                target_record_ids=target_record_ids,
                error_code=ErrorCode.RATE_LIMITED.value,
            )
            return self._error(
                request_id,
                ErrorCode.RATE_LIMITED,
                "The authorized source rate limit was reached.",
                retryable=True,
            )
        except NotFoundOrForbidden:
            await self._best_effort_audit(
                definition=definition,
                request_id=request_id,
                channel=channel,
                subject_id=access.user_id,
                role=access.role,
                decision="deny",
                reason="domain_or_record_not_visible",
                result_status="denied",
                started=started,
                target_record_ids=target_record_ids,
                error_code=ErrorCode.NOT_FOUND_OR_FORBIDDEN.value,
            )
            return self._error(
                request_id,
                ErrorCode.NOT_FOUND_OR_FORBIDDEN,
                "The requested record is not available in the current access scope.",
            )
        except Exception:
            await self._best_effort_audit(
                definition=definition,
                request_id=request_id,
                channel=channel,
                subject_id=access.user_id,
                role=access.role,
                decision="error",
                reason="tool_source_error",
                result_status="error",
                started=started,
                target_record_ids=target_record_ids,
                error_code=ErrorCode.SOURCE_UNAVAILABLE.value,
            )
            return self._error(
                request_id,
                ErrorCode.SOURCE_UNAVAILABLE,
                "An authorized source could not be read.",
                retryable=True,
            )

        audit_ok = await self._best_effort_audit(
            definition=definition,
            request_id=request_id,
            channel=channel,
            subject_id=access.user_id,
            role=access.role,
            decision="allow",
            reason="policy_allow",
            result_status="success",
            started=started,
            target_record_ids=target_record_ids,
            source_systems=[source.source_system for source in payload.sources],
            result_count=payload.result_count,
        )
        if not audit_ok:
            if definition.sensitive:
                return self._error(
                    request_id,
                    ErrorCode.SOURCE_UNAVAILABLE,
                    "Mandatory sensitive-access audit is unavailable.",
                    retryable=True,
                )
            payload.warnings.append(
                WarningItem(
                    code="AUDIT_DEGRADED",
                    message=(
                        "The non-sensitive result was returned while audit telemetry was degraded."
                    ),
                )
            )

        response = ToolResponse(
            request_id=request_id,
            environment=self._settings.environment,
            data=payload.data,
            sources=payload.sources,
            pagination=payload.pagination,
            access_scope=AccessScope(
                all_projects=access.role == "owner" or access.all_projects_read,
                project_ids=(
                    []
                    if access.role == "owner" or access.all_projects_read
                    else sorted(access.assigned_project_ids)
                ),
                permissions_applied=sorted(definition.required_permissions),
            ),
            freshness=payload.freshness,
            warnings=payload.warnings,
            partial=payload.partial,
        )
        return response.as_transport_dict()

    def _error(
        self,
        request_id: str,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
    ) -> dict[str, Any]:
        return ToolResponse(
            request_id=request_id,
            environment=self._settings.environment,
            error=ToolError(code=code, message=message, retryable=retryable),
        ).as_transport_dict()

    async def _best_effort_audit(self, **kwargs: Any) -> bool:
        try:
            await self._emit_audit(**kwargs)
            return True
        except AuditUnavailable:
            return False

    async def _emit_audit(
        self,
        *,
        definition: ToolDefinition,
        request_id: str,
        channel: str,
        subject_id: str,
        role: str,
        decision: str,
        reason: str,
        result_status: str,
        started: float,
        target_record_ids: list[str] | None = None,
        source_systems: list[str] | None = None,
        result_count: int = 0,
        error_code: str | None = None,
    ) -> None:
        elapsed = time.monotonic() - started
        latency = (
            "lt_1s"
            if elapsed < 1
            else "1s_to_5s"
            if elapsed < 5
            else "5s_to_15s"
            if elapsed < 15
            else "gte_15s"
        )
        event = ProductAuditEvent(
            event_id=uuid4().hex,
            request_id=request_id,
            timestamp=utc_now(),
            environment=self._settings.environment,
            client_channel=channel,
            user_subject_id=subject_id,
            effective_role=role,
            tool_name=definition.name,
            authorization_decision=decision,
            policy_reason_code=reason,
            target_domain=definition.domain.value,
            target_record_ids=(target_record_ids or [])[:20],
            sensitive_content=definition.sensitive,
            source_systems=list(dict.fromkeys(source_systems or []))[:10],
            result_count=result_count,
            result_status=result_status,
            latency_class=latency,
            error_code=error_code,
        )
        await self._audit.emit(event)

    @staticmethod
    def _stable_subject_id(issuer: str, subject: str) -> str:
        digest = hashlib.sha256(f"{issuer}|{subject}".encode()).hexdigest()[:24]
        return f"oauth_{digest}"

    @staticmethod
    def _client_channel(claims: dict[str, Any]) -> str:
        value = str(claims.get("client_channel") or "").strip().lower()
        return value if value in {"chatgpt", "codex", "internal_chat", "inspector"} else "unknown"
