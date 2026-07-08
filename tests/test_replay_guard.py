"""
Tests for InitDataReplayGuardService.

Covers:
- First use of a given init_data hash sets the Redis key and does NOT raise.
- Second use (key already set → SET NX returns False/None) raises InitDataReplayError.
- Redis unavailability triggers fail-open: the guard silently passes (default=True).
"""

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.errors import InitDataReplayError
from app.services.init_data_replay_guard import InitDataReplayGuardService


class InitDataReplayGuardServiceTests(IsolatedAsyncioTestCase):
    def _make_service(self) -> InitDataReplayGuardService:
        redis = MagicMock()
        redis.set = AsyncMock()
        return InitDataReplayGuardService(redis, ttl_seconds=3600)

    async def test_first_use_does_not_raise(self) -> None:
        service = self._make_service()

        # redis.set NX returns 1 (key was freshly set) → True-ish
        async def fake_redis_fail_open(operation, default=None):
            return await operation()

        service.redis.set = AsyncMock(return_value=True)

        with patch(
            "app.services.init_data_replay_guard.redis_fail_open",
            fake_redis_fail_open,
        ):
            # Should not raise
            await service.ensure_not_replayed("unique-init-data-string")

    async def test_second_use_raises_replay_error(self) -> None:
        service = self._make_service()

        # redis.set NX returns None (key already existed) → replay detected
        async def fake_redis_fail_open(operation, default=None):
            return await operation()

        service.redis.set = AsyncMock(return_value=None)

        with patch(
            "app.services.init_data_replay_guard.redis_fail_open",
            fake_redis_fail_open,
        ):
            with self.assertRaises(InitDataReplayError):
                await service.ensure_not_replayed("replayed-init-data-string")

    async def test_redis_failure_triggers_fail_open_and_does_not_raise(self) -> None:
        """
        When Redis is unavailable, redis_fail_open returns the default value (True).
        Because was_set=True, the guard must NOT raise — it fails open.
        """
        service = self._make_service()

        # Simulate redis_fail_open returning default=True (fail-open behaviour)
        async def fake_redis_fail_open(operation, default=None):
            return default  # simulates Redis being down

        with patch(
            "app.services.init_data_replay_guard.redis_fail_open",
            fake_redis_fail_open,
        ):
            # Should not raise – fail-open means we let the request through
            await service.ensure_not_replayed("any-init-data")

    async def test_hash_is_based_on_init_data_content(self) -> None:
        """
        The Redis key for two different init_data strings must differ so that
        one does not accidentally block the other.
        """
        keys_used: list[str] = []

        async def capture_redis_set(*, name: str, value, ex, nx):
            keys_used.append(name)
            return True

        service = self._make_service()
        service.redis.set = capture_redis_set  # type: ignore[method-assign]

        async def fake_redis_fail_open(operation, default=None):
            return await operation()

        with patch(
            "app.services.init_data_replay_guard.redis_fail_open",
            fake_redis_fail_open,
        ):
            await service.ensure_not_replayed("init-data-A")
            await service.ensure_not_replayed("init-data-B")

        self.assertEqual(len(keys_used), 2)
        self.assertNotEqual(keys_used[0], keys_used[1])
