from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from app.services.business.daily_and_quests import (
    DailyRewardBusinessService,
    UserQuestBusinessService,
)
from app.services.errors import ForbiddenError, ItemNotFoundError, RewardAlreadyClaimedError


def build_user() -> SimpleNamespace:
    return SimpleNamespace(
        id=1, display_name="Test", first_name="Test", username="test", public_id="pub",
        rank=1, level=3, level_progress=20, xp=6000, next_level_xp=10000,
        streak_days=5, season_label="Season", coins=100, active_border_id=None,
        active_bg_id=None,
    )


class DailyRewardBusinessServiceTests(IsolatedAsyncioTestCase):
    def make_service(self) -> DailyRewardBusinessService:
        service = object.__new__(DailyRewardBusinessService)
        service.daily_reward_service = MagicMock()
        service.daily_reward_service.claim = AsyncMock()
        service.streak_service = MagicMock()
        service.streak_service.record_login = AsyncMock()
        service.user_service = MagicMock()
        service.user_service.add_xp_and_check_level_up = AsyncMock()
        return service

    async def test_get_daily_status(self) -> None:
        service = self.make_service()
        user = SimpleNamespace(streak_days=3)
        service.daily_reward_service.can_claim.return_value = True
        service.daily_reward_service.next_reward_xp.return_value = 250

        result = await service.get_daily_status(user)

        self.assertFalse(result.claimed_today)
        self.assertEqual(result.current_streak, 3)
        self.assertEqual(result.next_reward_xp, 250)

    async def test_claim_daily_reward(self) -> None:
        service = self.make_service()
        user = build_user()
        service.streak_service.record_login.return_value = user
        service.daily_reward_service.can_claim.return_value = True
        service.daily_reward_service.claim.return_value = (100, MagicMock())
        service.user_service.add_xp_and_check_level_up.return_value = user

        result = await service.claim_daily_reward(user)

        self.assertEqual(result.xp, 100)
        service.user_service.add_xp_and_check_level_up.assert_awaited_once_with(user, 100)

    async def test_claim_daily_reward_rejects_duplicate(self) -> None:
        service = self.make_service()
        user = build_user()
        service.streak_service.record_login.return_value = user
        service.daily_reward_service.can_claim.return_value = False

        with self.assertRaises(RewardAlreadyClaimedError):
            await service.claim_daily_reward(user)


class UserQuestBusinessServiceTests(IsolatedAsyncioTestCase):
    def make_service(self) -> UserQuestBusinessService:
        service = object.__new__(UserQuestBusinessService)
        service.quest_service = MagicMock()
        service.quest_service.get_active_quests = AsyncMock()
        service.quest_service.get_quest = AsyncMock()
        service.user_quest_service = MagicMock()
        service.user_quest_service.get_for_user_and_quests = AsyncMock()
        service.user_quest_service.get_for_user_and_quest = AsyncMock()
        service.user_quest_service.mark_reward_claimed = AsyncMock()
        service.xp_event_service = MagicMock()
        service.xp_event_service.create_event = AsyncMock()
        service.user_service = MagicMock()
        service.user_service.add_xp_and_check_level_up = AsyncMock()
        return service

    async def test_get_user_quests_maps_progress(self) -> None:
        service = self.make_service()
        service.quest_service.get_active_quests.return_value = [
            SimpleNamespace(id="q1", name="Quest", target_count=5, rarity="common", reward_xp=100)
        ]
        service.user_quest_service.get_for_user_and_quests.return_value = [
            SimpleNamespace(quest_id="q1", progress=2)
        ]

        result = await service.get_user_quests(SimpleNamespace(id=1))

        self.assertEqual(result[0].step, "2/5")
        self.assertEqual(result[0].progress, 40)

    async def test_claim_quest_rejects_uncompleted(self) -> None:
        service = self.make_service()
        service.user_quest_service.get_for_user_and_quest.return_value = SimpleNamespace(
            completed_at=None,
            reward_claimed=False,
        )

        with self.assertRaises(ForbiddenError):
            await service.claim_quest_reward(SimpleNamespace(id=1), "q1")

    async def test_claim_quest_rejects_duplicate(self) -> None:
        service = self.make_service()
        service.user_quest_service.get_for_user_and_quest.return_value = SimpleNamespace(
            completed_at=object(),
            reward_claimed=True,
        )

        with self.assertRaises(RewardAlreadyClaimedError):
            await service.claim_quest_reward(SimpleNamespace(id=1), "q1")

    async def test_claim_quest_rejects_missing_definition(self) -> None:
        service = self.make_service()
        service.user_quest_service.get_for_user_and_quest.return_value = SimpleNamespace(
            completed_at=object(),
            reward_claimed=False,
        )
        service.quest_service.get_quest.return_value = None

        with self.assertRaises(ItemNotFoundError):
            await service.claim_quest_reward(SimpleNamespace(id=1), "q1")

    async def test_claim_quest_creates_event_and_marks_claimed(self) -> None:
        service = self.make_service()
        user = build_user()
        user_quest = SimpleNamespace(completed_at=object(), reward_claimed=False)
        service.user_quest_service.get_for_user_and_quest.return_value = user_quest
        service.quest_service.get_quest.return_value = SimpleNamespace(reward_xp=500)
        service.user_service.add_xp_and_check_level_up.return_value = user

        result = await service.claim_quest_reward(user, "q1")

        self.assertEqual(result.xp, 500)
        service.xp_event_service.create_event.assert_awaited_once()
        service.user_quest_service.mark_reward_claimed.assert_awaited_once_with(user_quest)
