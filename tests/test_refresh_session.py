from datetime import UTC, datetime, timedelta
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.refresh_session import RefreshSessionService
from app.db.models.refresh_session import RefreshSession
from app.services.errors import (
    ExpiredRefreshTokenError,
    InvalidRefreshTokenError,
    RefreshReuseDetectedError,
    RevokedRefreshTokenError,
)

class TestRefreshSessionService(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.session_mock = AsyncMock()
        self.service = RefreshSessionService(session=self.session_mock)
        self.repo_mock = AsyncMock()
        self.service.refresh_session_repository = self.repo_mock
        self.service.token_service = MagicMock()

    async def test_get_session_for_refresh_success(self) -> None:
        mock_claims = MagicMock()
        mock_claims.jti = "123e4567-e89b-12d3-a456-426614174000"
        self.service.token_service.decode_refresh_token.return_value = mock_claims

        mock_session = RefreshSession(
            revoked_at=None,
            expires_at=datetime.now(UTC) + timedelta(hours=1)
        )
        self.repo_mock.get_by_jti_and_token_hash.return_value = mock_session

        result = await self.service.get_session_for_refresh("valid_token")
        self.assertEqual(result, mock_session)

    async def test_get_session_for_refresh_not_found(self) -> None:
        mock_claims = MagicMock()
        mock_claims.jti = "123e4567-e89b-12d3-a456-426614174000"
        self.service.token_service.decode_refresh_token.return_value = mock_claims

        self.repo_mock.get_by_jti_and_token_hash.return_value = None

        with pytest.raises(InvalidRefreshTokenError):
            await self.service.get_session_for_refresh("invalid_token")

    async def test_get_session_for_refresh_revoked(self) -> None:
        mock_claims = MagicMock()
        mock_claims.jti = "123e4567-e89b-12d3-a456-426614174000"
        self.service.token_service.decode_refresh_token.return_value = mock_claims

        mock_session = RefreshSession(
            revoked_at=datetime.now(UTC),
            replaced_by_session_id=None
        )
        self.repo_mock.get_by_jti_and_token_hash.return_value = mock_session

        with pytest.raises(RevokedRefreshTokenError):
            await self.service.get_session_for_refresh("revoked_token")

    async def test_get_session_for_refresh_reuse_detected(self) -> None:
        mock_claims = MagicMock()
        mock_claims.jti = "123e4567-e89b-12d3-a456-426614174000"
        self.service.token_service.decode_refresh_token.return_value = mock_claims

        mock_session = RefreshSession(
            revoked_at=datetime.now(UTC),
            replaced_by_session_id=999
        )
        self.repo_mock.get_by_jti_and_token_hash.return_value = mock_session

        with pytest.raises(RefreshReuseDetectedError):
            await self.service.get_session_for_refresh("reused_token")
