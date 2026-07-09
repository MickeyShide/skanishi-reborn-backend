from __future__ import annotations

from sqlalchemy import select

from app.db.models.user import User
from app.schemas.frontend import FrontendUserResponse
from app.services.business.base import BusinessService


class LeaderboardBusinessService(BusinessService):
    """Business service for retrieving leaderboard data."""

    async def get_top_users(self, limit: int = 50, offset: int = 0) -> list[FrontendUserResponse]:
        """Return the top users sorted by rank (which is based on XP)."""
        session = await self._get_session()

        result = await session.execute(
            select(User)
            .where(User.is_private.is_(False))
            .order_by(User.rank.asc(), User.id.asc())
            .offset(offset)
            .limit(limit)
        )
        users = list(result.scalars().all())

        from app.services.business.frontend_data import FrontendDataService
        
        # Build responses
        return [FrontendDataService._build_frontend_user(u) for u in users]
