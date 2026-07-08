"""
Tests for UserService and the XP/level-up business logic.

Covers:
- get_next_level_xp boundary values
- add_xp_and_check_level_up: normal, level threshold, multi-level-up, zero XP
- create_from_telegram: field mapping
- update_telegram_fields: field mapping
- get_or_create_from_telegram: create-new and update-existing paths
- update_privacy: delegation to repository
"""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock

from app.services.init_data import TelegramUserData
from app.services.user import LEVEL_THRESHOLDS, UserService, get_next_level_xp


class GetNextLevelXpTests(TestCase):
    def test_known_levels_return_table_values(self) -> None:
        for level, expected_xp in LEVEL_THRESHOLDS.items():
            self.assertEqual(get_next_level_xp(level), expected_xp)

    def test_level_zero_is_handled_by_formula(self) -> None:
        # Level 0 is not in the table – formula fallback must not raise
        result = get_next_level_xp(0)
        self.assertIsInstance(result, int)

    def test_level_beyond_table_uses_formula(self) -> None:
        # Level 11 must not be in the static table
        self.assertNotIn(11, LEVEL_THRESHOLDS)
        result = get_next_level_xp(11)
        self.assertIsInstance(result, int)
        # Formula is level * 15000 + 1000
        self.assertEqual(result, 11 * 15000 + 1000)

    def test_high_level_formula_grows_linearly(self) -> None:
        xp_100 = get_next_level_xp(100)
        xp_101 = get_next_level_xp(101)
        self.assertGreater(xp_101, xp_100)


class AddXpAndCheckLevelUpTests(IsolatedAsyncioTestCase):
    def _make_service(self) -> UserService:
        service = object.__new__(UserService)
        service.user_repository = MagicMock()
        service.user_repository.update = AsyncMock(
            side_effect=lambda user, **kwargs: SimpleNamespace(
                id=user.id,
                xp=kwargs.get("xp", user.xp),
                level=kwargs.get("level", user.level),
                next_level_xp=kwargs.get("next_level_xp", user.next_level_xp),
                level_progress=kwargs.get("level_progress", user.level_progress),
            )
        )
        return service

    def _make_user(
        self,
        *,
        xp: int = 0,
        level: int = 1,
        next_level_xp: int | None = None,
        level_progress: int = 0,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            id=42,
            xp=xp,
            level=level,
            next_level_xp=next_level_xp or get_next_level_xp(level),
            level_progress=level_progress,
        )

    async def test_adding_zero_xp_does_not_change_level(self) -> None:
        service = self._make_service()
        user = self._make_user(xp=500, level=1, next_level_xp=1000)

        updated = await service.add_xp_and_check_level_up(user, 0)

        self.assertEqual(updated.xp, 500)
        self.assertEqual(updated.level, 1)

    async def test_adding_xp_below_threshold_keeps_same_level(self) -> None:
        service = self._make_service()
        user = self._make_user(xp=0, level=1, next_level_xp=1000)

        updated = await service.add_xp_and_check_level_up(user, 500)

        self.assertEqual(updated.xp, 500)
        self.assertEqual(updated.level, 1)
        self.assertEqual(updated.next_level_xp, 1000)

    async def test_reaching_exact_threshold_triggers_level_up(self) -> None:
        service = self._make_service()
        user = self._make_user(xp=0, level=1, next_level_xp=1000)

        updated = await service.add_xp_and_check_level_up(user, 1000)

        self.assertEqual(updated.level, 2)
        self.assertEqual(updated.xp, 1000)

    async def test_exceeding_multiple_thresholds_levels_up_repeatedly(self) -> None:
        service = self._make_service()
        # Start at level 1 (threshold=1000), add enough to blow through level 2 (2500) too
        user = self._make_user(xp=0, level=1, next_level_xp=1000)

        # 2500 XP should at minimum push past level 1→2→3
        updated = await service.add_xp_and_check_level_up(user, 3000)

        self.assertGreater(updated.level, 1)

    async def test_level_progress_is_clamped_to_100(self) -> None:
        service = self._make_service()
        user = self._make_user(xp=0, level=1, next_level_xp=1)

        # With next_level_xp=1 and xp=999, progress would be > 100 if unclamped
        updated = await service.add_xp_and_check_level_up(user, 999)

        self.assertLessEqual(updated.level_progress, 100)

    async def test_level_progress_reflects_proportion(self) -> None:
        service = self._make_service()
        # next_level_xp at level 1 is 1000 in the table
        user = self._make_user(xp=0, level=1, next_level_xp=1000)

        updated = await service.add_xp_and_check_level_up(user, 500)

        # 500/1000 = 50%
        self.assertEqual(updated.level_progress, 50)


