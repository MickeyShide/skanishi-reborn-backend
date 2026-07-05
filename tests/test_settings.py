from unittest import TestCase

from pydantic import ValidationError

from app.config import Settings


def build_settings_payload() -> dict[str, object]:
    return {
        "APP_ENV": "local",
        "DATABASE_URL": "postgresql+asyncpg://app:app@localhost:5432/skanishi",
        "REDIS_URL": "redis://localhost:6379/0",
        "SECRET_KEY": "a" * 32,
        "JWT_ALGORITHM": "HS256",
        "ACCESS_TOKEN_TTL_SECONDS": 900,
        "REFRESH_TOKEN_TTL_SECONDS": 2_592_000,
        "BOT_TOKEN": "123456:replace-me",
        "YANDEX_MAPS_API_KEY": None,
        "FRONTEND_ORIGINS": ["http://localhost:5173"],
        "COOKIE_DOMAIN": None,
        "COOKIE_SECURE": False,
        "COOKIE_SAMESITE": "lax",
        "SQL_ECHO": False,
        "LOG_LEVEL": "INFO",
    }


class SettingsValidationTests(TestCase):
    def test_cookie_samesite_strict_is_rejected(self) -> None:
        payload = build_settings_payload()
        payload["COOKIE_SAMESITE"] = "strict"

        with self.assertRaises(ValidationError):
            Settings(**payload)

    def test_prod_requires_secure_cookie(self) -> None:
        payload = build_settings_payload()
        payload["APP_ENV"] = "prod"

        with self.assertRaises(ValidationError):
            Settings(**payload)

    def test_prod_rejects_sql_echo(self) -> None:
        payload = build_settings_payload()
        payload["APP_ENV"] = "prod"
        payload["COOKIE_SECURE"] = True
        payload["SQL_ECHO"] = True

        with self.assertRaises(ValidationError):
            Settings(**payload)

    def test_required_secrets_and_ttls_are_validated(self) -> None:
        payload = build_settings_payload()
        payload["BOT_TOKEN"] = ""

        with self.assertRaises(ValidationError):
            Settings(**payload)

    def test_empty_yandex_maps_api_key_is_normalized_to_none(self) -> None:
        payload = build_settings_payload()
        payload["YANDEX_MAPS_API_KEY"] = ""

        settings = Settings(**payload)

        self.assertIsNone(settings.YANDEX_MAPS_API_KEY)
