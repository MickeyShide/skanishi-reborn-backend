from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from app.services.business.events import EventBusinessService
from app.services.errors import ForbiddenError, RewardAlreadyClaimedError


def build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=1, display_name="Test", first_name="Test", username="test", public_id="pub",
        rank=1, level=1, level_progress=0, xp=0, next_level_xp=1000,
        streak_days=1, season_label="S", coins=0, active_border_id=None, active_bg_id=None,
    )


class EventBusinessServiceTests(IsolatedAsyncioTestCase):
    def make_service(self) -> EventBusinessService:
        service = object.__new__(EventBusinessService)
        service.event_progress_service = MagicMock()
        for name in (
            "get_active_events", "get_modifiers", "get_items", "get_goals",
            "get_user_events", "get_user_event", "get_goal", "mark_reward_claimed",
        ):
            setattr(service.event_progress_service, name, AsyncMock())
        service.user_service = MagicMock()
        service.user_service.add_xp_and_check_level_up = AsyncMock()
        service.xp_event_service = MagicMock()
        service.xp_event_service.get_user_event_by_source = AsyncMock()
        service.xp_event_service.create_event = AsyncMock()
        return service

    async def test_get_active_events_merges_progress(self) -> None:
        service = self.make_service()
        event = SimpleNamespace(
            id="e1", title="Event", rarity="epic", xp_multiplier="1.5",
            starts_at=None, ends_at=None, is_active=True,
            model_dump=lambda: {"id": "e1", "title": "Event", "rarity": "epic", "xp_multiplier": "1.5", "starts_at": None, "ends_at": None, "is_active": True},
        )
        modifier = SimpleNamespace(
            event_id="e1",
            model_dump=lambda: {"id": 1, "event_id": "e1", "modifier_type": "xp", "value": "2"},
        )
        item = SimpleNamespace(
            event_id="e1",
            model_dump=lambda: {"id": 1, "event_id": "e1", "item_id": 10},
        )
        goal = SimpleNamespace(
            event_id="e1",
            model_dump=lambda: {"id": 1, "event_id": "e1", "target_value": 10, "current_value": 2, "reward_xp": 100},
        )
        service.event_progress_service.get_active_events.return_value = [event]
        service.event_progress_service.get_modifiers.return_value = [modifier]
        service.event_progress_service.get_items.return_value = [item]
        service.event_progress_service.get_goals.return_value = [goal]
        service.event_progress_service.get_user_events.return_value = [
            SimpleNamespace(event_id="e1", progress=5, completed_at=None, reward_claimed=False)
        ]

        result = await service.get_active_events(SimpleNamespace(id=1))

        self.assertEqual(result[0].goals[0].progress, 5)
        self.assertEqual(result[0].modifiers[0].value, "2")

    async def test_claim_goal_rejects_uncompleted_event(self) -> None:
        service = self.make_service()
        service.event_progress_service.get_user_event.return_value = SimpleNamespace(
            completed_at=None,
            reward_claimed=False,
        )

        with self.assertRaises(ForbiddenError):
            await service.claim_goal_reward(SimpleNamespace(id=1), "e1", "g1")

    async def test_claim_goal_rejects_duplicate_claim(self) -> None:
        service = self.make_service()
        service.event_progress_service.get_user_event.return_value = SimpleNamespace(
            completed_at=object(),
            reward_claimed=True,
        )

        with self.assertRaises(RewardAlreadyClaimedError):
            await service.claim_goal_reward(SimpleNamespace(id=1), "e1", "g1")

    async def test_claim_goal_creates_event_and_marks_claimed(self) -> None:
        service = self.make_service()
        user = build_user()
        user_event = SimpleNamespace(completed_at=object(), reward_claimed=False)
        service.event_progress_service.get_user_event.return_value = user_event
        service.event_progress_service.get_goal.return_value = SimpleNamespace(
            event_id="e1",
            reward_xp=250,
        )
        service.xp_event_service.get_user_event_by_source.return_value = None
        service.user_service.add_xp_and_check_level_up.return_value = user

        result = await service.claim_goal_reward(user, "e1", "g1")

        self.assertEqual(result.id, "pub")
        service.xp_event_service.create_event.assert_awaited_once()
        service.event_progress_service.mark_reward_claimed.assert_awaited_once_with(user_event)
