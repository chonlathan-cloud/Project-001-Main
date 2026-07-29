"""Validated, environment-locked Product MCP configuration."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    DEMO = "demo"
    BETA = "beta"


class EnvironmentProfile:
    def __init__(
        self,
        *,
        app_env: str,
        service_name: str,
        backend_service_name: str,
        cloud_sql_instance: str,
        firestore_database_id: str,
        buckets: set[str],
    ) -> None:
        self.app_env = app_env
        self.service_name = service_name
        self.backend_service_name = backend_service_name
        self.cloud_sql_instance = cloud_sql_instance
        self.firestore_database_id = firestore_database_id
        self.buckets = frozenset(buckets)


ENVIRONMENT_PROFILES = {
    Environment.DEMO: EnvironmentProfile(
        app_env="production",
        service_name="projects-001-mcp",
        backend_service_name="projects-001-be",
        cloud_sql_instance="project001-489710:asia-southeast1:project-001",
        firestore_database_id="(default)",
        buckets={
            "kyc_id_cards",
            "temp_bills",
            "perm_bills",
            "project001-489710-work-inspection",
            "project001-489710-daily-reports-demo",
        },
    ),
    Environment.BETA: EnvironmentProfile(
        app_env="prod-beta",
        service_name="projects-001-mcp-beta",
        backend_service_name="projects-001-be-beta",
        cloud_sql_instance="project001-489710:asia-southeast1:project-001-beta",
        firestore_database_id="prod-beta",
        buckets={
            "kyc_id_cards-beta",
            "temp_bills-beta",
            "perm_bills-beta",
            "project001-489710-work-inspection-beta",
            "project001-489710-daily-reports-beta",
        },
    ),
}

FORBIDDEN_RESOURCE_FRAGMENTS = (
    "project-001-saas",
    "project-001-saas-restore-test",
    "project-saas-001-be",
    "project-saas-001-fe",
    "bigquery",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )

    environment: Environment = Field(alias="MCP_ENVIRONMENT")
    app_env: str = Field(alias="MCP_APP_ENV")
    gcp_project_id: str = Field(alias="MCP_GCP_PROJECT_ID")
    gcp_region: str = Field(alias="MCP_GCP_REGION")
    service_name: str = Field(alias="MCP_SERVICE_NAME")
    resource_url: AnyHttpUrl = Field(alias="MCP_RESOURCE_URL")

    oauth_issuer: AnyHttpUrl = Field(alias="MCP_OAUTH_ISSUER")
    oauth_audience: str = Field(alias="MCP_OAUTH_AUDIENCE")
    oauth_jwks_url: AnyHttpUrl = Field(alias="MCP_OAUTH_JWKS_URL")
    oauth_algorithms: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["RS256"],
        alias="MCP_OAUTH_ALGORITHMS",
    )
    oauth_required_scopes: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["mcp:read"],
        alias="MCP_OAUTH_REQUIRED_SCOPES",
    )
    oauth_environment_claim: str = Field(
        default="app_env",
        alias="MCP_OAUTH_ENVIRONMENT_CLAIM",
    )
    require_environment_claim: bool = Field(
        default=True,
        alias="MCP_REQUIRE_ENVIRONMENT_CLAIM",
    )

    backend_url: AnyHttpUrl = Field(alias="MCP_BACKEND_URL")
    backend_service_name: str = Field(alias="MCP_BACKEND_SERVICE_NAME")
    backend_audience: str = Field(alias="MCP_BACKEND_AUDIENCE")
    backend_access_context_path: str = Field(
        default="/api/v1/internal/mcp/access-context:resolve",
        alias="MCP_BACKEND_ACCESS_CONTEXT_PATH",
    )
    backend_timeout_seconds: float = Field(
        default=5.0,
        ge=0.5,
        le=30.0,
        alias="MCP_BACKEND_TIMEOUT_SECONDS",
    )
    rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        alias="MCP_RATE_LIMIT_PER_MINUTE",
    )

    cloud_sql_instance: str = Field(alias="MCP_CLOUD_SQL_INSTANCE")
    firestore_database_id: str = Field(alias="MCP_FIRESTORE_DATABASE_ID")
    allowed_buckets: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        alias="MCP_ALLOWED_BUCKETS",
    )
    audit_log_name: str = Field(alias="MCP_AUDIT_LOG_NAME")
    operational_log_name: str = Field(alias="MCP_OPERATIONAL_LOG_NAME")
    log_level: str = Field(default="INFO", alias="MCP_LOG_LEVEL")

    @field_validator(
        "oauth_algorithms",
        "oauth_required_scopes",
        "allowed_buckets",
        mode="before",
    )
    @classmethod
    def parse_csv(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @field_validator("oauth_algorithms")
    @classmethod
    def validate_algorithms(cls, value: list[str]) -> list[str]:
        allowed = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
        if not value or any(item not in allowed for item in value):
            raise ValueError("OAuth algorithms must use an approved asymmetric algorithm.")
        return value

    @field_validator("oauth_required_scopes")
    @classmethod
    def validate_scopes(cls, value: list[str]) -> list[str]:
        if "mcp:read" not in value:
            raise ValueError("MCP OAuth scopes must include mcp:read.")
        return list(dict.fromkeys(value))

    @field_validator("backend_access_context_path")
    @classmethod
    def validate_backend_path(cls, value: str) -> str:
        if not value.startswith("/api/v1/internal/mcp/") or ".." in value:
            raise ValueError("Backend access-context path must be an internal MCP v1 path.")
        return value

    @model_validator(mode="after")
    def validate_environment_lock(self) -> Settings:
        profile = ENVIRONMENT_PROFILES[self.environment]
        expected = {
            "MCP_APP_ENV": (self.app_env, profile.app_env),
            "MCP_GCP_PROJECT_ID": (self.gcp_project_id, "project001-489710"),
            "MCP_GCP_REGION": (self.gcp_region, "asia-southeast1"),
            "MCP_SERVICE_NAME": (self.service_name, profile.service_name),
            "MCP_BACKEND_SERVICE_NAME": (
                self.backend_service_name,
                profile.backend_service_name,
            ),
            "MCP_CLOUD_SQL_INSTANCE": (
                self.cloud_sql_instance,
                profile.cloud_sql_instance,
            ),
            "MCP_FIRESTORE_DATABASE_ID": (
                self.firestore_database_id,
                profile.firestore_database_id,
            ),
        }
        mismatches = [name for name, (actual, wanted) in expected.items() if actual != wanted]
        if mismatches:
            raise ValueError("Environment mapping mismatch: " + ", ".join(mismatches))

        if frozenset(self.allowed_buckets) != profile.buckets:
            raise ValueError("MCP_ALLOWED_BUCKETS must exactly match the environment allowlist.")

        resource = str(self.resource_url).rstrip("/")
        parsed_resource = urlparse(resource)
        if (
            parsed_resource.path.rstrip("/") != "/mcp"
            or parsed_resource.query
            or parsed_resource.fragment
            or parsed_resource.username
            or parsed_resource.password
        ):
            raise ValueError("The canonical MCP resource URL must end with /mcp.")
        if self.oauth_audience.rstrip("/") != resource:
            raise ValueError("OAuth audience must equal the canonical MCP resource URL.")
        if self.backend_audience.rstrip("/") != str(self.backend_url).rstrip("/"):
            raise ValueError("Backend audience must equal the configured Backend URL.")

        https_fields = {
            "MCP_RESOURCE_URL": resource,
            "MCP_OAUTH_ISSUER": str(self.oauth_issuer),
            "MCP_OAUTH_JWKS_URL": str(self.oauth_jwks_url),
            "MCP_BACKEND_URL": str(self.backend_url),
        }
        invalid_https = [
            name for name, value in https_fields.items() if urlparse(value).scheme != "https"
        ]
        if invalid_https:
            raise ValueError("HTTPS is required for: " + ", ".join(invalid_https))

        all_values = " ".join(
            [
                self.service_name,
                self.backend_service_name,
                self.cloud_sql_instance,
                self.firestore_database_id,
                *self.allowed_buckets,
            ]
        ).lower()
        if any(fragment in all_values for fragment in FORBIDDEN_RESOURCE_FRAGMENTS):
            raise ValueError("Configuration references an explicitly excluded resource.")
        return self

    @property
    def canonical_resource_url(self) -> str:
        return str(self.resource_url).rstrip("/")

    @property
    def canonical_issuer(self) -> str:
        # OAuth issuer identifiers are exact values. In particular, providers
        # such as Auth0 publish an issuer ending in "/" and sign access tokens
        # with that exact value, so normalizing the trailing slash would make
        # otherwise valid tokens fail issuer validation.
        return str(self.oauth_issuer)

    @property
    def canonical_backend_url(self) -> str:
        return str(self.backend_url).rstrip("/")

    @property
    def allowed_host_patterns(self) -> list[str]:
        host = urlparse(self.canonical_resource_url).netloc
        hostname = urlparse(self.canonical_resource_url).hostname or host
        return list(dict.fromkeys([host, hostname]))

    @property
    def allowed_origins(self) -> list[str]:
        parsed = urlparse(self.canonical_resource_url)
        return [f"{parsed.scheme}://{parsed.netloc}"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
