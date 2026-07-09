from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.v1.dependencies import CurrentUser
from app.schemas.frontend import FrontendUserResponse
from app.services.business.leaderboard import LeaderboardBusinessService

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("", response_model=list[FrontendUserResponse])
async def get_leaderboard(
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[FrontendUserResponse]:
    """Return top public users by XP."""
    return await LeaderboardBusinessService().get_top_users(limit=limit, offset=offset)
