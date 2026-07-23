"""
Tests for StreakService.

Covers:
- get_streak_xp_multiplier logic
- record_login extending streak
- record_login resetting streak
- is_streak_active checking cutoff
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.streak import StreakService, get_streak_xp_multiplier


class StreakServiceTests(IsolatedAsyncioTestCase):
    def test_get_streak_xp_multiplier(self) -> None:
        self.assertEqual(get_streak_xp_multiplier(1), 1.0)
        self.assertEqual(get_streak_xp_multiplier(6), 1.0)
        self.assertEqual(get_streak_xp_multiplier(7), 1.5)
        self.assertEqual(get_streak_xp_multiplier(13), 1.5)
        self.assertEqual(get_streak_xp_multiplier(14), 2.0)
        self.assertEqual(get_streak_xp_multiplier(30), 2.5)
        self.assertEqual(get_streak_xp_multiplier(100), 2.5)

    async def test_record_login_same_day_no_change(self) -> None:
        session_mock = MagicMock()
        service = StreakService(session=session_mock)

        now = datetime.now(UTC)
        user = SimpleNamespace(last_login_at=now, streak_days=5, streak_last_date=now.date())

        updated = await service.record_login(user)

        self.assertEqual(updated.streak_days, 5)
        session_mock.add.assert_not_called()

    async def test_record_login_consecutive_day_extends_streak(self) -> None:
        session_mock = MagicMock()
        session_mock.flush = AsyncMock()
        session_mock.refresh = AsyncMock()
        service = StreakService(session=session_mock)

        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        user = SimpleNamespace(last_login_at=yesterday, streak_days=5, streak_last_date=yesterday.date())

        updated = await service.record_login(user)

        self.assertEqual(updated.streak_days, 6)
        self.assertEqual(updated.last_login_at.date(), now.date())
        self.assertEqual(updated.streak_last_date, now.date())
        session_mock.add.assert_called_once_with(updated)

    async def test_record_login_gap_resets_streak(self) -> None:
        session_mock = MagicMock()
        session_mock.flush = AsyncMock()
        session_mock.refresh = AsyncMock()
        service = StreakService(session=session_mock)

        now = datetime.now(UTC)
        two_days_ago = now - timedelta(days=2)
        user = SimpleNamespace(last_login_at=two_days_ago, streak_days=5, streak_last_date=two_days_ago.date())

        updated = await service.record_login(user)

        self.assertEqual(updated.streak_days, 1)
        self.assertEqual(updated.last_login_at.date(), now.date())
        session_mock.add.assert_called_once_with(updated)

    async def test_record_login_first_time(self) -> None:
        session_mock = MagicMock()
        session_mock.flush = AsyncMock()
        session_mock.refresh = AsyncMock()
        service = StreakService(session=session_mock)

        now = datetime.now(UTC)
        user = SimpleNamespace(last_login_at=None, streak_days=0, streak_last_date=None)

        updated = await service.record_login(user)

        self.assertEqual(updated.streak_days, 1)
        self.assertEqual(updated.last_login_at.date(), now.date())
        session_mock.add.assert_called_once_with(updated)

    def test_is_streak_active(self) -> None:
        now = datetime.now(UTC)
        
        # None -> False
        user_none = SimpleNamespace(last_login_at=None)
        self.assertFalse(StreakService.is_streak_active(user_none))

        # 24 hours ago -> True (cutoff is 25 hours)
        user_active = SimpleNamespace(last_login_at=now - timedelta(hours=24))
        self.assertTrue(StreakService.is_streak_active(user_active))

        # 26 hours ago -> False
        user_inactive = SimpleNamespace(last_login_at=now - timedelta(hours=26))
        self.assertFalse(StreakService.is_streak_active(user_inactive))
