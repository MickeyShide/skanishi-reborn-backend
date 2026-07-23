import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.services.errors import (
    ExpiredInitDataError,
    InvalidInitDataError,
    InvalidTelegramSignatureError,
)
from app.services.init_data import TelegramInitDataService


def generate_test_init_data(bot_token: str, auth_date: int, user_id: int = 12345) -> str:
    user_data = {
        "id": user_id,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "language_code": "en",
        "is_premium": True,
    }
    
    pairs = {
        "query_id": "AAHdF6IQAAAAAN0XohD-test",
        "user": json.dumps(user_data, separators=(",", ":")),
        "auth_date": str(auth_date),
    }

    # Telegram algorithm
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(pairs.items())
    )

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode(),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=data_check_string.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    pairs["hash"] = calculated_hash
    return urlencode(pairs)


class TestTelegramInitDataService:
    def setup_method(self) -> None:
        self.bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        self.service = TelegramInitDataService(bot_token=self.bot_token)

    def test_validate_and_parse_success(self) -> None:
        now = int(time.time())
        init_data = generate_test_init_data(self.bot_token, auth_date=now)
        
        result = self.service.validate_and_parse(init_data)
        
        assert result.auth_date == now
        assert result.user.tg_id == 12345
        assert result.user.username == "testuser"
        assert result.user.is_premium is True

    def test_validate_invalid_signature(self) -> None:
        now = int(time.time())
        # Use a wrong bot token to sign, but validate with the correct one
        init_data = generate_test_init_data("wrong_token:123", auth_date=now)
        
        with pytest.raises(InvalidTelegramSignatureError):
            self.service.validate_and_parse(init_data)

    def test_validate_expired_auth_date(self) -> None:
        # Generate data that is 2 hours old
        old_time = int(time.time()) - 7200
        init_data = generate_test_init_data(self.bot_token, auth_date=old_time)
        
        with pytest.raises(ExpiredInitDataError):
            self.service.validate_and_parse(init_data)

    def test_validate_missing_hash(self) -> None:
        with pytest.raises(InvalidInitDataError):
            self.service.validate_and_parse("query_id=123&auth_date=123456")

    def test_validate_malformed_string(self) -> None:
        with pytest.raises(InvalidInitDataError):
            self.service.validate_and_parse("")
