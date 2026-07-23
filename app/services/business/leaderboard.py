from __future__ import annotations

from app.schemas.frontend import FrontendUserResponse
from app.services.business.base import BusinessService
from app.services.user import UserService


class LeaderboardBusinessService(BusinessService):
    """Business service for retrieving leaderboard data."""

    user_service: UserService

    async def get_top_users(self, limit: int = 50, offset: int = 0) -> list[FrontendUserResponse]:
        """Return the top users sorted by rank (which is based on XP)."""
        users = await self.user_service.get_public_leaderboard(
            limit=limit,
            offset=offset,
        )

        from app.services.business.frontend_data import FrontendDataBusinessService

        return [FrontendDataBusinessService._build_frontend_user(u) for u in users]
