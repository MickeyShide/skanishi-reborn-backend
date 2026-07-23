"""
Tests for Celery workers in game_tasks.py

Covers:
- process_quest_progress
"""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.game_tasks import process_quest_progress


class GameTasksTests(IsolatedAsyncioTestCase):
    @patch("app.workers.game_tasks.session_context")
    async def test_process_quest_progress_increments_and_completes(self, mock_session_context) -> None:
        # Mock session
        session_mock = AsyncMock()
        
        # Async context manager mock
        async_ctx_manager = MagicMock()
        async_ctx_manager.__aenter__ = AsyncMock(return_value=session_mock)
        async_ctx_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session_context.return_value = async_ctx_manager

        # Mock Quests
        quest1 = SimpleNamespace(id="q1", name="Quest 1", target_count=3, is_active=True, condition_tag="scan", reward_xp=100)
        quests_result = MagicMock()
        quests_result.scalars.return_value.all.return_value = [quest1]

        # Mock UserQuest (current progress is 2, so it will reach 3 and complete)
        uq1 = SimpleNamespace(user_id=1, quest_id="q1", progress=2, completed_at=None)
        uq_result = MagicMock()
        uq_result.scalars.return_value.all.return_value = [uq1]

        session_mock.execute = AsyncMock(side_effect=[quests_result, uq_result])

        payload = {"user_id": 1, "tag": "scan"}

        # Patch asyncio.run so it returns the coroutine instead of executing it synchronously.
        # Then we can await it ourselves in the async test.
        with patch("app.workers.game_tasks.asyncio.run", new=lambda coro: coro):
            with patch("app.workers.game_tasks.event_dispatcher") as mock_dispatcher:
                # Call the worker (it returns the coroutine because of our asyncio.run patch)
                coro = process_quest_progress.run(payload)
                await coro

                self.assertEqual(uq1.progress, 3)
                self.assertIsNotNone(uq1.completed_at)
                
                # Ensure the outbox event was emitted for completion
                mock_dispatcher.emit.assert_called_once_with(
                    "quest_completed",
                    {
                        "user_id": 1,
                        "quest_id": "q1",
                        "quest_name": "Quest 1",
                        "reward_xp": 100,
                        "request_id": mock_dispatcher.emit.call_args[0][1]["request_id"]
                    }
                )
                session_mock.commit.assert_awaited_once()

    @patch("app.workers.game_tasks.session_context")
    async def test_process_quest_progress_new_quest_creation(self, mock_session_context) -> None:
        session_mock = AsyncMock()
        async_ctx_manager = MagicMock()
        async_ctx_manager.__aenter__ = AsyncMock(return_value=session_mock)
        async_ctx_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session_context.return_value = async_ctx_manager

        quest1 = SimpleNamespace(id="q1", name="Q1", target_count=5, is_active=True, condition_tag="scan", reward_xp=100)
        quests_result = MagicMock()
        quests_result.scalars.return_value.all.return_value = [quest1]

        uq_result = MagicMock()
        uq_result.scalars.return_value.all.return_value = [] # No existing progress

        session_mock.execute = AsyncMock(side_effect=[quests_result, uq_result])

        payload = {"user_id": 1, "tag": "scan"}

        with patch("app.workers.game_tasks.asyncio.run", new=lambda coro: coro):
            with patch("app.workers.game_tasks.UserQuest") as mock_user_quest:
                # Give it a fake instance when instantiated
                fake_uq = SimpleNamespace(user_id=1, quest_id="q1", progress=0, completed_at=None)
                mock_user_quest.return_value = fake_uq

                await process_quest_progress.run(payload)

                session_mock.add.assert_called_once_with(fake_uq)
                self.assertEqual(fake_uq.progress, 1)
                self.assertIsNone(fake_uq.completed_at)
