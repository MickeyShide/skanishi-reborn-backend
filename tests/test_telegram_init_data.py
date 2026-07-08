"""
Tests for TelegramInitDataService – additional branches.

Covers (in addition to what test_auth_business.py already has):
- missing hash raises InvalidInitDataError
- missing auth_date raises InvalidInitDataError
- auth_date in the future raises InvalidInitDataError
- missing user field raises InvalidInitDataError
- user field with invalid JSON raises InvalidInitDataError
- user field missing 'id' raises InvalidInitDataError
- user field with non-integer 'id' raises InvalidInitDataError
- empty init_data string raises InvalidInitDataError
- valid init_data parses all user fields correctly
- custom lifetime_seconds allows longer-lived init data
"""

import hashlib
import hmac
import json
import time
from unittest import TestCase

from app.services.errors import ExpiredInitDataError, InvalidInitDataError, InvalidTelegramSignatureError
from app.services.init_data import TelegramInitDataService


BOT_TOKEN = "123456:test-bot-token"


def _sign(payload: dict[str, str]) -> dict[str, str]:
    """Return payload with a valid 'hash' added."""
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(payload.items()) if k != "hash"
    )
    secret_key = hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256,
    ).digest()
    payload["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return payload


def _encode_init_data(payload: dict[str, str]) -> str:
    return "&".join(f"{k}={v}" for k, v in payload.items())


def _build_valid_payload(
    *,
    auth_date: int | None = None,
    user: dict | None = None,
) -> str:
    raw_user = json.dumps(user or {"id": 777, "first_name": "Alice"}, separators=(",", ":"))
    payload = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAEAAAE",
        "user": raw_user,
    }
    _sign(payload)
    return _encode_init_data(payload)


