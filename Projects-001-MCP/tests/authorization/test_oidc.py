from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.oidc import OidcJwtTokenVerifier
from tests.fakes import make_settings


@pytest.fixture
def rsa_keys() -> tuple[object, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def issue_token(private_key: object, **overrides: object) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "iss": "https://issuer.test",
        "sub": "oauth-user-001",
        "aud": "https://testserver/mcp",
        "client_id": "codex-client",
        "scope": "mcp:read projects:read",
        "resource": "https://testserver/mcp",
        "app_env": "production",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256")


async def test_valid_resource_bound_token_is_accepted(rsa_keys: tuple[object, object]) -> None:
    private_key, public_key = rsa_keys
    verifier = OidcJwtTokenVerifier(
        make_settings(),
        signing_key_resolver=lambda _token: public_key,
    )
    token = await verifier.verify_token(issue_token(private_key))
    assert token is not None
    assert token.subject == "oauth-user-001"
    assert token.resource == "https://testserver/mcp"
    assert token.scopes == ["mcp:read", "projects:read"]


@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("iss", "https://wrong-issuer.test"),
        ("aud", "https://beta.testserver"),
        ("resource", "https://beta.testserver"),
        ("app_env", "prod-beta"),
        ("client_id", ""),
    ],
)
async def test_wrong_token_binding_is_rejected(
    rsa_keys: tuple[object, object],
    claim: str,
    value: str,
) -> None:
    private_key, public_key = rsa_keys
    verifier = OidcJwtTokenVerifier(
        make_settings(),
        signing_key_resolver=lambda _token: public_key,
    )
    assert await verifier.verify_token(issue_token(private_key, **{claim: value})) is None


async def test_expired_token_is_rejected(rsa_keys: tuple[object, object]) -> None:
    private_key, public_key = rsa_keys
    expired = int((datetime.now(UTC) - timedelta(minutes=2)).timestamp())
    verifier = OidcJwtTokenVerifier(
        make_settings(),
        signing_key_resolver=lambda _token: public_key,
    )
    assert await verifier.verify_token(issue_token(private_key, exp=expired)) is None


async def test_missing_environment_claim_is_rejected(rsa_keys: tuple[object, object]) -> None:
    private_key, public_key = rsa_keys
    now = datetime.now(UTC)
    claims = {
        "iss": "https://issuer.test",
        "sub": "oauth-user-001",
        "aud": "https://testserver/mcp",
        "client_id": "codex-client",
        "scope": "mcp:read",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    encoded = jwt.encode(claims, private_key, algorithm="RS256")
    verifier = OidcJwtTokenVerifier(
        make_settings(),
        signing_key_resolver=lambda _token: public_key,
    )
    assert await verifier.verify_token(encoded) is None
