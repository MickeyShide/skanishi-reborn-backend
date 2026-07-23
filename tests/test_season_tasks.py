"""
Tests for Celery workers in season_tasks.py

Covers:
- close_active_season
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.season_tasks import close_active_season


class SeasonTasksTests(IsolatedAsyncioTestCase):
    @patch("app.workers.season_tasks.session_context")
    async def test_close_active_season_archives_and_resets(self, mock_session_context) -> None:
        session_mock = AsyncMock()
        async_ctx_manager = MagicMock()
        async_ctx_manager.__aenter__ = AsyncMock(return_value=session_mock)
        async_ctx_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session_context.return_value = async_ctx_manager

        now = datetime.now(UTC)
        past_date = now - timedelta(days=1)

        # Mock Active Season that has ended
        active_season = SimpleNamespace(id=1, name="S1", is_active=True, ends_at=past_date)
        active_season_result = MagicMock()
        active_season_result.scalar_one_or_none.return_value = active_season

        # Mock Users
        user1 = SimpleNamespace(id=1, xp=5000, level=5, rank=10, is_private=False)
        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = [user1]

        # Mock Next Season (not available)
        next_season_result = MagicMock()
        next_season_result.scalar_one_or_none.return_value = None

        session_mock.execute = AsyncMock(side_effect=[active_season_result, user_result, MagicMock(), next_season_result, MagicMock()])

        with patch("app.workers.season_tasks.asyncio.run", new=lambda coro: coro):
            with patch("app.workers.season_tasks.UserSeasonHistory") as mock_ush:
                fake_history = SimpleNamespace()
                mock_ush.return_value = fake_history

                # Run worker
                coro = close_active_season()
                await coro

                self.assertFalse(active_season.is_active)
                session_mock.add_all.assert_called_once()
                session_mock.commit.assert_awaited_once()

    @patch("app.workers.season_tasks.session_context")
    async def test_close_active_season_no_action_if_not_ended(self, mock_session_context) -> None:
        session_mock = AsyncMock()
        async_ctx_manager = MagicMock()
        async_ctx_manager.__aenter__ = AsyncMock(return_value=session_mock)
        async_ctx_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session_context.return_value = async_ctx_manager

        now = datetime.now(UTC)
        future_date = now + timedelta(days=1)

        active_season = SimpleNamespace(id=1, name="S1", is_active=True, ends_at=future_date)
        active_season_result = MagicMock()
        active_season_result.scalar_one_or_none.return_value = active_season

        session_mock.execute = AsyncMock(side_effect=[active_season_result])

        with patch("app.workers.season_tasks.asyncio.run", new=lambda coro: coro):
            coro = close_active_season()
            await coro

            session_mock.commit.assert_not_called()