class TelegramInitDataServiceEdgeCaseTests(TestCase):
    def setUp(self) -> None:
        self.service = TelegramInitDataService(bot_token=BOT_TOKEN)

    # ------------------------------------------------------------------ #
    # Empty / missing data
    # ------------------------------------------------------------------ #
    def test_empty_string_raises_invalid_init_data(self) -> None:
        with self.assertRaises(InvalidInitDataError):
            self.service.validate_and_parse("")

    def test_missing_hash_raises_invalid_init_data(self) -> None:
        # auth_date and user present but no hash
        init_data = "auth_date=1234567890&user=%7B%22id%22%3A777%7D"
        with self.assertRaises(InvalidInitDataError):
            self.service.validate_and_parse(init_data)

    def test_missing_auth_date_raises_invalid_init_data(self) -> None:
        # Construct manually without auth_date
        raw_user = json.dumps({"id": 777, "first_name": "X"}, separators=(",", ":"))
        payload = {"query_id": "Q", "user": raw_user}
        _sign(payload)
        init_data = _encode_init_data(payload)
        with self.assertRaises(InvalidInitDataError):
            self.service.validate_and_parse(init_data)

    def test_non_integer_auth_date_raises_invalid_init_data(self) -> None:
        raw_user = json.dumps({"id": 777}, separators=(",", ":"))
        payload = {"auth_date": "notanumber", "user": raw_user}
        _sign(payload)
        init_data = _encode_init_data(payload)
        with self.assertRaises(InvalidInitDataError):
            self.service.validate_and_parse(init_data)

    # ------------------------------------------------------------------ #
    # Lifetime validation
    # ------------------------------------------------------------------ #
    def test_auth_date_far_in_future_raises_invalid_init_data(self) -> None:
        future_ts = int(time.time()) + 120  # 2 minutes in the future
        init_data = _build_valid_payload(auth_date=future_ts)
        with self.assertRaises(InvalidInitDataError):
            self.service.validate_and_parse(init_data)

    def test_expired_auth_date_raises_expired_init_data(self) -> None:
        past_ts = int(time.time()) - 7200  # 2 hours ago
        init_data = _build_valid_payload(auth_date=past_ts)
        with self.assertRaises(ExpiredInitDataError):
            self.service.validate_and_parse(init_data)

    def test_custom_lifetime_allows_longer_lived_data(self) -> None:
        service = TelegramInitDataService(bot_token=BOT_TOKEN, lifetime_seconds=86400)
        past_ts = int(time.time()) - 7200  # 2 hours ago – OK within 24 h
        init_data = _build_valid_payload(auth_date=past_ts)
        # Should not raise
        result = service.validate_and_parse(init_data)
        self.assertEqual(result.user.tg_id, 777)

    # ------------------------------------------------------------------ #
    # User field validation
    # ------------------------------------------------------------------ #
    def test_missing_user_field_raises_invalid_init_data(self) -> None:
        payload = {"auth_date": str(int(time.time())), "query_id": "Q"}
        _sign(payload)
        init_data = _encode_init_data(payload)
        with self.assertRaises(InvalidInitDataError):
            self.service.validate_and_parse(init_data)

    def test_invalid_json_in_user_field_raises_invalid_init_data(self) -> None:
        payload = {
            "auth_date": str(int(time.time())),
            "user": "not-valid-json",
        }
        _sign(payload)
        init_data = _encode_init_data(payload)
        with self.assertRaises(InvalidInitDataError):
            self.service.validate_and_parse(init_data)

    def test_user_missing_id_raises_invalid_init_data(self) -> None:
        raw_user = json.dumps({"first_name": "Alice"}, separators=(",", ":"))
        payload = {"auth_date": str(int(time.time())), "user": raw_user}
        _sign(payload)
        init_data = _encode_init_data(payload)
        with self.assertRaises(InvalidInitDataError):
            self.service.validate_and_parse(init_data)

    def test_user_with_string_id_is_parsed_as_int(self) -> None:
        # Telegram sometimes sends id as a JSON number; test numeric str
        raw_user = json.dumps({"id": "777", "first_name": "Alice"}, separators=(",", ":"))
        payload = {"auth_date": str(int(time.time())), "user": raw_user}
        _sign(payload)
        init_data = _encode_init_data(payload)
        result = self.service.validate_and_parse(init_data)
        self.assertEqual(result.user.tg_id, 777)

    def test_user_with_non_numeric_id_raises_invalid_init_data(self) -> None:
        raw_user = json.dumps({"id": "not-a-number"}, separators=(",", ":"))
        payload = {"auth_date": str(int(time.time())), "user": raw_user}
        _sign(payload)
        init_data = _encode_init_data(payload)
        with self.assertRaises(InvalidInitDataError):
            self.service.validate_and_parse(init_data)

    # ------------------------------------------------------------------ #
    # Successful parse
    # ------------------------------------------------------------------ #
    def test_valid_init_data_maps_all_user_fields(self) -> None:
        user_data = {
            "id": 12345,
            "first_name": "Bob",
            "last_name": "Builder",
            "username": "bobbuilder",
            "language_code": "ru",
            "is_premium": True,
            "photo_url": "https://example.com/photo.jpg",
        }
        init_data = _build_valid_payload(user=user_data)
        result = self.service.validate_and_parse(init_data)

        self.assertEqual(result.user.tg_id, 12345)
        self.assertEqual(result.user.first_name, "Bob")
        self.assertEqual(result.user.last_name, "Builder")
        self.assertEqual(result.user.username, "bobbuilder")
        self.assertEqual(result.user.language_code, "ru")
        self.assertTrue(result.user.is_premium)
        self.assertEqual(result.user.photo_url, "https://example.com/photo.jpg")

    def test_valid_init_data_captures_query_id(self) -> None:
        raw_user = json.dumps({"id": 777}, separators=(",", ":"))
        payload = {
            "auth_date": str(int(time.time())),
            "query_id": "MY-QUERY-ID",
            "user": raw_user,
        }
        _sign(payload)
        init_data = _encode_init_data(payload)
        result = self.service.validate_and_parse(init_data)
        self.assertEqual(result.query_id, "MY-QUERY-ID")

    def test_tampered_data_raises_invalid_signature(self) -> None:
        init_data = _build_valid_payload() + "&extra=tamper"
        with self.assertRaises(InvalidTelegramSignatureError):
            self.service.validate_and_parse(init_data)
