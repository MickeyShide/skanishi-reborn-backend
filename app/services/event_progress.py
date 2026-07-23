from datetime import UTC, datetime

from app.db.models.event import Event
from app.db.models.event_extended import EventGoal, EventItem, EventModifier, UserEvent
from app.db.repositories.event import EventRepository
from app.services.base import BaseService


class EventProgressService(BaseService):
    repositories = {"event_repository": EventRepository}

    event_repository: EventRepository

    async def get_active_events(self) -> list[Event]:
        return await self.event_repository.get_active_events(datetime.now(UTC))

    async def get_modifiers(self, *, event_ids: list[str]) -> list[EventModifier]:
        return await self.event_repository.get_modifiers(event_ids=event_ids)

    async def get_items(self, *, event_ids: list[str]) -> list[EventItem]:
        return await self.event_repository.get_items(event_ids=event_ids)

    async def get_goals(self, *, event_ids: list[str]) -> list[EventGoal]:
        return await self.event_repository.get_goals(event_ids=event_ids)

    async def get_user_events(
        self,
        *,
        user_id: int,
        event_ids: list[str],
    ) -> list[UserEvent]:
        return await self.event_repository.get_user_events(
            user_id=user_id,
            event_ids=event_ids,
        )

    async def get_user_event(
        self,
        *,
        user_id: int,
        event_id: str,
    ) -> UserEvent | None:
        return await self.event_repository.get_user_event(
            user_id=user_id,
            event_id=event_id,
        )

    async def get_goal(self, *, goal_id: str) -> EventGoal | None:
        return await self.event_repository.get_goal(goal_id=goal_id)

    async def mark_reward_claimed(self, user_event: UserEvent) -> UserEvent:
        return await self.event_repository.mark_reward_claimed(user_event)
