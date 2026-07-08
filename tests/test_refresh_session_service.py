"""
Tests for RefreshSessionService session lifecycle logic.

Covers:
- hash_refresh_token: determinism
- create_refresh_session: decodes token and persists
- get_session_for_refresh: happy path, not found, revoked, reuse, expired
- revoke_refresh_session: marks revoked, sets replaced_by_session_id
- revoke_by_refresh_token: ignores malformed tokens, revokes valid ones, skips already-revoked
"""

import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

import jwt

from app.services.errors import (
    ExpiredRefreshTokenError,
    InvalidRefreshTokenError,
    RefreshReuseDetectedError,
    RevokedRefreshTokenError,
)
from app.services.refresh_session import RefreshSessionService
from app.services.token import TokenService


def _make_service() -> RefreshSessionService:
    service = object.__new__(RefreshSessionService)
    service.token_service = TokenService(
        secret_key="a" * 32,
        algorithm="HS256",
        access_ttl_minutes=5,
        refresh_ttl_days=7,
    )
    service.refresh_session_repository = MagicMock()
    return service


def _make_refresh_token(*, user_id: int = 1, exp_offset_seconds: int = 3600) -> str:
    service = TokenService(
        secret_key="a" * 32,
        algorithm="HS256",
        access_ttl_minutes=5,
        refresh_ttl_days=1,
    )
    user = SimpleNamespace(id=user_id, tg_id=123, role=SimpleNamespace(value="USER"))
    # Manually encode with offset for expired token tests
    now = int(time.time())
    from uuid import uuid4
    payload = {
        "sub": str(user_id),
        "id": user_id,
        "jti": str(uuid4()),
        "token_type": "refresh",
        "iat": now,
        "exp": now + exp_offset_seconds,
    }
    return jwt.encode(payload, "a" * 32, algorithm="HS256")


class HashRefreshTokenTests(IsolatedAsyncioTestCase):
    def test_hash_is_deterministic(self) -> None:
        token = "some-refresh-token"
        hash1 = RefreshSessionService.hash_refresh_token(token)
        hash2 = RefreshSessionService.hash_refresh_token(token)
        self.assertEqual(hash1, hash2)

    def test_different_tokens_produce_different_hashes(self) -> None:
        hash1 = RefreshSessionService.hash_refresh_token("token-a")
        hash2 = RefreshSessionService.hash_refresh_token("token-b")
        self.assertNotEqual(hash1, hash2)

    def test_hash_is_64_hex_characters(self) -> None:
        result = RefreshSessionService.hash_refresh_token("any-token")
        self.assertEqual(len(result), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result))


class CreateRefreshSessionTests(IsolatedAsyncioTestCase):
    async def test_create_session_decodes_token_and_delegates_to_repository(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=5)
        created_session = SimpleNamespace(id=10)
        service.refresh_session_repository.create = AsyncMock(return_value=created_session)

        result = await service.create_refresh_session(
            user_id=5,
            refresh_token=token,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )

        self.assertIs(result, created_session)
        call_kwargs = service.refresh_session_repository.create.await_args.kwargs
        self.assertEqual(call_kwargs["user_id"], 5)
        self.assertEqual(call_kwargs["user_agent"], "Mozilla/5.0")
        self.assertEqual(call_kwargs["ip_address"], "192.168.1.1")
        self.assertIsNotNone(call_kwargs["jti"])
        self.assertIsNotNone(call_kwargs["token_hash"])
        self.assertIsNone(call_kwargs["revoked_at"])

    async def test_create_session_accepts_none_user_agent_and_ip(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=5)
        service.refresh_session_repository.create = AsyncMock(return_value=SimpleNamespace(id=1))

        await service.create_refresh_session(
            user_id=5,
            refresh_token=token,
            user_agent=None,
            ip_address=None,
        )

        call_kwargs = service.refresh_session_repository.create.await_args.kwargs
        self.assertIsNone(call_kwargs["user_agent"])
        self.assertIsNone(call_kwargs["ip_address"])


