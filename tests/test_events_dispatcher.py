"""
Tests for Core Event Dispatcher
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from app.core.events import EventDispatcher


class EventDispatcherTests(TestCase):
    def setUp(self) -> None:
        self.dispatcher = EventDispatcher()

    def test_emit_scan_claimed(self) -> None:
        payload = {"event_id": "test_scan", "user_id": 1}

        with patch("app.workers.tasks.process_scan_claimed.delay") as mock_process_scan:
            with patch.object(self.dispatcher, "_dispatch_scan_side_effects") as mock_side_effects:
                self.dispatcher.emit("scan_claimed", payload)

                mock_process_scan.assert_called_once_with(payload)
                mock_side_effects.assert_called_once_with(payload)

    def test_emit_level_up(self) -> None:
        payload = {"user_id": 1, "old_level": 1, "new_level": 2, "request_id": "req-1"}

        with patch("app.workers.tasks.send_notification.delay") as mock_send_notification:
            self.dispatcher.emit("level_up", payload)

            mock_send_notification.assert_called_once_with({
                "user_id": 1,
                "type": "level_up",
                "data": {
                    "old_level": 1,
                    "new_level": 2,
                },
                "request_id": "req-1",
            })

    def test_emit_quest_completed(self) -> None:
        payload = {"user_id": 1, "quest_id": "q1", "quest_name": "Quest 1", "reward_xp": 100}

        with patch("app.workers.tasks.send_notification.delay") as mock_send_notification:
            self.dispatcher.emit("quest_completed", payload)

            mock_send_notification.assert_called_once_with({
                "user_id": 1,
                "type": "quest_completed",
                "data": {
                    "quest_id": "q1",
                    "quest_name": "Quest 1",
                    "xp": 100,
                },
                "request_id": None,
            })

    def test_dispatch_scan_side_effects(self) -> None:
        payload = {"event_id": "test_scan", "user_id": 1}

        with patch("app.workers.game_tasks.process_quest_progress.delay") as mock_quest:
            with patch("app.workers.game_tasks.process_achievement_check.delay") as mock_achieve:
                with patch("app.workers.game_tasks.process_collection_progress.delay") as mock_col:
                    self.dispatcher._dispatch_scan_side_effects(payload)

                    mock_quest.assert_called_once_with(payload)
                    mock_achieve.assert_called_once_with(payload)
                    mock_col.assert_called_once_with(payload)
