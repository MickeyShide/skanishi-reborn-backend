from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import CurrentUser, enforce_csrf_protection
from app.db.models.user import User
from app.services.business.daily_and_quests import (
    DailyClaimResponse,
    DailyRewardBusinessService,
    DailyStatusResponse,
)

router = APIRouter(prefix="/daily", tags=["Daily Reward"])


@router.get("/status", response_model=DailyStatusResponse)
async def get_daily_status(current_user: CurrentUser) -> DailyStatusResponse:
    """Return whether the daily reward is available and how much XP it will grant."""
    return await DailyRewardBusinessService().get_daily_status(current_user)


@router.post(
    "/claim",
    response_model=DailyClaimResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def claim_daily_reward(current_user: CurrentUser) -> DailyClaimResponse:
    """Claim today's daily login reward.

    Returns 409 if already claimed today.
    """
    return await DailyRewardBusinessService().claim_daily_reward(current_user)
