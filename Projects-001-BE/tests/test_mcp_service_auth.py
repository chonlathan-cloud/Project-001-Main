from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps.service_auth import require_mcp_service
from app.core.config import Settings


def settings() -> Settings:
    return Settings(
        _env_file=None,
        APP_ENV="production",
        MCP_INTERNAL_ENABLED=True,
        MCP_BACKEND_AUDIENCE="https://backend.test",
        MCP_ALLOWED_SERVICE_ACCOUNTS=(
            "projects-001-mcp-demo@project001-489710.iam.gserviceaccount.com"
        ),
    )


def credentials() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="google-signed-id-token")


def test_exact_allowed_service_account_is_accepted() -> None:
    claims = {
        "iss": "https://accounts.google.com",
        "sub": "service-subject",
        "email": "projects-001-mcp-demo@project001-489710.iam.gserviceaccount.com",
        "email_verified": True,
    }
    with patch(
        "app.api.deps.service_auth.google_id_token.verify_oauth2_token",
        return_value=claims,
    ) as verifier:
        principal = asyncio.run(require_mcp_service(credentials(), settings()))

    assert principal.email == claims["email"]
    assert principal.audience == "https://backend.test"
    assert verifier.call_args.args[2] == "https://backend.test"


def test_other_service_account_is_denied() -> None:
    claims = {
        "iss": "https://accounts.google.com",
        "sub": "service-subject",
        "email": "backend-runtime@project001-489710.iam.gserviceaccount.com",
        "email_verified": True,
    }
    with patch(
        "app.api.deps.service_auth.google_id_token.verify_oauth2_token",
        return_value=claims,
    ):
        with pytest.raises(HTTPException) as error:
            asyncio.run(require_mcp_service(credentials(), settings()))

    assert error.value.status_code == 403


def test_disabled_internal_contract_is_unavailable_before_token_validation() -> None:
    disabled = settings().model_copy(update={"mcp_internal_enabled": False})
    with patch(
        "app.api.deps.service_auth.google_id_token.verify_oauth2_token"
    ) as verifier:
        with pytest.raises(HTTPException) as error:
            asyncio.run(require_mcp_service(credentials(), disabled))

    assert error.value.status_code == 503
    verifier.assert_not_called()
