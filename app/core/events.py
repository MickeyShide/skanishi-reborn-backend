from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Central event router.

    Maps outbox event types to one or more Celery task chains.
    Import tasks lazily inside each branch to avoid circular imports at
    module load time (celery_app imports tasks which import models, etc.).
    """

    def emit(self, event_name: str, payload: dict) -> None:
        from app.workers.tasks import (
            process_scan_claimed,
            send_notification,
        )

        if event_name == "scan_claimed":
            # Primary: award XP + level-up
            process_scan_claimed.delay(payload)

            # Secondary async checks (fire-and-forget; each is idempotent)
            self._dispatch_scan_side_effects(payload)

        elif event_name == "level_up":
            send_notification.delay(
                {
                    "user_id": payload.get("user_id"),
                    "type": "level_up",
                    "data": {
                        "old_level": payload.get("old_level"),
                        "new_level": payload.get("new_level"),
                    },
                    "request_id": payload.get("request_id"),
                }
            )

        elif event_name == "quest_completed":
            send_notification.delay(
                {
                    "user_id": payload.get("user_id"),
                    "type": "quest_completed",
                    "data": {
                        "quest_id": payload.get("quest_id"),
                        "quest_name": payload.get("quest_name", ""),
                        "xp": payload.get("reward_xp", 0),
                    },
                    "request_id": payload.get("request_id"),
                }
            )

        elif event_name == "achievement_unlocked":
            send_notification.delay(
                {
                    "user_id": payload.get("user_id"),
                    "type": "achievement_unlocked",
                    "data": {
                        "achievement_id": payload.get("achievement_id"),
                        "name": payload.get("name", ""),
                        "xp": payload.get("xp", 0),
                        "rarity": payload.get("rarity", "common"),
                    },
                    "request_id": payload.get("request_id"),
                }
            )

        elif event_name == "daily_claimed":
            send_notification.delay(
                {
                    "user_id": payload.get("user_id"),
                    "type": "daily_claimed",
                    "data": {
                        "xp": payload.get("xp", 0),
                        "streak": payload.get("streak", 0),
                    },
                    "request_id": payload.get("request_id"),
                }
            )

        elif event_name == "collection_completed":
            send_notification.delay(
                {
                    "user_id": payload.get("user_id"),
                    "type": "collection_completed",
                    "data": {
                        "collection_id": payload.get("collection_id"),
                        "name": payload.get("name", ""),
                    },
                    "request_id": payload.get("request_id"),
                }
            )

        else:
            logger.warning("Unknown outbox event type: %s", event_name)

    def _dispatch_scan_side_effects(self, payload: dict) -> None:
        """Fire async workers that react to a scan_claimed event.

        Each worker is independently idempotent — failures are retried
        without affecting the others.
        """
        from app.workers.game_tasks import (
            process_achievement_check,
            process_collection_progress,
            process_quest_progress,
        )

        process_quest_progress.delay(payload)
        process_achievement_check.delay(payload)
        process_collection_progress.delay(payload)


event_dispatcher = EventDispatcher()
