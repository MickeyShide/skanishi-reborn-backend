from __future__ import annotations

from datetime import UTC, date, datetime

from app.db.models.enums import UIColorToken
from app.db.models.user import User
from app.db.models.xp_event import XpEvent
from app.db.repositories.user import UserRepository
from app.db.repositories.xp_event import XpEventRepository
from app.services.base import BaseService
from app.services.errors import RewardAlreadyClaimedError

# Daily reward XP by consecutive streak day (1-indexed).
# Non-defined days use the FALLBACK value.
DAILY_REWARD_TABLE: dict[int, int] = {
    1: 50,
    2: 75,
    3: 100,
    4: 125,
    5: 150,
    6: 175,
    7: 300,  # streak bonus
}
DAILY_REWARD_FALLBACK = 50


def _xp_for_day(day: int) -> int:
    return DAILY_REWARD_TABLE.get(day, DAILY_REWARD_FALLBACK)


def _daily_source(user_id: int, today: date) -> str:
    return f"daily:{user_id}:{today.isoformat()}"


class DailyRewardService(BaseService):
    """Handles daily login reward logic.

    Designed to be called within a BusinessService transaction.
    The caller is responsible for the final commit.
    """

    repositories = {
        "user_repository": UserRepository,
        "xp_event_repository": XpEventRepository,
    }

    user_repository: UserRepository
    xp_event_repository: XpEventRepository

    def can_claim(self, user: User) -> bool:
        """Return True if the user has not yet claimed today's daily reward."""
        today = datetime.now(UTC).date()
        return user.last_daily_claimed_at != today

    async def claim(self, user: User) -> tuple[int, XpEvent]:
        """
        Grant the daily reward for today.

        Returns (xp_awarded, xp_event).
        Raises ValueError if already claimed today.
        """
        today = datetime.now(UTC).date()

        if user.last_daily_claimed_at == today:
            raise RewardAlreadyClaimedError("Daily reward already claimed today.")

        xp = _xp_for_day(user.streak_days or 1)
        source = _daily_source(user.id, today)

        xp_event = await self.xp_event_repository.create(
            user_id=user.id,
            xp=xp,
            source=source,
            tag="daily",
            color=UIColorToken.GOLD,
            occurred_at=datetime.now(UTC),
        )
        await self.user_repository.update(user, last_daily_claimed_at=today)

        return xp, xp_event

    @staticmethod
    def next_reward_xp(user: User) -> int:
        """How much XP the user will get on their next claim (tomorrow if claimed today)."""
        next_day = (user.streak_days or 0) + 1
        return _xp_for_day(next_day)
