# app/services/token.py

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from pydantic import ValidationError

from app.config import settings
from app.db.models.user import User
from app.schemas.auth import AccessTokenClaims, RefreshTokenClaims
from app.services.errors import (
    ExpiredAccessTokenError,
    ExpiredRefreshTokenError,
    InvalidAccessTokenError,
    InvalidRefreshTokenError,
)


class TokenService:
    def __init__(
        self,
        session: object | None = None,
        *,
        secret_key: str | None = None,
        algorithm: str | None = None,
        access_ttl_minutes: int | None = None,
        refresh_ttl_days: int | None = None,
    ) -> None:
        self.session = session
        self.secret_key = secret_key or settings.SECRET_KEY
        self.algorithm = algorithm or settings.JWT_ALGORITHM
        self.access_ttl_seconds = (
            settings.ACCESS_TOKEN_TTL_SECONDS
            if access_ttl_minutes is None
            else access_ttl_minutes * 60
        )
        self.refresh_ttl_seconds = (
            settings.REFRESH_TOKEN_TTL_SECONDS
            if refresh_ttl_days is None
            else refresh_ttl_days * 86400
        )

    def create_access_token(self, user: User) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": str(user.id),
            "id": user.id,
            "tg_id": user.tg_id,
            "role": user.role.value if hasattr(user.role, "value") else user.role,
            "token_type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=self.access_ttl_seconds),
        }

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def create_refresh_token(self, user: User) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": str(user.id),
            "id": user.id,
            "jti": str(uuid4()),
            "token_type": "refresh",
            "iat": now,
            "exp": now + timedelta(seconds=self.refresh_ttl_seconds),
        }

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def _decode_token(
        self,
        token: str,
        *,
        verify_exp: bool = True,
    ) -> dict[str, Any]:
        return jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
            options={"verify_exp": verify_exp},
        )

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        try:
            payload = self._decode_token(token)
            return AccessTokenClaims.model_validate(payload)
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredAccessTokenError from exc
        except (jwt.InvalidTokenError, ValidationError) as exc:
            raise InvalidAccessTokenError from exc

    def decode_refresh_token(
        self,
        token: str,
        *,
        verify_exp: bool = True,
    ) -> RefreshTokenClaims:
        try:
            payload = self._decode_token(token, verify_exp=verify_exp)
            return RefreshTokenClaims.model_validate(payload)
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredRefreshTokenError from exc
        except (jwt.InvalidTokenError, ValidationError) as exc:
            raise InvalidRefreshTokenError from exc
