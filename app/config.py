"""Application configuration."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Stock Agent Platform"
    environment: str = "local"
    log_level: str = "INFO"
    api_key: str | None = None

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/stock_agent"
    auto_create_schema: bool = False

    rate_limit_per_minute: int = Field(default=30, ge=1, le=10_000)
    analysis_cache_ttl_seconds: int = Field(default=900, ge=0, le=86_400)
    job_lease_seconds: int = Field(default=1800, ge=60, le=86_400)

    market_data_period: str = "5y"
    benchmark_ticker: str = "SPY"

    enable_crewai_default: bool = True
    openai_api_key: str | None = None
    crewai_model: str = "openai/gpt-4.1-mini"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Accept Render Postgres URLs and convert them for SQLAlchemy asyncio."""
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        return value

    @property
    def crewai_enabled(self) -> bool:
        """Return whether CrewAI can be used for narrative synthesis."""
        return self.enable_crewai_default and bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
