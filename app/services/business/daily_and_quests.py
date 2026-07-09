"""Business services for daily reward and quest progress.

Both services follow the existing BusinessService pattern:
  - Lazy session from `_get_session()`
  - No explicit commits (caller / BusinessService base handles lifecycle)
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.db.models.enums import UIColorToken
from app.db.models.user import User
from app.db.models.user_quest import UserQuest
from app.schemas.frontend import FrontendUserResponse, QuestCardResponse
from app.services.business.base import BusinessService
from app.services.daily_reward import DailyRewardService
from app.services.quest import QuestService
from app.services.streak import StreakService
from app.services.user import UserService


# ──────────────────────────────────────────────────────────────────────────────
# Daily reward schemas (defined here to avoid circular imports)
# ──────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel


class DailyStatusResponse(BaseModel):
    claimed_today: bool
    current_streak: int
    xp_reward: int        # XP available now (or already earned today)
    next_reward_xp: int   # XP available tomorrow
    streak_multiplier: float


class DailyClaimResponse(BaseModel):
    xp: int
    current_streak: int
    streak_multiplier: float
    user: FrontendUserResponse


# ──────────────────────────────────────────────────────────────────────────────
# Daily Reward Business Service
# ──────────────────────────────────────────────────────────────────────────────

class DailyRewardBusinessService(BusinessService):
    """Orchestrates daily reward claim and status queries."""

    user_service: UserService

    async def get_daily_status(self, current_user: User) -> DailyStatusResponse:
        from app.services.daily_reward import DailyRewardService, _xp_for_day
        from app.services.streak import get_streak_xp_multiplier

        session = await self._get_session()
        daily_svc = DailyRewardService(session)
        claimed = not daily_svc.can_claim(current_user)
        streak = current_user.streak_days or 0

        if claimed:
            xp_today = _xp_for_day(streak)
        else:
            xp_today = _xp_for_day(max(streak + 1, 1))

        return DailyStatusResponse(
            claimed_today=claimed,
            current_streak=streak,
            xp_reward=xp_today,
            next_reward_xp=daily_svc.next_reward_xp(current_user),
            streak_multiplier=get_streak_xp_multiplier(streak),
        )

    async def claim_daily_reward(self, current_user: User) -> DailyClaimResponse:
        from app.services.daily_reward import DailyRewardService
        from app.services.errors import RewardAlreadyClaimedError
        from app.services.streak import StreakService, get_streak_xp_multiplier

        session = await self._get_session()

        # 1. Update streak first (so daily XP uses the new streak day)
        streak_svc = StreakService(session)
        user = await streak_svc.record_login(current_user)

        # 2. Claim daily reward
        daily_svc = DailyRewardService(session)
        if not daily_svc.can_claim(user):
            raise RewardAlreadyClaimedError("Daily reward already claimed today.")

        xp, _ = await daily_svc.claim(user)

        # 3. Apply XP to user.xp (also triggers level up check)
        user_svc = UserService(session)
        updated_user = await user_svc.add_xp_and_check_level_up(user, 0)
        # Note: DailyRewardService.claim() already added xp to user.xp,
        # so we pass 0 to only run the level-up check without double-adding.

        streak = updated_user.streak_days or 0

        from app.schemas.frontend import FrontendUserResponse

        return DailyClaimResponse(
            xp=xp,
            current_streak=streak,
            streak_multiplier=get_streak_xp_multiplier(streak),
            user=_build_user_response(updated_user),
        )


def _build_user_response(user: User) -> FrontendUserResponse:
    """Quick helper to build a FrontendUserResponse from a User ORM object."""
    from app.services.user import LEVEL_THRESHOLDS, get_next_level_xp

    level = user.level
    xp = user.xp or 0
    current_threshold = LEVEL_THRESHOLDS.get(level, xp)
    next_threshold = LEVEL_THRESHOLDS.get(level + 1, current_threshold)
    xp_in_level = xp - current_threshold
    level_range = max(next_threshold - current_threshold, 1)
    progress = min(100, int(xp_in_level / level_range * 100))

    return FrontendUserResponse(
        name=user.name or "",
        username=user.username or "",
        id=str(user.id),
        rank=user.rank,
        level=level,
        levelProgress=progress,
        xp=xp,
        nextLevelXp=next_threshold,
        streakDays=user.streak_days or 0,
        season=user.season_label or "",
    )


# ──────────────────────────────────────────────────────────────────────────────
# UserQuest Business Service
# ──────────────────────────────────────────────────────────────────────────────

class UserQuestBusinessService(BusinessService):
    """Handles per-user quest progress and reward claiming."""

    user_service: UserService
    quest_service: QuestService

    async def get_user_quests(self, current_user: User) -> list[QuestCardResponse]:
        """Return active quests with per-user progress injected."""
        from sqlalchemy import select

        session = await self._get_session()
        quests = await self.quest_service.get_active_quests()

        # Bulk-load UserQuest rows for this user
        from app.db.models.user_quest import UserQuest
        uq_result = await session.execute(
            select(UserQuest).where(
                UserQuest.user_id == current_user.id,
                UserQuest.quest_id.in_([q.id for q in quests]),
            )
        )
        uq_by_id: dict[str, UserQuest] = {uq.quest_id: uq for uq in uq_result.scalars().all()}

        cards: list[QuestCardResponse] = []
        for quest in quests:
            uq = uq_by_id.get(quest.id)
            progress = uq.progress if uq else 0
            pct = min(100, int(progress / max(quest.target_count, 1) * 100))
            step = f"{progress}/{quest.target_count}"
            cards.append(
                QuestCardResponse(
                    id=quest.id,
                    name=quest.name,
                    step=step,
                    progress=pct,
                    rarity=quest.rarity,
                    xp=quest.reward_xp,
                )
            )
        return cards

    async def claim_quest_reward(
        self, current_user: User, quest_id: str
    ) -> DailyClaimResponse:
        from sqlalchemy import select

        from app.db.models.user_quest import UserQuest
        from app.services.errors import (
            ItemNotFoundError,
            RewardAlreadyClaimedError,
            ForbiddenError,
        )

        session = await self._get_session()

        # Load quest
        result = await session.execute(
            select(UserQuest).where(
                UserQuest.user_id == current_user.id,
                UserQuest.quest_id == quest_id,
            )
        )
        uq: UserQuest | None = result.scalar_one_or_none()

        if uq is None or uq.completed_at is None:
            raise ForbiddenError("Quest not completed yet.")

        if uq.reward_claimed:
            raise RewardAlreadyClaimedError("Quest reward already claimed.")

        # Load quest definition for XP amount
        from app.db.models.quest import Quest
        quest_obj: Quest | None = await session.get(Quest, quest_id)
        if quest_obj is None:
            raise ItemNotFoundError(f"Quest {quest_id} not found.")

        xp = quest_obj.reward_xp
        source = f"quest:{current_user.id}:{quest_id}"

        from app.db.models.xp_event import XpEvent
        xp_event = XpEvent(
            user_id=current_user.id,
            xp=xp,
            source=source,
            tag="quest",
            color=UIColorToken.VIOLET_HI,
            occurred_at=datetime.now(UTC),
        )
        session.add(xp_event)

        uq.reward_claimed = True
        session.add(uq)

        # Apply XP
        user_svc = UserService(session)
        updated_user = await user_svc.add_xp_and_check_level_up(current_user, xp)

        from app.services.streak import get_streak_xp_multiplier
        streak = updated_user.streak_days or 0

        return DailyClaimResponse(
            xp=xp,
            current_streak=streak,
            streak_multiplier=get_streak_xp_multiplier(streak),
            user=_build_user_response(updated_user),
        )
