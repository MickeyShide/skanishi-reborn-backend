"""Business scenarios for daily rewards and user quest progress."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel

from app.db.models.enums import UIColorToken
from app.db.models.user import User
from app.schemas.frontend import FrontendUserResponse, QuestCardResponse
from app.services.business.base import BusinessService
from app.services.daily_reward import DailyRewardService, _xp_for_day
from app.services.errors import ForbiddenError, ItemNotFoundError, RewardAlreadyClaimedError
from app.services.quest import QuestService
from app.services.streak import StreakService, get_streak_xp_multiplier
from app.services.user import UserService
from app.services.user_quest import UserQuestService
from app.services.xp_event import XpEventService


class DailyStatusResponse(BaseModel):
    claimed_today: bool = False
    current_streak: int = 0
    xp_reward: int = 0
    next_reward_xp: int = 0
    streak_multiplier: float = 1.0
    is_available: bool | None = None
    reward_xp: int | None = None
    streak_days: int | None = None


class DailyClaimResponse(BaseModel):
    xp: int = 0
    current_streak: int = 0
    streak_multiplier: float = 1.0
    user: FrontendUserResponse
    reward_xp: int | None = None
    streak_days: int | None = None


class DailyRewardBusinessService(BusinessService):
    """Orchestrates daily reward claim and status queries."""

    daily_reward_service: DailyRewardService
    streak_service: StreakService
    user_service: UserService

    async def get_daily_status(self, current_user: User) -> DailyStatusResponse:
        claimed = not self.daily_reward_service.can_claim(current_user)
        streak = current_user.streak_days or 0
        xp_today = _xp_for_day(streak if claimed else max(streak + 1, 1))

        return DailyStatusResponse(
            claimed_today=claimed,
            current_streak=streak,
            xp_reward=xp_today,
            next_reward_xp=self.daily_reward_service.next_reward_xp(current_user),
            streak_multiplier=get_streak_xp_multiplier(streak),
        )

    async def claim_daily_reward(self, current_user: User) -> DailyClaimResponse:
        user = await self.streak_service.record_login(current_user)
        if not self.daily_reward_service.can_claim(user):
            raise RewardAlreadyClaimedError("Daily reward already claimed today.")

        xp, _ = await self.daily_reward_service.claim(user)
        updated_user = await self.user_service.add_xp_and_check_level_up(user, xp)
        streak = updated_user.streak_days or 0

        return DailyClaimResponse(
            xp=xp,
            current_streak=streak,
            streak_multiplier=get_streak_xp_multiplier(streak),
            user=_build_user_response(updated_user),
        )


def _build_user_response(user: User) -> FrontendUserResponse:
    return FrontendUserResponse(
        name=user.display_name or user.first_name,
        username=user.username or user.public_id or f"user{user.id}",
        id=user.public_id or str(user.id),
        rank=user.rank,
        level=user.level,
        level_progress=user.level_progress,
        xp=user.xp or 0,
        next_level_xp=user.next_level_xp or 1000,
        streak_days=user.streak_days or 0,
        season=user.season_label or "",
        coins=getattr(user, "coins", 0),
        active_border_id=getattr(user, "active_border_id", None),
        active_bg_id=getattr(user, "active_bg_id", None),
    )


class UserQuestBusinessService(BusinessService):
    """Handles per-user quest progress and reward claiming."""

    user_service: UserService
    quest_service: QuestService
    user_quest_service: UserQuestService
    xp_event_service: XpEventService

    async def get_user_quests(self, current_user: User) -> list[QuestCardResponse]:
        quests = await self.quest_service.get_active_quests()
        user_quests = await self.user_quest_service.get_for_user_and_quests(
            user_id=current_user.id,
            quest_ids=[quest.id for quest in quests],
        )
        quest_progress = {user_quest.quest_id: user_quest for user_quest in user_quests}

        cards: list[QuestCardResponse] = []
        for quest in quests:
            user_quest = quest_progress.get(quest.id)
            progress = user_quest.progress if user_quest else 0
            cards.append(
                QuestCardResponse(
                    id=quest.id,
                    name=quest.name,
                    step=f"{progress}/{quest.target_count}",
                    progress=min(100, int(progress / max(quest.target_count, 1) * 100)),
                    rarity=quest.rarity,
                    xp=quest.reward_xp,
                )
            )
        return cards

    async def claim_quest_reward(
        self,
        current_user: User,
        quest_id: str,
    ) -> DailyClaimResponse:
        user_quest = await self.user_quest_service.get_for_user_and_quest(
            user_id=current_user.id,
            quest_id=quest_id,
        )
        if user_quest is None or user_quest.completed_at is None:
            raise ForbiddenError("Quest not completed yet.")
        if user_quest.reward_claimed:
            raise RewardAlreadyClaimedError("Quest reward already claimed.")

        quest = await self.quest_service.get_quest(quest_id)
        if quest is None:
            raise ItemNotFoundError(f"Quest {quest_id} not found.")

        xp = quest.reward_xp
        await self.xp_event_service.create_event(
            user_id=current_user.id,
            xp=xp,
            source=f"quest:{current_user.id}:{quest_id}",
            tag="quest",
            color=UIColorToken.VIOLET_HI,
            occurred_at=datetime.now(UTC),
        )
        await self.user_quest_service.mark_reward_claimed(user_quest)
        updated_user = await self.user_service.add_xp_and_check_level_up(
            current_user,
            xp,
        )
        streak = updated_user.streak_days or 0

        return DailyClaimResponse(
            xp=xp,
            current_streak=streak,
            streak_multiplier=get_streak_xp_multiplier(streak),
            user=_build_user_response(updated_user),
        )
