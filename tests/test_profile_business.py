from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.business.profile import (
    VALIDATION_COUNT_CACHE_TTL_SECONDS,
    ProfileBusinessService,
)


class ProfileBusinessServiceTests(IsolatedAsyncioTestCase):
    async def test_returns_cached_validation_count_on_cache_hit(self) -> None:
        service = object.__new__(ProfileBusinessService)
        service.get_current_user = AsyncMock(return_value=SimpleNamespace(id=77))
        service.validation_service = MagicMock()
        service.validation_service.count_user_validations = AsyncMock()

        redis_get = AsyncMock(return_value="12")
        redis_set = AsyncMock()

        async def fake_redis_fail_open(operation, default=None):
            return await operation()

        with (
            patch(
                "app.services.business.profile.redis_fail_open",
                fake_redis_fail_open,
            ),
            patch("app.services.business.profile.redis_client.get", redis_get),
            patch("app.services.business.profile.redis_client.set", redis_set),
        ):
            result = await ProfileBusinessService.get_validation_count(service)

        self.assertEqual(result.count, 12)
        self.assertEqual(
            service.validation_service.count_user_validations.await_count,
            0,
        )
        redis_get.assert_awaited_once_with("user:77:validation_count")
        self.assertEqual(redis_set.await_count, 0)

    async def test_reads_database_and_warms_cache_on_cache_miss(self) -> None:
        service = object.__new__(ProfileBusinessService)
        service.get_current_user = AsyncMock(return_value=SimpleNamespace(id=77))
        service.validation_service = MagicMock()
        service.validation_service.count_user_validations = AsyncMock(return_value=12)

        redis_get = AsyncMock(return_value=None)
        redis_set = AsyncMock(return_value=True)

        async def fake_redis_fail_open(operation, default=None):
            return await operation()

        with (
            patch(
                "app.services.business.profile.redis_fail_open",
                fake_redis_fail_open,
            ),
            patch("app.services.business.profile.redis_client.get", redis_get),
            patch("app.services.business.profile.redis_client.set", redis_set),
        ):
            result = await ProfileBusinessService.get_validation_count(service)

        self.assertEqual(result.count, 12)
        service.validation_service.count_user_validations.assert_awaited_once_with(
            user_id=77
        )
        redis_set.assert_awaited_once_with(
            name="user:77:validation_count",
            value="12",
            ex=VALIDATION_COUNT_CACHE_TTL_SECONDS,
        )

    async def test_falls_back_to_database_when_redis_is_unavailable(self) -> None:
        service = object.__new__(ProfileBusinessService)
        service.get_current_user = AsyncMock(return_value=SimpleNamespace(id=77))
        service.validation_service = MagicMock()
        service.validation_service.count_user_validations = AsyncMock(return_value=7)

        redis_fail_open = AsyncMock(side_effect=[None, None])

        with patch("app.services.business.profile.redis_fail_open", redis_fail_open):
            result = await ProfileBusinessService.get_validation_count(service)

        self.assertEqual(result.count, 7)
        service.validation_service.count_user_validations.assert_awaited_once_with(
            user_id=77
        )
