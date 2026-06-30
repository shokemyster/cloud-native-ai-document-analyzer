"""Environment-backed application settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated configuration shared by API process components."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    app_name: str = "AI Document Analyzer API"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=10, ge=0)
    database_pool_timeout_seconds: int = Field(default=30, ge=1)

    redis_url: str = "redis://localhost:6379/0"
    celery_queue_name: str = Field(default="documents", min_length=1)
    celery_broker_connection_timeout_seconds: int = Field(default=5, ge=1)
    celery_visibility_timeout_seconds: int = Field(default=3600, ge=60)
    celery_task_soft_time_limit_seconds: int = Field(default=270, ge=1)
    celery_task_time_limit_seconds: int = Field(default=300, ge=1)

    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
        repr=False,
    )
    openai_analysis_instructions: SecretStr | None = Field(
        default=None,
        validation_alias="OPENAI_ANALYSIS_INSTRUCTIONS",
        repr=False,
    )
    ai_model: str = Field(default="gpt-5.5", min_length=1)
    ai_max_input_characters: int = Field(default=80_000, ge=1)
    ai_max_output_tokens: int = Field(default=600, ge=1)
    openai_timeout_seconds: int = Field(default=60, ge=1)
    openai_max_retries: int = Field(default=2, ge=0, le=5)

    upload_directory: Path = Path("data/uploads")
    max_upload_size_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    allowed_upload_extensions: tuple[str, ...] = (".pdf", ".csv")
    allowed_upload_media_types: tuple[str, ...] = (
        "application/pdf",
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
    )

    cors_origins: tuple[str, ...] = ("http://localhost:5173",)

    @model_validator(mode="after")
    def validate_task_time_limits(self) -> Self:
        if (
            self.celery_task_soft_time_limit_seconds
            >= self.celery_task_time_limit_seconds
        ):
            raise ValueError("Celery hard time limit must exceed soft time limit")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""

    return Settings()  # type: ignore[call-arg]
