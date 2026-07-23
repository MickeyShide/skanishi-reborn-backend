"""
Tests for Celery workers in outbox.py

Covers:
- publish_outbox_events
"""

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.outbox import publish_outbox_events
from app.db.models.system_events import OutboxEventStatus


class OutboxTasksTests(IsolatedAsyncioTestCase):
    @patch("app.workers.outbox.session_context")
    async def test_publish_outbox_events(self, mock_session_context) -> None:
        session_mock = AsyncMock()
        async_ctx_manager = MagicMock()
        async_ctx_manager.__aenter__ = AsyncMock(return_value=session_mock)
        async_ctx_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session_context.return_value = async_ctx_manager

        event1 = SimpleNamespace(id=1, event_type="scan_claimed", payload={"user_id": 1}, status=OutboxEventStatus.PENDING)
        event2 = SimpleNamespace(id=2, event_type="quest_completed", payload={"quest_id": "q1"}, status=OutboxEventStatus.PENDING)

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [event1, event2]
        session_mock.execute = AsyncMock(return_value=events_result)

        with patch("app.workers.outbox.asyncio.run", new=lambda coro: coro):
            with patch("app.workers.outbox.event_dispatcher") as mock_dispatcher:
                coro = publish_outbox_events()
                await coro

                self.assertEqual(mock_dispatcher.emit.call_count, 2)
                mock_dispatcher.emit.assert_any_call("scan_claimed", {"user_id": 1})
                mock_dispatcher.emit.assert_any_call("quest_completed", {"quest_id": "q1"})

                self.assertEqual(event1.status, OutboxEventStatus.PUBLISHED)
                self.assertEqual(event2.status, OutboxEventStatus.PUBLISHED)
                
                session_mock.commit.assert_awaited_once()

    @patch("app.workers.outbox.session_context")
    async def test_publish_outbox_events_handles_exceptions(self, mock_session_context) -> None:
        session_mock = AsyncMock()
        async_ctx_manager = MagicMock()
        async_ctx_manager.__aenter__ = AsyncMock(return_value=session_mock)
        async_ctx_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session_context.return_value = async_ctx_manager

        event1 = SimpleNamespace(id=1, event_type="fail_event", payload={}, status=OutboxEventStatus.PENDING)
        event2 = SimpleNamespace(id=2, event_type="ok_event", payload={}, status=OutboxEventStatus.PENDING)

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [event1, event2]
        session_mock.execute = AsyncMock(return_value=events_result)

        with patch("app.workers.outbox.asyncio.run", new=lambda coro: coro):
            with patch("app.workers.outbox.event_dispatcher") as mock_dispatcher:
                # Dispatcher raises error for event1
                def mock_emit(event_type, payload):
                    if event_type == "fail_event":
                        raise ValueError("Simulated failure")
                mock_dispatcher.emit.side_effect = mock_emit

                coro = publish_outbox_events()
                await coro

                # Event 1 remains PENDING
                self.assertEqual(event1.status, OutboxEventStatus.PENDING)
                # Event 2 is PUBLISHED
                self.assertEqual(event2.status, OutboxEventStatus.PUBLISHED)
                
                session_mock.commit.assert_awaited_once()
