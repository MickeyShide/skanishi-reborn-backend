# app/services/telegram_init_data.py

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from app.services.errors import (
    ExpiredInitDataError,
    InvalidInitDataError,
    InvalidTelegramSignatureError,
)


@dataclass(slots=True, frozen=True)
class TelegramUserData:
    tg_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None
    photo_url: str | None = None


@dataclass(slots=True, frozen=True)
class TelegramInitData:
    auth_date: int
    query_id: str | None
    user: TelegramUserData
    raw_hash: str


class TelegramInitDataService:
    def __init__(self, *, bot_token: str, lifetime_seconds: int = 3600) -> None:
        self.bot_token = bot_token
        self.lifetime_seconds = lifetime_seconds

    def validate_and_parse(self, init_data: str) -> TelegramInitData:
        pairs = self._parse_init_data(init_data)

        received_hash = pairs.get("hash")
        if not received_hash:
            raise InvalidInitDataError()

        self._verify_signature(
            pairs=pairs,
            received_hash=received_hash,
        )

        auth_date = self._get_auth_date(pairs)
        self._verify_lifetime(auth_date)

        user = self._get_user(pairs)

        return TelegramInitData(
            auth_date=auth_date,
            query_id=pairs.get("query_id"),
            user=user,
            raw_hash=received_hash,
        )

    def _parse_init_data(self, init_data: str) -> dict[str, str]:
        try:
            pairs = dict(
                parse_qsl(
                    init_data,
                    keep_blank_values=True,
                    strict_parsing=True,
                )
            )
        except ValueError as exc:
            raise InvalidInitDataError() from exc

        if not pairs:
            raise InvalidInitDataError()

        return pairs

    def _verify_signature(self, *, pairs: dict[str, str], received_hash: str) -> None:
        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(pairs.items()) if key != "hash"
        )

        secret_key = hmac.new(
            key=b"WebAppData",
            msg=self.bot_token.encode(),
            digestmod=hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            raise InvalidTelegramSignatureError()

    def _get_auth_date(self, pairs: dict[str, str]) -> int:
        raw_auth_date = pairs.get("auth_date")

        if raw_auth_date is None:
            raise InvalidInitDataError()

        try:
            return int(raw_auth_date)
        except ValueError as exc:
            raise InvalidInitDataError() from exc

    def _verify_lifetime(self, auth_date: int) -> None:
        now = int(time.time())

        if now - auth_date > self.lifetime_seconds:
            raise ExpiredInitDataError()

        # На случай мусорной даты из будущего.
        if auth_date > now + 60:
            raise InvalidInitDataError()

    def _get_user(self, pairs: dict[str, str]) -> TelegramUserData:
        raw_user = pairs.get("user")

        if raw_user is None:
            raise InvalidInitDataError()

        try:
            user_data: dict[str, Any] = json.loads(raw_user)
        except json.JSONDecodeError as exc:
            raise InvalidInitDataError() from exc

        tg_id = user_data.get("id")
        if tg_id is None:
            raise InvalidInitDataError()

        try:
            tg_id = int(tg_id)
        except ValueError as exc:
            raise InvalidInitDataError() from exc

        return TelegramUserData(
            tg_id=tg_id,
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            username=user_data.get("username"),
            language_code=user_data.get("language_code"),
            is_premium=user_data.get("is_premium"),
            photo_url=user_data.get("photo_url"),
        )
