from datetime import UTC, datetime, timedelta
import jwt
import pytest
from unittest.mock import MagicMock

from app.services.token import TokenService
from app.services.errors import (
    ExpiredAccessTokenError,
    ExpiredRefreshTokenError,
    InvalidAccessTokenError,
    InvalidRefreshTokenError,
)

class TestTokenService:
    def setup_method(self) -> None:
        self.secret_key = "test_super_secret"
        self.service = TokenService(secret_key=self.secret_key, algorithm="HS256")
        
        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.tg_id = 12345
        self.mock_user.role = "USER"

    def test_create_and_decode_access_token(self) -> None:
        token = self.service.create_access_token(self.mock_user)
        assert isinstance(token, str)

        claims = self.service.decode_access_token(token)
        assert claims.id == 1
        assert claims.tg_id == 12345
        assert claims.token_type == "access"

    def test_create_and_decode_refresh_token(self) -> None:
        token = self.service.create_refresh_token(self.mock_user)
        assert isinstance(token, str)

        claims = self.service.decode_refresh_token(token)
        assert claims.id == 1
        assert claims.token_type == "refresh"
        assert claims.jti is not None

    def test_expired_access_token(self) -> None:
        # Create a manually expired token
        payload = {
            "sub": "1",
            "id": 1,
            "tg_id": 12345,
            "role": "USER",
            "token_type": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) - timedelta(seconds=10),
        }
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        with pytest.raises(ExpiredAccessTokenError):
            self.service.decode_access_token(token)

    def test_expired_refresh_token(self) -> None:
        payload = {
            "sub": "1",
            "id": 1,
            "jti": "fake-jti",
            "token_type": "refresh",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) - timedelta(seconds=10),
        }
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        with pytest.raises(ExpiredRefreshTokenError):
            self.service.decode_refresh_token(token)

    def test_invalid_access_token(self) -> None:
        with pytest.raises(InvalidAccessTokenError):
            self.service.decode_access_token("not.a.real.jwt")

    def test_invalid_refresh_token(self) -> None:
        with pytest.raises(InvalidRefreshTokenError):
            self.service.decode_refresh_token("not.a.real.jwt")
