"""Service-authenticated Backend policy client.

The external MCP bearer token is never accepted by this module and therefore
cannot be passed through to the Product Backend.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.config.settings import Settings
from app.policy.models import AccessContext


class PolicyUnavailable(RuntimeError):
    pass


class PolicyClient(Protocol):
    async def resolve_access(
        self,
        *,
        subject: str,
        issuer: str,
        client_id: str,
        request_id: str,
    ) -> AccessContext: ...


class ServiceIdentityTokenProvider(Protocol):
    async def get_token(self, audience: str) -> str: ...


class CloudRunIdentityTokenProvider:
    """Fetch and briefly cache a Cloud Run ID token from the metadata server."""

    METADATA_URL = (
        "http://metadata.google.internal/computeMetadata/v1/instance/"
        "service-accounts/default/identity"
    )

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at = 0
        self._lock = asyncio.Lock()

    async def get_token(self, audience: str) -> str:
        now = int(time.time())
        if self._token and self._expires_at - now > 60:
            return self._token
        async with self._lock:
            now = int(time.time())
            if self._token and self._expires_at - now > 60:
                return self._token
            try:
                async with httpx.AsyncClient(timeout=3.0, follow_redirects=False) as client:
                    response = await client.get(
                        self.METADATA_URL,
                        params={"audience": audience, "format": "full"},
                        headers={"Metadata-Flavor": "Google"},
                    )
                response.raise_for_status()
                token = response.text.strip()
                expires_at = self._unverified_expiry(token)
            except Exception as exc:
                raise PolicyUnavailable("Backend service identity is unavailable.") from exc
            self._token = token
            self._expires_at = expires_at
            return token

    @staticmethod
    def _unverified_expiry(token: str) -> int:
        try:
            payload_segment = token.split(".", 2)[1]
            padding = "=" * (-len(payload_segment) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_segment + padding))
            return int(payload["exp"])
        except Exception as exc:
            raise PolicyUnavailable("Metadata server returned an invalid identity token.") from exc


class BackendEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["success"] = "success"
    data: AccessContext


class BackendPolicyClient:
    def __init__(
        self,
        settings: Settings,
        *,
        token_provider: ServiceIdentityTokenProvider | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._token_provider = token_provider or CloudRunIdentityTokenProvider()
        self._transport = transport

    async def resolve_access(
        self,
        *,
        subject: str,
        issuer: str,
        client_id: str,
        request_id: str,
    ) -> AccessContext:
        try:
            service_token = await self._token_provider.get_token(self._settings.backend_audience)
            async with httpx.AsyncClient(
                base_url=self._settings.canonical_backend_url,
                timeout=self._settings.backend_timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    self._settings.backend_access_context_path,
                    headers={
                        "Authorization": f"Bearer {service_token}",
                        "X-Request-ID": request_id,
                        "X-MCP-Contract-Version": "1.0",
                    },
                    json={
                        "contract_version": "1.0",
                        "subject": subject,
                        "issuer": issuer,
                        "client_id": client_id,
                        "environment": self._settings.environment.value,
                    },
                )
            if response.status_code != 200:
                raise PolicyUnavailable("Backend authorization resolution failed.")
            access = BackendEnvelope.model_validate(response.json()).data
        except (httpx.HTTPError, ValidationError, ValueError, TypeError) as exc:
            raise PolicyUnavailable("Backend authorization resolution failed.") from exc

        if (
            access.subject != subject
            or access.issuer.rstrip("/") != issuer.rstrip("/")
            or access.client_id != client_id
            or access.environment != self._settings.environment
        ):
            raise PolicyUnavailable("Backend returned a mismatched authorization context.")
        return access
