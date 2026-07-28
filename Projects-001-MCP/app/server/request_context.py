"""Request correlation without persisting request contents."""

from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_request_id: ContextVar[str] = ContextVar("mcp_request_id", default="")


def current_request_id() -> str:
    value = _request_id.get()
    return value or uuid4().hex


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        requested = headers.get(b"x-request-id", b"").decode("ascii", errors="ignore").strip()
        request_id = requested[:128] if requested else uuid4().hex
        token = _request_id.set(request_id)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self._app(scope, receive, send_with_request_id)
        finally:
            _request_id.reset(token)

