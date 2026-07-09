from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.services.base import BaseService


# Grace period: a user is still considered "active today" if they logged in
# within the last 25 hours.  This gives flexibility across timezone differences.
STREAK_BREAK_HOURS = 25

# XP multipliers keyed by streak length.  Non-listed lengths are 1.0×.
STREAK_MULTIPLIERS: dict[int, float] = {
    7: 1.5,
    14: 2.0,
    30: 2.5,
}


def get_streak_xp_multiplier(streak_days: int) -> float:
    """Return the XP multiplier for the given consecutive streak length."""
    for threshold in sorted(STREAK_MULTIPLIERS, reverse=True):
        if streak_days >= threshold:
            return STREAK_MULTIPLIERS[threshold]
    return 1.0


class StreakService(BaseService):
    """Manages login streak tracking.

    Called once per user session (e.g. inside get_app_state) to update
    last_login_at and potentially increment streak_days.
    """

    repositories: dict = {}  # no custom repositories needed

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def record_login(self, user: User) -> User:
        """Record a login event and update the streak counter.

        Logic:
          - If last_login_at is today (UTC) → no change (already recorded).
          - If last_login_at was yesterday (UTC) → streak_days += 1.
          - If last_login_at was >1 day ago OR None → reset streak_days = 1.
        """
        now = datetime.now(UTC)
        today = now.date()

        # Normalise last_login_at to UTC date
        if user.last_login_at is not None:
            last_date = user.last_login_at.astimezone(UTC).date()
        else:
            last_date = None

        # Already recorded a login today → nothing to do
        if last_date == today:
            return user

        yesterday = today - timedelta(days=1)

        if last_date == yesterday:
            # Consecutive day → extend streak
            new_streak = user.streak_days + 1
        else:
            # Gap or first ever login → start fresh
            new_streak = 1

        user.last_login_at = now
        user.streak_last_date = today
        user.streak_days = new_streak

        self.session.add(user)
        # The caller (BusinessService) owns the commit.
        return user

    @staticmethod
    def is_streak_active(user: User) -> bool:
        """Return True if the user's streak is still alive (logged in recently)."""
        if user.last_login_at is None:
            return False
        cutoff = datetime.now(UTC) - timedelta(hours=STREAK_BREAK_HOURS)
        return user.last_login_at >= cutoff
