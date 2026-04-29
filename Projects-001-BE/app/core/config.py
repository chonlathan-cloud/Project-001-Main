"""
Application settings loaded from the backend .env file.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list, alias="CORS_ORIGINS")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/project-001",
        alias="DATABASE_URL",
    )

    gcp_project_id: str | None = Field(default=None, alias="GCP_PROJECT_ID")
    gcp_location: str = Field(default="asia-southeast1", alias="GCP_LOCATION")
    firebase_project_id: str | None = Field(default=None, alias="FIREBASE_PROJECT_ID")
    google_application_credentials: str | None = Field(
        default=None,
        alias="GOOGLE_APPLICATION_CREDENTIALS",
    )

    firebase_web_api_key: str | None = Field(default=None, alias="FIREBASE_WEB_API_KEY")
    firebase_auth_emulator_host: str | None = Field(
        default=None,
        alias="FIREBASE_AUTH_EMULATOR_HOST",
    )
    firebase_storage_bucket: str | None = Field(default=None, alias="FIREBASE_STORAGE_BUCKET")

    line_channel_id: str | None = Field(default=None, alias="LINE_CHANNEL_ID")
    line_channel_secret: str | None = Field(default=None, alias="LINE_CHANNEL_SECRET")
    line_liff_id: str | None = Field(default=None, alias="LINE_LIFF_ID")
    line_redirect_uri: str | None = Field(default=None, alias="LINE_REDIRECT_URI")

    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=480, alias="JWT_EXPIRE_MINUTES")

    gcs_bucket_name: str | None = Field(default=None, alias="GCS_BUCKET_NAME")
    gcs_kyc_prefix: str = Field(default="kyc_id_cards", alias="GCS_KYC_PREFIX")
    gcs_temp_bills_prefix: str = Field(default="temp_bills", alias="GCS_TEMP_BILLS_PREFIX")
    gcs_perm_bills_prefix: str = Field(default="perm_bills", alias="GCS_PERM_BILLS_PREFIX")
    signed_url_expires_minutes: int = Field(default=15, alias="SIGNED_URL_EXPIRES_MINUTES")

    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    embedding_model: str = Field(default="text-embedding-004", alias="EMBEDDING_MODEL")
    boq_batch_sync_max_tabs: int = Field(default=3, alias="BOQ_BATCH_SYNC_MAX_TABS")

    admin_email_domain: str | None = Field(default=None, alias="ADMIN_EMAIL_DOMAIN")
    admin_emails: Annotated[list[str], NoDecode] = Field(default_factory=list, alias="ADMIN_EMAILS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @field_validator("admin_emails", mode="before")
    @classmethod
    def _parse_admin_emails(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip().lower() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return []

    @field_validator("admin_email_domain", mode="before")
    @classmethod
    def _normalize_admin_domain(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        if not cleaned:
            return None
        if "@" in cleaned:
            return cleaned.split("@", 1)[1]
        return cleaned

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
