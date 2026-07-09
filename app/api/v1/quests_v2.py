from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import CurrentUser, enforce_csrf_protection
from app.schemas.frontend import QuestCardResponse
from app.services.business.daily_and_quests import DailyClaimResponse, UserQuestBusinessService

router = APIRouter(prefix="/quests", tags=["Quests"])


@router.get("", response_model=list[QuestCardResponse])
async def get_user_quests(current_user: CurrentUser) -> list[QuestCardResponse]:
    """Return active quests with the current user's personal progress."""
    return await UserQuestBusinessService().get_user_quests(current_user)


@router.post(
    "/{quest_id}/claim",
    response_model=DailyClaimResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def claim_quest_reward(
    quest_id: str,
    current_user: CurrentUser,
) -> DailyClaimResponse:
    """Claim the XP reward for a completed quest."""
    return await UserQuestBusinessService().claim_quest_reward(current_user, quest_id)
