from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import CurrentUser, enforce_csrf_protection
from app.schemas.frontend import FrontendUserResponse
from app.services.business.events import EventBusinessService, EventDetailResponse

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=list[EventDetailResponse])
async def get_events(current_user: CurrentUser) -> list[EventDetailResponse]:
    """Return all active events and user progress."""
    return await EventBusinessService().get_active_events(current_user)


@router.post(
    "/{event_id}/goals/{goal_id}/claim",
    response_model=FrontendUserResponse,
    dependencies=[Depends(enforce_csrf_protection)],
)
async def claim_event_goal_reward(
    event_id: str,
    goal_id: str,
    current_user: CurrentUser,
) -> FrontendUserResponse:
    """Claim the XP reward for a completed event goal."""
    return await EventBusinessService().claim_goal_reward(current_user, event_id, goal_id)
