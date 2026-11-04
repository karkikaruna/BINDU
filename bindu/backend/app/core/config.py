from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False, populate_by_name=True)

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "BINDU"
    api_v1_prefix: str = "/api/v1"

    # "meta" = Meta Muse Spark via the Meta Model API (default). "mock" = clearly labelled offline demo/test provider.
    ai_provider: Literal["mock", "meta"] = "meta"
    # Meta's own docs/SDKs call this MODEL_API_KEY; META_API_KEY is accepted too.
    meta_api_key: str = Field(default="", validation_alias=AliasChoices("META_API_KEY", "MODEL_API_KEY"))
    meta_api_base_url: str = "https://api.meta.ai/v1"
    # "muse-spark-1.3" = Standard mode (your prompts are not used for training).
    # "muse-spark-1.3-contributor" is cheaper but Meta may train on prompts/photos, so it is never the default.
    meta_model_name: str = "muse-spark-1.3"
    meta_structured_output: bool = True
    # Muse Spark always reasons, and reasoning tokens count against the output cap. Keep effort low for snappy answers
    # and the cap generous so the visible JSON is never cut off. Set META_REASONING_EFFORT= (empty) to omit the field.
    meta_reasoning_effort: Literal["", "minimal", "low", "medium", "high", "xhigh", "max"] = "low"
    meta_max_output_tokens: int = Field(default=8000, ge=500, le=64000)
    ai_request_timeout_seconds: float = Field(default=60, gt=0, le=300)

    # Swar: Nepali-focused text-to-speech (Naamche-Labs/swar), served by the FastAPI wrapper from voice.ipynb.
    # Leave swar_base_url empty to disable server-side TTS (the app then falls back to the pre-recorded audio_url).
    swar_base_url: str = ""
    swar_api_key: str = ""
    swar_voice_id: str = ""  # a preset (e.g. "maya") or an id returned by POST /voices on the Swar server
    swar_quality: Literal["fast", "best"] = "fast"
    swar_timeout_seconds: float = Field(default=120, gt=0, le=900)  # first call loads the models, so be generous
    tts_max_chars: int = Field(default=300, ge=1, le=600)  # Swar itself rejects > 600
    tts_cache_dir: str = "/tmp/bindu_tts_cache"

    auth_mode: Literal["supabase", "dev"] = "supabase"
    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    # Server-only. Used solely to delete an account on the user's own request. Never ship it in the app.
    supabase_service_role_key: str = ""

    cors_origins: str = "http://localhost:8081"
    max_upload_size_mb: int = Field(default=10, ge=1, le=50)
    ai_rate_limit_per_minute: int = Field(default=10, ge=1)
    # GET /tts is called once per tapped answer option (cached on disk after the first synthesis), so it gets its own, higher budget.
    tts_rate_limit_per_minute: int = Field(default=60, ge=1)

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
