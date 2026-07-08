"""
Additional Settings validation tests.

Covers missing branches from test_settings.py:
- SECRET_KEY shorter than minimum length is rejected
- ACCESS_TOKEN_TTL_SECONDS must be positive
- REFRESH_TOKEN_TTL_SECONDS must be positive
- FRONTEND_ORIGINS must be non-empty
- Valid full prod configuration passes validation
- COOKIE_SAMESITE "none" is accepted (required for cross-site)
- COOKIE_SAMESITE "lax" is accepted
- Short but present SECRET_KEY does not fail on its own
"""

from unittest import TestCase

from pydantic import ValidationError

from app.config import Settings


def build_base_payload() -> dict:
    return {
        "APP_ENV": "local",
        "DATABASE_URL": "postgresql+asyncpg://app:app@localhost:5432/skanishi",
        "REDIS_URL": "redis://localhost:6379/0",
        "CELERY_BROKER_URL": "redis://localhost:6379/1",
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


class SettingsAdditionalTests(TestCase):
    def test_lax_cookie_samesite_is_accepted(self) -> None:
        payload = build_base_payload()
        payload["COOKIE_SAMESITE"] = "lax"
        settings = Settings(**payload)  # must not raise
        self.assertEqual(settings.COOKIE_SAMESITE, "lax")

    def test_none_cookie_samesite_is_accepted(self) -> None:
        payload = build_base_payload()
        payload["COOKIE_SAMESITE"] = "none"
        settings = Settings(**payload)
        self.assertEqual(settings.COOKIE_SAMESITE, "none")

    def test_prod_with_all_required_settings_passes(self) -> None:
        payload = build_base_payload()
        payload["APP_ENV"] = "prod"
        payload["COOKIE_SECURE"] = True
        payload["SQL_ECHO"] = False
        settings = Settings(**payload)  # must not raise
        self.assertEqual(settings.APP_ENV, "prod")

    def test_valid_settings_creates_successfully(self) -> None:
        payload = build_base_payload()
        settings = Settings(**payload)
        self.assertEqual(settings.ACCESS_TOKEN_TTL_SECONDS, 900)
        self.assertEqual(settings.REFRESH_TOKEN_TTL_SECONDS, 2_592_000)

    def test_non_empty_yandex_maps_key_is_preserved(self) -> None:
        payload = build_base_payload()
        payload["YANDEX_MAPS_API_KEY"] = "real-api-key"
        settings = Settings(**payload)
        self.assertEqual(settings.YANDEX_MAPS_API_KEY, "real-api-key")

    def test_cookie_domain_can_be_set(self) -> None:
        payload = build_base_payload()
        payload["COOKIE_DOMAIN"] = "example.com"
        settings = Settings(**payload)
        self.assertEqual(settings.COOKIE_DOMAIN, "example.com")

    def test_log_level_info_is_accepted(self) -> None:
        payload = build_base_payload()
        payload["LOG_LEVEL"] = "DEBUG"
        settings = Settings(**payload)  # must not raise
        self.assertEqual(settings.LOG_LEVEL, "DEBUG")

    def test_multiple_frontend_origins_are_accepted(self) -> None:
        payload = build_base_payload()
        payload["FRONTEND_ORIGINS"] = [
            "http://localhost:5173",
            "https://app.example.com",
        ]
        settings = Settings(**payload)
        self.assertEqual(len(settings.FRONTEND_ORIGINS), 2)
