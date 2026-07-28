"""OAuth JWT resource-server verification for the Product MCP."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.config.settings import Settings

SigningKeyResolver = Callable[[str], Any]


class OidcJwtTokenVerifier(TokenVerifier):
    """Validate issuer/resource-bound asymmetric JWT access tokens.

    Product role and permission claims are deliberately not interpreted here.
    Authorization is resolved from the Product Backend on every tool call.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        signing_key_resolver: SigningKeyResolver | None = None,
    ) -> None:
        self._settings = settings
        jwks_client = PyJWKClient(str(settings.oauth_jwks_url))
        self._signing_key_resolver = signing_key_resolver or (
            lambda token: jwks_client.get_signing_key_from_jwt(token).key
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or len(token) > 16384:
            return None
        try:
            signing_key = await asyncio.to_thread(self._signing_key_resolver, token)
            claims = jwt.decode(
                token,
                key=signing_key,
                algorithms=self._settings.oauth_algorithms,
                audience=self._settings.oauth_audience,
                issuer=self._settings.canonical_issuer,
                leeway=30,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
            if not self._valid_environment(claims):
                return None
            if not self._valid_resource(claims):
                return None

            subject = str(claims.get("sub") or "").strip()
            client_id = str(claims.get("client_id") or claims.get("azp") or "").strip()
            if not subject or not client_id:
                return None

            scopes = self._extract_scopes(claims)
            safe_claims = {
                key: claims[key]
                for key in (
                    "iss",
                    "sub",
                    "aud",
                    "azp",
                    "client_id",
                    "scope",
                    "scp",
                    "resource",
                    self._settings.oauth_environment_claim,
                    "client_channel",
                )
                if key in claims
            }
            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=scopes,
                expires_at=int(claims["exp"]),
                resource=self._settings.canonical_resource_url,
                subject=subject,
                claims=safe_claims,
            )
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            return None
        except Exception:
            # JWKS/network/provider failures are authentication failures at the
            # resource boundary. Details remain in operational telemetry only.
            return None

    def _valid_environment(self, claims: dict[str, Any]) -> bool:
        actual = claims.get(self._settings.oauth_environment_claim)
        if actual is None:
            return not self._settings.require_environment_claim
        return str(actual).strip() == self._settings.app_env

    def _valid_resource(self, claims: dict[str, Any]) -> bool:
        resource = claims.get("resource")
        if resource is None:
            return True
        accepted = (
            {str(item).rstrip("/") for item in resource}
            if isinstance(resource, list)
            else {str(resource).rstrip("/")}
        )
        return self._settings.canonical_resource_url in accepted

    @staticmethod
    def _extract_scopes(claims: dict[str, Any]) -> list[str]:
        values: list[str] = []
        raw_scope = claims.get("scope")
        if isinstance(raw_scope, str):
            values.extend(raw_scope.split())
        raw_scp = claims.get("scp")
        if isinstance(raw_scp, str):
            values.extend(raw_scp.split())
        elif isinstance(raw_scp, list):
            values.extend(str(item) for item in raw_scp)
        return list(dict.fromkeys(item.strip() for item in values if item.strip()))

