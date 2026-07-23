from datetime import datetime

from sqlalchemy import select

from app.db.models.event import Event
from app.db.models.event_extended import EventGoal, EventItem, EventModifier, UserEvent
from app.db.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    model = Event

    async def get_active_event(self, now: datetime) -> Event | None:
        query = (
            select(Event)
            .where(
                Event.is_active.is_(True),
                Event.starts_at <= now,
                Event.ends_at > now,
            )
            .order_by(Event.ends_at.asc())
            .limit(1)
        )

        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_active_events(self, now: datetime) -> list[Event]:
        result = await self.session.execute(
            select(Event)
            .where(
                Event.is_active.is_(True),
                Event.starts_at <= now,
                Event.ends_at >= now,
            )
        )
        return list(result.scalars().all())

    async def get_modifiers(self, *, event_ids: list[str]) -> list[EventModifier]:
        if not event_ids:
            return []
        result = await self.session.execute(
            select(EventModifier).where(EventModifier.event_id.in_(event_ids))
        )
        return list(result.scalars().all())

    async def get_items(self, *, event_ids: list[str]) -> list[EventItem]:
        if not event_ids:
            return []
        result = await self.session.execute(
            select(EventItem).where(EventItem.event_id.in_(event_ids))
        )
        return list(result.scalars().all())

    async def get_goals(self, *, event_ids: list[str]) -> list[EventGoal]:
        if not event_ids:
            return []
        result = await self.session.execute(
            select(EventGoal).where(EventGoal.event_id.in_(event_ids))
        )
        return list(result.scalars().all())

    async def get_user_events(
        self,
        *,
        user_id: int,
        event_ids: list[str],
    ) -> list[UserEvent]:
        if not event_ids:
            return []
        result = await self.session.execute(
            select(UserEvent).where(
                UserEvent.user_id == user_id,
                UserEvent.event_id.in_(event_ids),
            )
        )
        return list(result.scalars().all())

    async def get_user_event(
        self,
        *,
        user_id: int,
        event_id: str,
    ) -> UserEvent | None:
        result = await self.session.execute(
            select(UserEvent)
            .where(UserEvent.user_id == user_id, UserEvent.event_id == event_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_goal(self, *, goal_id: str) -> EventGoal | None:
        return await self.session.get(EventGoal, goal_id)

    async def mark_reward_claimed(self, user_event: UserEvent) -> UserEvent:
        user_event.reward_claimed = True
        self.session.add(user_event)
        await self.session.flush()
        return user_event
