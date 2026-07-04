# app/services/refresh_session.py

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from app.db.models.refresh_session import RefreshSession
from app.db.repositories.refresh_session import RefreshSessionRepository
from app.services.base import BaseService
from app.services.errors import (
    ExpiredRefreshTokenError,
    InvalidRefreshTokenError,
    RefreshReuseDetectedError,
    RevokedRefreshTokenError,
)
from app.services.token import TokenService


class RefreshSessionService(BaseService):
    repositories = {
        "refresh_session_repository": RefreshSessionRepository,
    }

    refresh_session_repository: RefreshSessionRepository

    def __init__(self, session) -> None:
        super().__init__(session)
        self.token_service = TokenService()

    @staticmethod
    def hash_refresh_token(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode()).hexdigest()

    @staticmethod
    def _parse_jti(jti: str) -> UUID:
        try:
            return UUID(jti)
        except ValueError as exc:
            raise InvalidRefreshTokenError from exc

    async def create_refresh_session(
        self,
        *,
        user_id: int,
        refresh_token: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> RefreshSession:
        claims = self.token_service.decode_refresh_token(refresh_token)

        return await self.refresh_session_repository.create(
            user_id=user_id,
            jti=self._parse_jti(claims.jti),
            token_hash=self.hash_refresh_token(refresh_token),
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.fromtimestamp(claims.exp, UTC),
            revoked_at=None,
        )

    async def get_session_by_refresh_token(
        self,
        refresh_token: str,
        *,
        for_update: bool = False,
        verify_exp: bool = True,
    ) -> RefreshSession | None:
        claims = self.token_service.decode_refresh_token(
            refresh_token,
            verify_exp=verify_exp,
        )
        return await self.refresh_session_repository.get_by_jti_and_token_hash(
            jti=self._parse_jti(claims.jti),
            token_hash=self.hash_refresh_token(refresh_token),
            for_update=for_update,
        )

    async def get_session_for_refresh(self, refresh_token: str) -> RefreshSession:
        session = await self.get_session_by_refresh_token(
            refresh_token,
            for_update=True,
        )

        if session is None:
            raise InvalidRefreshTokenError()

        if session.revoked_at is not None:
            if session.replaced_by_session_id is not None:
                raise RefreshReuseDetectedError()
            raise RevokedRefreshTokenError()

        if session.expires_at <= datetime.now(UTC):
            raise ExpiredRefreshTokenError()

        return session

    async def revoke_refresh_session(
        self,
        refresh_session: RefreshSession,
        *,
        replaced_by_session_id: int | None = None,
    ) -> RefreshSession:
        now = datetime.now(UTC)
        return await self.refresh_session_repository.update(
            refresh_session,
            revoked_at=refresh_session.revoked_at or now,
            last_used_at=now,
            replaced_by_session_id=(
                refresh_session.replaced_by_session_id or replaced_by_session_id
            ),
        )

    async def revoke_by_refresh_token(self, refresh_token: str) -> None:
        try:
            refresh_session = await self.get_session_by_refresh_token(
                refresh_token,
                for_update=True,
                verify_exp=False,
            )
        except InvalidRefreshTokenError:
            return

        if refresh_session is None or refresh_session.revoked_at is not None:
            return

        await self.revoke_refresh_session(refresh_session)