class UserServiceTelegramTests(IsolatedAsyncioTestCase):
    def _make_service(self) -> UserService:
        service = object.__new__(UserService)
        service.user_repository = MagicMock()
        return service

    def _telegram_user(
        self,
        *,
        tg_id: int = 123,
        first_name: str = "Alice",
        last_name: str | None = "Smith",
        username: str | None = "alice",
        is_premium: bool = False,
        photo_url: str | None = None,
    ) -> TelegramUserData:
        return TelegramUserData(
            tg_id=tg_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code="en",
            is_premium=is_premium,
            photo_url=photo_url,
        )

    async def test_create_from_telegram_sets_all_fields(self) -> None:
        service = self._make_service()
        created_user = SimpleNamespace(id=1)
        service.user_repository.create = AsyncMock(return_value=created_user)

        tg_user = self._telegram_user(
            tg_id=999,
            first_name="Bob",
            last_name="Marley",
            username="bob_m",
            is_premium=True,
            photo_url="https://cdn.example.com/photo.jpg",
        )

        result = await service.create_from_telegram(tg_user)

        self.assertIs(result, created_user)
        call_kwargs = service.user_repository.create.await_args.kwargs
        self.assertEqual(call_kwargs["tg_id"], 999)
        self.assertEqual(call_kwargs["first_name"], "Bob")
        self.assertEqual(call_kwargs["last_name"], "Marley")
        self.assertEqual(call_kwargs["username"], "bob_m")
        self.assertTrue(call_kwargs["is_premium"])
        self.assertEqual(call_kwargs["photo_url"], "https://cdn.example.com/photo.jpg")
        self.assertTrue(call_kwargs["is_private"])  # defaults to private
        self.assertIn("next_level_xp", call_kwargs)

    async def test_create_from_telegram_treats_none_is_premium_as_false(self) -> None:
        service = self._make_service()
        service.user_repository.create = AsyncMock(return_value=SimpleNamespace(id=1))

        tg_user = TelegramUserData(tg_id=1, first_name="X", is_premium=None)
        await service.create_from_telegram(tg_user)

        call_kwargs = service.user_repository.create.await_args.kwargs
        self.assertFalse(call_kwargs["is_premium"])

    async def test_update_telegram_fields_passes_all_expected_fields(self) -> None:
        service = self._make_service()
        existing_user = SimpleNamespace(id=1)
        updated_user = SimpleNamespace(id=1)
        service.user_repository.update = AsyncMock(return_value=updated_user)

        tg_user = self._telegram_user(
            first_name="Carol",
            last_name="Danvers",
            username="captaincarol",
            is_premium=True,
        )

        result = await service.update_telegram_fields(existing_user, tg_user)

        self.assertIs(result, updated_user)
        call_kwargs = service.user_repository.update.await_args.kwargs
        self.assertEqual(call_kwargs["first_name"], "Carol")
        self.assertEqual(call_kwargs["last_name"], "Danvers")
        self.assertEqual(call_kwargs["username"], "captaincarol")
        self.assertTrue(call_kwargs["is_premium"])

    async def test_get_or_create_creates_user_when_not_found(self) -> None:
        service = self._make_service()
        new_user = SimpleNamespace(id=99)
        service.user_repository.get_one_or_none = AsyncMock(return_value=None)
        service.user_repository.create = AsyncMock(return_value=new_user)
        service.user_repository.update = AsyncMock()

        tg_user = self._telegram_user(tg_id=999)
        result = await service.get_or_create_from_telegram(tg_user)

        self.assertIs(result, new_user)
        service.user_repository.create.assert_awaited_once()
        service.user_repository.update.assert_not_awaited()

    async def test_get_or_create_updates_user_when_found(self) -> None:
        service = self._make_service()
        existing_user = SimpleNamespace(id=77)
        updated_user = SimpleNamespace(id=77)
        service.user_repository.get_one_or_none = AsyncMock(return_value=existing_user)
        service.user_repository.update = AsyncMock(return_value=updated_user)
        service.user_repository.create = AsyncMock()

        tg_user = self._telegram_user(tg_id=777)
        result = await service.get_or_create_from_telegram(tg_user)

        self.assertIs(result, updated_user)
        service.user_repository.create.assert_not_awaited()
        service.user_repository.update.assert_awaited_once()

    async def test_update_privacy_delegates_to_repository(self) -> None:
        service = self._make_service()
        user = SimpleNamespace(id=5)
        updated = SimpleNamespace(id=5, is_private=False)
        service.user_repository.update = AsyncMock(return_value=updated)

        result = await service.update_privacy(user, is_private=False)

        self.assertFalse(result.is_private)
        call_kwargs = service.user_repository.update.await_args.kwargs
        self.assertFalse(call_kwargs["is_private"])
