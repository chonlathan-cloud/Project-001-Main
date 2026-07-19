"""Small per-instance rate limiter for high-risk beta endpoints."""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.observability import log_event


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    method: str
    path_pattern: re.Pattern[str]
    requests_per_minute: int

    @classmethod
    def create(
        cls,
        *,
        name: str,
        method: str,
        path_pattern: str,
        requests_per_minute: int,
    ) -> "RateLimitRule":
        return cls(
            name=name,
            method=method.upper(),
            path_pattern=re.compile(path_pattern),
            requests_per_minute=max(1, requests_per_minute),
        )


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class FixedWindowRateLimiter:
    """Bounded in-memory counters suitable as Cloud Run defense in depth."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, str, int], int] = {}

    def consume(
        self,
        *,
        rule_name: str,
        client_key: str,
        limit: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        current_time = time.time() if now is None else now
        window = int(current_time // 60)
        counter_key = (rule_name, client_key, window)
        count = self._counters.get(counter_key, 0) + 1
        self._counters[counter_key] = count
        if len(self._counters) > 10_000:
            self._counters = {
                key: value
                for key, value in self._counters.items()
                if key[2] >= window - 1
            }
        remaining = max(0, limit - count)
        retry_after = max(1, 60 - int(current_time % 60))
        return RateLimitDecision(
            allowed=count <= limit,
            limit=limit,
            remaining=remaining,
            retry_after_seconds=retry_after,
        )


def _client_key(request: Request) -> str:
    authorization = str(request.headers.get("Authorization") or "").strip()
    if authorization.lower().startswith("bearer "):
        return f"token:{hashlib.sha256(authorization.encode('utf-8')).hexdigest()[:24]}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        enabled: bool,
        rules: list[RateLimitRule],
        limiter: FixedWindowRateLimiter | None = None,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.rules = rules
        self.limiter = limiter or FixedWindowRateLimiter()

    def _matching_rule(self, request: Request) -> RateLimitRule | None:
        for rule in self.rules:
            if request.method == rule.method and rule.path_pattern.fullmatch(
                request.url.path
            ):
                return rule
        return None

    async def dispatch(self, request: Request, call_next):
        rule = self._matching_rule(request) if self.enabled else None
        if rule is None:
            return await call_next(request)

        decision = self.limiter.consume(
            rule_name=rule.name,
            client_key=_client_key(request),
            limit=rule.requests_per_minute,
        )
        headers = {
            "X-RateLimit-Limit": str(decision.limit),
            "X-RateLimit-Remaining": str(decision.remaining),
        }
        if not decision.allowed:
            headers["Retry-After"] = str(decision.retry_after_seconds)
            log_event(
                logging.getLogger("rayadee.security"),
                logging.WARNING,
                "rate_limit_exceeded",
                request_id=getattr(request.state, "request_id", None),
                method=request.method,
                path=request.url.path,
                limit=decision.limit,
                remaining=decision.remaining,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again shortly."},
                headers=headers,
            )

        response = await call_next(request)
        response.headers.update(headers)
        return response


def daily_report_rate_limit_rules(settings) -> list[RateLimitRule]:
    return [
        RateLimitRule.create(
            name="authentication",
            method="POST",
            path_pattern=(
                r"/api/v1/auth/"
                r"(?:line-login|admin-login|sign-up|access-request)"
            ),
            requests_per_minute=settings.rate_limit_auth_per_minute,
        ),
        RateLimitRule.create(
            name="daily_report_upload",
            method="POST",
            path_pattern=(
                r"/api/v1/daily-reports/me/submissions/[^/]+/media"
            ),
            requests_per_minute=settings.rate_limit_upload_per_minute,
        ),
        RateLimitRule.create(
            name="daily_report_question",
            method="POST",
            path_pattern=(
                r"/api/v1/daily-reports/customer/reports/[^/]+/questions"
            ),
            requests_per_minute=settings.rate_limit_question_per_minute,
        ),
        RateLimitRule.create(
            name="line_customer_webhook",
            method="POST",
            path_pattern=r"/api/v1/daily-reports/line/customer/webhook",
            requests_per_minute=settings.rate_limit_webhook_per_minute,
        ),
    ]
