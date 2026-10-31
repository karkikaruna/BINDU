from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "BINDU"
    api_v1_prefix: str = "/api/v1"

    ai_provider: Literal["mock", "meta", "gemini"] = "meta"
    meta_api_key: str = ""
    meta_api_base_url: str = "https://api.meta.ai/v1"
    meta_model_name: str = "muse-spark-1.3"
    meta_structured_output: bool = True
    gemini_api_key: str = ""
    gemini_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_model_name: str = "gemini-2.5-flash"
    ai_request_timeout_seconds: float = Field(default=60, gt=0, le=300)

    auth_mode: Literal["supabase", "dev"] = "supabase"
    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    # Server-only. Used solely to delete an account on the user's own request. Never ship it in the app.
    supabase_service_role_key: str = ""

    cors_origins: str = "http://localhost:8081"
    max_upload_size_mb: int = Field(default=10, ge=1, le=50)
    ai_rate_limit_per_minute: int = Field(default=10, ge=1)

    @field_validator("auth_mode")
    @classmethod
    def _no_dev_auth_in_production(cls, v: str, info):  # noqa: ANN001
        if v == "dev" and info.data.get("app_env") == "production":
            raise ValueError("AUTH_MODE=dev is not allowed when APP_ENV=production")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
