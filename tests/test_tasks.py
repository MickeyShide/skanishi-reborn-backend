"""
Tests for primary Celery workers in tasks.py
"""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.tasks import process_scan_claimed, send_notification


class MainTasksTests(IsolatedAsyncioTestCase):
    @patch("app.workers.tasks.session_context")
    async def test_process_scan_claimed_inserts_event_and_updates_user(self, mock_session_context) -> None:
        session_mock = AsyncMock()
        async_ctx_manager = MagicMock()
        async_ctx_manager.__aenter__ = AsyncMock(return_value=session_mock)
        async_ctx_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session_context.return_value = async_ctx_manager

        payload = {
            "event_id": "test_event_1",
            "user_id": 1,
            "reward_xp": 100,
            "reward_coins": 50,
            "reward_fragment_amount": 1,
            "reward_fragment_rarity": "RARE",
            "request_id": "req-1"
        }

        # Mock idempotency check (no existing processed event)
        processed_event_result = MagicMock()
        processed_event_result.scalar_one_or_none.return_value = None
        session_mock.execute.return_value = processed_event_result

        # Mock User
        user = SimpleNamespace(id=1, xp=0, level=1, coins=0)
        
        # Patch User lookup and add methods.
        with patch("app.workers.tasks.asyncio.run", new=lambda coro: coro):
            with patch("app.workers.tasks.UserService.get_user_by_id", new_callable=AsyncMock) as mock_get_user:
                mock_get_user.return_value = user
                with patch("app.workers.tasks.UserService.add_fragment", new_callable=AsyncMock) as mock_add_fragment:
                    async def apply_xp(_, target, amount):
                        target.xp += amount
                        target.coins += amount // 2
                        return target

                    with patch(
                        "app.workers.tasks.UserService.add_xp_and_check_level_up",
                        new=apply_xp,
                    ):
                        with patch("app.workers.tasks.redis_client") as mock_redis:
                            mock_redis.publish = AsyncMock()

                            coro = process_scan_claimed.run(payload)
                            await coro

                            # User stats updated
                            self.assertEqual(user.xp, 100)
                            self.assertEqual(user.coins, 100)

                            # Fragment added
                            mock_add_fragment.assert_awaited_once_with(user, "RARE", 1)

                            # ProcessedEvent inserted
                            self.assertEqual(session_mock.add.call_count, 1)
                            self.assertEqual(session_mock.add.call_args[0][0].event_id, "test_event_1")

                            # Notifications published
                            mock_redis.publish.assert_awaited()

    @patch("app.workers.tasks.session_context")
    async def test_process_scan_claimed_idempotency(self, mock_session_context) -> None:
        session_mock = AsyncMock()
        async_ctx_manager = MagicMock()
        async_ctx_manager.__aenter__ = AsyncMock(return_value=session_mock)
        async_ctx_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session_context.return_value = async_ctx_manager

        payload = {"event_id": "test_event_2", "user_id": 1}

        # Event already processed
        processed_event_result = MagicMock()
        processed_event_result.scalar_one_or_none.return_value = SimpleNamespace(id=1)
        session_mock.execute.return_value = processed_event_result

        with patch("app.workers.tasks.asyncio.run", new=lambda coro: coro):
            coro = process_scan_claimed.run(payload)
            await coro

            session_mock.add.assert_not_called()
            session_mock.commit.assert_not_awaited()

    def test_send_notification(self) -> None:
        payload = {"user_id": 1, "type": "test_type", "data": {}}
        
        with patch("app.workers.tasks.asyncio.run", new=lambda coro: coro):
            with patch("app.workers.tasks.redis_client") as mock_redis:
                mock_redis.publish = AsyncMock()

                coro = send_notification(payload)
                # It's an async function passed to asyncio.run
                import asyncio
                asyncio.run(coro)

                mock_redis.publish.assert_awaited_once_with(
                    "sse:user:1",
                    '{"type": "test_type", "data": {}}'
                )