class GetSessionForRefreshTests(IsolatedAsyncioTestCase):
    async def test_valid_session_is_returned(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=1)
        future_expires_at = datetime.now(UTC) + timedelta(days=1)
        session = SimpleNamespace(
            revoked_at=None,
            replaced_by_session_id=None,
            expires_at=future_expires_at,
        )
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=session
        )

        result = await service.get_session_for_refresh(token)

        self.assertIs(result, session)

    async def test_not_found_session_raises_invalid_refresh_token(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=1)
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=None
        )

        with self.assertRaises(InvalidRefreshTokenError):
            await service.get_session_for_refresh(token)

    async def test_revoked_session_with_replacement_raises_reuse_detected(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=1)
        future_expires_at = datetime.now(UTC) + timedelta(days=1)
        session = SimpleNamespace(
            revoked_at=datetime.now(UTC),  # revoked
            replaced_by_session_id=999,   # has a replacement (reuse attack)
            expires_at=future_expires_at,
        )
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=session
        )

        with self.assertRaises(RefreshReuseDetectedError):
            await service.get_session_for_refresh(token)

    async def test_revoked_session_without_replacement_raises_revoked_error(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=1)
        future_expires_at = datetime.now(UTC) + timedelta(days=1)
        session = SimpleNamespace(
            revoked_at=datetime.now(UTC),
            replaced_by_session_id=None,
            expires_at=future_expires_at,
        )
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=session
        )

        with self.assertRaises(RevokedRefreshTokenError):
            await service.get_session_for_refresh(token)

    async def test_expired_session_raises_expired_error(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=1)
        past_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session = SimpleNamespace(
            revoked_at=None,
            replaced_by_session_id=None,
            expires_at=past_expires_at,
        )
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=session
        )

        with self.assertRaises(ExpiredRefreshTokenError):
            await service.get_session_for_refresh(token)


class RevokeRefreshSessionTests(IsolatedAsyncioTestCase):
    async def test_revoke_sets_revoked_at_and_replaced_by(self) -> None:
        service = _make_service()
        session = SimpleNamespace(
            revoked_at=None,
            last_used_at=None,
            replaced_by_session_id=None,
        )
        updated = SimpleNamespace(id=1, revoked_at=datetime.now(UTC))
        service.refresh_session_repository.update = AsyncMock(return_value=updated)

        result = await service.revoke_refresh_session(session, replaced_by_session_id=42)

        self.assertIs(result, updated)
        call_kwargs = service.refresh_session_repository.update.await_args.kwargs
        self.assertIsNotNone(call_kwargs["revoked_at"])
        self.assertEqual(call_kwargs["replaced_by_session_id"], 42)

    async def test_revoke_does_not_overwrite_existing_revoked_at(self) -> None:
        service = _make_service()
        original_revoked_at = datetime(2026, 1, 1, tzinfo=UTC)
        session = SimpleNamespace(
            revoked_at=original_revoked_at,
            replaced_by_session_id=None,
        )
        service.refresh_session_repository.update = AsyncMock(
            return_value=SimpleNamespace(id=1)
        )

        await service.revoke_refresh_session(session)

        call_kwargs = service.refresh_session_repository.update.await_args.kwargs
        self.assertEqual(call_kwargs["revoked_at"], original_revoked_at)

    async def test_revoke_without_replacement_sets_none(self) -> None:
        service = _make_service()
        session = SimpleNamespace(revoked_at=None, replaced_by_session_id=None)
        service.refresh_session_repository.update = AsyncMock(return_value=SimpleNamespace())

        await service.revoke_refresh_session(session)

        call_kwargs = service.refresh_session_repository.update.await_args.kwargs
        self.assertIsNone(call_kwargs["replaced_by_session_id"])


class RevokeByRefreshTokenTests(IsolatedAsyncioTestCase):
    async def test_revokes_valid_active_session(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=1)
        session = SimpleNamespace(revoked_at=None, replaced_by_session_id=None)
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=session
        )
        service.refresh_session_repository.update = AsyncMock(return_value=session)

        await service.revoke_by_refresh_token(token)

        service.refresh_session_repository.update.assert_awaited_once()

    async def test_skips_already_revoked_session(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=1)
        session = SimpleNamespace(revoked_at=datetime.now(UTC), replaced_by_session_id=None)
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=session
        )
        service.refresh_session_repository.update = AsyncMock()

        await service.revoke_by_refresh_token(token)

        service.refresh_session_repository.update.assert_not_awaited()

    async def test_ignores_none_session(self) -> None:
        service = _make_service()
        token = _make_refresh_token(user_id=1)
        service.refresh_session_repository.get_by_jti_and_token_hash = AsyncMock(
            return_value=None
        )
        service.refresh_session_repository.update = AsyncMock()

        await service.revoke_by_refresh_token(token)

        service.refresh_session_repository.update.assert_not_awaited()

    async def test_ignores_invalid_token_format(self) -> None:
        service = _make_service()
        service.refresh_session_repository.update = AsyncMock()

        # A garbage string should not raise – just silently ignore
        await service.revoke_by_refresh_token("totally.invalid.jwt")

        service.refresh_session_repository.update.assert_not_awaited()
