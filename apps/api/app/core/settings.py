# Core settings for HireLoop

import os
import re
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "HireLoop"
    API_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Direct database URL override (e.g. from Neon, Supabase, Render, Railway)
    RAW_DATABASE_URL: Optional[str] = Field(default=None, alias="DATABASE_URL")
    RAW_DATABASE_URL_UNPOOLED: Optional[str] = Field(default=None, alias="DATABASE_URL_UNPOOLED")
    NEON_BRANCH: Optional[str] = Field(default=None, alias="NEON_BRANCH")
    NEON_BRANCH_ID: Optional[str] = Field(default=None, alias="NEON_BRANCH_ID")
    RAW_REDIS_URL: Optional[str] = Field(default=None, alias="REDIS_URL")

    # Individual connection parameters fallback
    POSTGRES_HOST: str = Field(default="db", alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, alias="POSTGRES_PORT")
    POSTGRES_DB: str = Field(default="hireloop", alias="POSTGRES_DB")
    POSTGRES_USER: str = Field(default="postgres", alias="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="postgres", alias="POSTGRES_PASSWORD")

    # Redis connection parameters fallback
    REDIS_HOST: str = Field(default="redis", alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, alias="REDIS_PORT")

    # JWT Security
    JWT_SECRET_KEY: str = Field(default="hireloop-production-secret-key-change-me", alias="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM API keys (Optional - fallback to deterministic heuristics if unset)
    ANTHROPIC_API_KEY: str = Field(default="", alias="ANTHROPIC_API_KEY")
    OPENAI_API_KEY: str = Field(default="", alias="OPENAI_API_KEY")

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Async connection URL (postgresql+asyncpg://) for FastAPI endpoints."""
        if self.RAW_DATABASE_URL:
            raw = self.RAW_DATABASE_URL.strip()
            parsed = urlparse(raw)
            query_params = parse_qs(parsed.query)
            # Remove libpq-only parameters not recognized by asyncpg
            query_params.pop("channel_binding", None)
            if "sslmode" in query_params:
                query_params["ssl"] = query_params.pop("sslmode")
            clean_query = urlencode(query_params, doseq=True)
            return urlunparse((
                "postgresql+asyncpg",
                parsed.netloc,
                parsed.path,
                parsed.params,
                clean_query,
                parsed.fragment
            ))

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def DATABASE_SYNC_URL(self) -> str:
        """Synchronous connection URL (postgresql+psycopg://) for workers & migrations."""
        target_raw = self.RAW_DATABASE_URL_UNPOOLED or self.RAW_DATABASE_URL
        if target_raw:
            raw = target_raw.strip()
            if raw.startswith("postgres://"):
                raw = "postgresql+psycopg://" + raw[len("postgres://"):]
            elif raw.startswith("postgresql://"):
                raw = "postgresql+psycopg://" + raw[len("postgresql://"):]
            return raw

        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:
        if self.RAW_REDIS_URL:
            return self.RAW_REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @computed_field
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        if self.RAW_REDIS_URL:
            return self.RAW_REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"

settings = Settings()
