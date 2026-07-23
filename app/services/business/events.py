from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import UIColorToken
from app.db.models.user import User
from app.schemas.frontend import FrontendUserResponse
from app.services.business.base import BusinessService
from app.services.business.daily_and_quests import _build_user_response
from app.services.errors import ForbiddenError, ItemNotFoundError, RewardAlreadyClaimedError
from app.services.event_progress import EventProgressService
from app.services.user import UserService
from app.services.xp_event import XpEventService


class EventModifierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    modifier_type: str
    value: str


class EventItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    item_id: int


class EventGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    target_value: int
    current_value: int
    reward_xp: int
    progress: int = 0
    is_completed: bool = False
    reward_claimed: bool = False


class EventDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    rarity: str
    xp_multiplier: str
    starts_at: datetime | None
    ends_at: datetime | None
    is_active: bool = True
    modifiers: list[EventModifierResponse] = []
    items: list[EventItemResponse] = []
    goals: list[EventGoalResponse] = []


class EventBusinessService(BusinessService):
    """Business scenarios for event views and reward claims."""

    event_progress_service: EventProgressService
    user_service: UserService
    xp_event_service: XpEventService

    async def get_active_events(
        self,
        current_user: User,
    ) -> list[EventDetailResponse]:
        events = await self.event_progress_service.get_active_events()
        if not events:
            return []

        event_ids = [event.id for event in events]
        modifiers_by_event: dict[str, list[EventModifierResponse]] = {}
        for modifier in await self.event_progress_service.get_modifiers(
            event_ids=event_ids
        ):
            modifiers_by_event.setdefault(modifier.event_id, []).append(
                EventModifierResponse(**modifier.model_dump())
            )

        items_by_event: dict[str, list[EventItemResponse]] = {}
        for item in await self.event_progress_service.get_items(event_ids=event_ids):
            items_by_event.setdefault(item.event_id, []).append(
                EventItemResponse(**item.model_dump())
            )

        goals_by_event: dict[str, list] = {}
        for goal in await self.event_progress_service.get_goals(event_ids=event_ids):
            goals_by_event.setdefault(goal.event_id, []).append(goal)

        user_events_by_event = {
            user_event.event_id: user_event
            for user_event in await self.event_progress_service.get_user_events(
                user_id=current_user.id,
                event_ids=event_ids,
            )
        }

        responses: list[EventDetailResponse] = []
        for event in events:
            goal_responses = []
            user_event = user_events_by_event.get(event.id)
            for goal in goals_by_event.get(event.id, []):
                goal_responses.append(
                    EventGoalResponse(
                        **goal.model_dump(),
                        progress=user_event.progress if user_event else 0,
                        is_completed=bool(
                            user_event is not None
                            and user_event.completed_at is not None
                        ),
                        reward_claimed=(
                            user_event.reward_claimed if user_event else False
                        ),
                    )
                )

            responses.append(
                EventDetailResponse(
                    **event.model_dump(),
                    modifiers=modifiers_by_event.get(event.id, []),
                    items=items_by_event.get(event.id, []),
                    goals=goal_responses,
                )
            )
        return responses

    async def claim_goal_reward(
        self,
        current_user: User,
        event_id: str,
        goal_id: str,
    ) -> FrontendUserResponse:
        user_event = await self.event_progress_service.get_user_event(
            user_id=current_user.id,
            event_id=event_id,
        )
        if user_event is None or user_event.completed_at is None:
            raise ForbiddenError("Goal is not completed yet.")
        if user_event.reward_claimed:
            raise RewardAlreadyClaimedError("Goal reward already claimed.")

        goal = await self.event_progress_service.get_goal(goal_id=goal_id)
        if goal is None or goal.event_id != event_id:
            raise ItemNotFoundError("Goal not found for this event.")

        xp = goal.reward_xp
        source = f"event_goal:{current_user.id}:{event_id}:{goal_id}"
        existing_event = await self.xp_event_service.get_user_event_by_source(
            user_id=current_user.id,
            source=source,
        )

        updated_user = current_user
        if existing_event is None and xp > 0:
            await self.xp_event_service.create_event(
                user_id=current_user.id,
                xp=xp,
                source=source,
                tag="event",
                color=UIColorToken.PINK,
                occurred_at=datetime.now(UTC),
            )
            updated_user = await self.user_service.add_xp_and_check_level_up(
                current_user,
                xp,
            )

        await self.event_progress_service.mark_reward_claimed(user_event)
        return _build_user_response(updated_user)
