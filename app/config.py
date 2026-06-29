import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    PROD = "prod"


class Settings(BaseSettings):
    APP_ENV: Environment

    DATABASE_URL: PostgresDsn

    REDIS_URL: RedisDsn

    SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_TTL_SECONDS: int
    REFRESH_TOKEN_TTL_SECONDS: int

    BOT_TOKEN: str

    FRONTEND_ORIGINS: Annotated[list[str], NoDecode]

    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool
    COOKIE_SAMESITE: Literal["strict", "lax", "none"]

    SQL_ECHO: bool

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )

    @field_validator("FRONTEND_ORIGINS", mode="before")
    @classmethod
    def parse_frontend_origins(cls, value: object) -> object:
        if isinstance(value, str):
            raw_value = value.strip()
            if raw_value.startswith("["):
                return json.loads(raw_value)
            return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

        return value

    @field_validator("COOKIE_DOMAIN", mode="before")
    @classmethod
    def parse_cookie_domain(cls, value: object) -> object:
        if value == "":
            return None

        return value


settings = Settings()
