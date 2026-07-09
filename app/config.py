import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
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

    CELERY_BROKER_URL: str

    SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = Field(min_length=1)
    ACCESS_TOKEN_TTL_SECONDS: int = Field(gt=0)
    REFRESH_TOKEN_TTL_SECONDS: int = Field(gt=0)

    BOT_TOKEN: str = Field(min_length=1)
    YANDEX_MAPS_API_KEY: str | None = None
    ADMIN_SECRET_KEY: str | None = None

    FRONTEND_ORIGINS: Annotated[list[str], NoDecode]

    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool
    COOKIE_SAMESITE: Literal["lax", "none"]

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

    @field_validator("FRONTEND_ORIGINS")
    @classmethod
    def validate_frontend_origins(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("FRONTEND_ORIGINS must contain at least one origin.")

        return value

    @field_validator("COOKIE_DOMAIN", mode="before")
    @classmethod
    def parse_cookie_domain(cls, value: object) -> object:
        if value == "":
            return None

        return value

    @field_validator("YANDEX_MAPS_API_KEY", mode="before")
    @classmethod
    def parse_yandex_maps_api_key(cls, value: object) -> object:
        if value == "":
            return None

        return value

    @model_validator(mode="after")
    def validate_environment_rules(self) -> "Settings":
        if self.APP_ENV == Environment.PROD:
            if not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SECURE must be true in prod.")
            if self.SQL_ECHO:
                raise ValueError("SQL_ECHO must be false in prod.")

        return self


settings = Settings()
